# -*- coding: utf-8 -*-
"""
modules/ascolti_maps.py

Aderenza agli ascolti MAPS — chi ha fatto la lezione del giorno e chi no.

Come arrivano i dati: un piccolo snippet lato WordPress (vedi
wp-snippet-traccia-ascolti.php) chiama questo endpoint pubblico ogni volta
che LearnPress segna una lezione completata per uno studente. Nessuna
modifica ai player: l'aderenza si registra lato WordPress, che è la fonte
di verità su chi ha davvero finito la lezione.

Uso doppio, come richiesto:
- controllo clinico: chi si sta perdendo dei giorni, per intervenire prima
  che l'abbandono sia già successo
- marketing/relazione: il paziente sa che qualcuno guarda se ascolta, e lo
  studio può scrivere "ti sei perso l'ascolto di ieri" — la persona si
  sente seguita, non solo monitorata
"""

import datetime
import streamlit as st

TOKEN_SEGRETO = "pnev_ascolti_2026"  # deve combaciare con lo snippet WP

CORSI = {
    "basic": "Stimolazione uditiva — Basic (84 giorni)",
    "intermediate": "Stimolazione uditiva — Intermediate",
    "potential": "Potential",
}


def _assicura_tabella(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ascolti_maps (
            id          BIGSERIAL PRIMARY KEY,
            studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            email       TEXT NOT NULL,
            paziente_id BIGINT,
            corso       TEXT,
            giorno      INT,
            completato_il TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("""CREATE INDEX IF NOT EXISTS ix_ascolti_email
                   ON ascolti_maps (email, corso, giorno);""")
    cur.execute("ALTER TABLE ascolti_maps ENABLE ROW LEVEL SECURITY;")
    cur.execute("ALTER TABLE ascolti_maps FORCE ROW LEVEL SECURITY;")
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies
                           WHERE tablename='ascolti_maps' AND policyname='ascolti_maps_studio') THEN
                CREATE POLICY ascolti_maps_studio ON ascolti_maps
                    USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                    WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
            END IF;
        END $$;
    """)
    conn.commit()


def _collega_paziente(conn, email):
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pazienti WHERE lower(email)=lower(%s) LIMIT 1", (email,))
        r = cur.fetchone()
        return int(r[0]) if r else None
    except Exception:
        return None


def _invia_conferma_email(email, corso, giorno):
    """Email breve ad ogni ascolto completato (non solo a fine fase)."""
    try:
        from modules.ui_questionari import _invia_email
        corpo = (
            f"Ascolto di oggi registrato ✅ — giorno {giorno}/84 di "
            f"{CORSI.get(corso, corso)}.\n\n"
            f"MAPS funziona per stimolazione continua: è la costanza, giorno dopo "
            f"giorno, a fare la differenza — non l'intensità di un singolo ascolto. "
            f"Ci vediamo domani.\n\n"
            f"Studio The Organism — Metodo PNEV"
        )
        _invia_email(email, "Ascolto di oggi completato ✅", corpo)
    except Exception:
        pass


def _invia_congratulazioni_email(email, corso, giorno):
    """Email automatica quando si completa una fase (ogni 21 giorni)."""
    try:
        from modules.ui_questionari import _invia_email
        fase = (giorno - 1) // 21 + 1
        oggetto = f"Complimenti — hai completato {CORSI.get(corso, corso)} {fase}! 🎉"
        corpo = (
            f"Un traguardo importante: hai portato a termine 21 giorni di ascolto.\n\n"
            f"La costanza è la parte più difficile, e tu l'hai fatta. Continua così — "
            f"si riparte con la fase successiva.\n\n"
            f"Studio The Organism — Metodo PNEV"
        )
        _invia_email(email, oggetto, corpo)
        return True
    except Exception:
        return False


def registra_ascolto(conn, email, corso, giorno):
    """Chiamata dall'endpoint pubblico. Evita doppioni stesso giorno/corso."""
    cur = conn.cursor()
    cur.execute("""SELECT 1 FROM ascolti_maps
                   WHERE lower(email)=lower(%s) AND corso=%s AND giorno=%s""",
                (email, corso, giorno))
    if cur.fetchone():
        return False
    pid = _collega_paziente(conn, email)
    cur.execute("""INSERT INTO ascolti_maps (email, paziente_id, corso, giorno)
                   VALUES (%s,%s,%s,%s)""", (email, pid, corso, giorno))
    conn.commit()
    return True


def ui_public_ascolto_hook(get_conn):
    """Endpoint pubblico: ?ascolto_hook=1&token=...&email=...&corso=basic&giorno=14"""
    qs = st.query_params
    def p(k, d=""):
        v = qs.get(k, d)
        return (v[0] if isinstance(v, list) and v else v) or d

    if p("token") != TOKEN_SEGRETO:
        st.write("no")
        return
    email = p("email").strip()
    corso = p("corso").strip() or "basic"
    try:
        giorno = int(p("giorno", "0"))
    except Exception:
        giorno = 0
    if not email or not giorno:
        st.write("no")
        return
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        nuovo = registra_ascolto(conn, email, corso, giorno)
        if nuovo:
            _invia_conferma_email(email, corso, giorno)
            if giorno % 21 == 0:
                _invia_congratulazioni_email(email, corso, giorno)
        st.write("ok" if nuovo else "già")
    except Exception as e:
        st.write(f"errore: {e}")


def _giorni_da_iscrizione(conn, email, corso):
    """Giorno atteso oggi = giorni trascorsi dal primo ascolto registrato +1
    (approssimazione: senza data di iscrizione LearnPress nel gestionale)."""
    cur = conn.cursor()
    cur.execute("""SELECT min(completato_il) FROM ascolti_maps
                   WHERE lower(email)=lower(%s) AND corso=%s""", (email, corso))
    r = cur.fetchone()
    if not r or not r[0]:
        return None
    delta = (datetime.datetime.now(r[0].tzinfo) - r[0]).days
    return delta + 1


def studenti_da_sollecitare(conn):
    """Chi ha iniziato ma non ha ascoltato oggi (e non ha finito gli 84 giorni)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT email, corso, max(giorno) AS ultimo, max(completato_il) AS ultima_data
        FROM ascolti_maps
        GROUP BY email, corso
        HAVING max(giorno) < 84
    """)
    out = []
    oggi = datetime.date.today()
    for r in cur.fetchall():
        email = r[0] if not hasattr(r, "keys") else r["email"]
        corso = r[1] if not hasattr(r, "keys") else r["corso"]
        ultimo = r[2] if not hasattr(r, "keys") else r["ultimo"]
        ultima_data = r[3] if not hasattr(r, "keys") else r["ultima_data"]
        try:
            giorno_ultima = ultima_data.date() if hasattr(ultima_data, "date") else ultima_data
        except Exception:
            giorno_ultima = None
        if giorno_ultima != oggi:  # non ha ancora ascoltato oggi
            out.append({"email": email, "corso": corso, "ultimo": ultimo,
                       "ultima_data": ultima_data})
    return out


def invia_promemoria_giornalieri(conn, email_studio=None):
    """Da chiamare una volta al giorno (cron). Manda un promemoria a chi non
    ha ancora ascoltato oggi, e un riepilogo allo studio."""
    from modules.ui_questionari import _invia_email
    da_sollecitare = studenti_da_sollecitare(conn)
    for s in da_sollecitare:
        try:
            corpo = (
                f"Ciao! Ti scriviamo per ricordarti l'ascolto di oggi — "
                f"sei al giorno {s['ultimo']} di {CORSI.get(s['corso'], s['corso'])}.\n\n"
                f"MAPS si basa sulla stimolazione uditiva continua: è la regolarità "
                f"quotidiana, non un singolo ascolto più lungo, a fare il lavoro. "
                f"Anche solo cinque minuti oggi mantengono il percorso vivo.\n\n"
                f"Studio The Organism — Metodo PNEV"
            )
            _invia_email(s["email"], "Promemoria — il tuo ascolto MAPS di oggi", corpo)
        except Exception:
            pass

    if email_studio and da_sollecitare:
        try:
            righe = "\n".join(f"- {s['email']} ({CORSI.get(s['corso'], s['corso'])}, "
                              f"fermo al giorno {s['ultimo']})" for s in da_sollecitare)
            _invia_email(email_studio, f"MAPS — {len(da_sollecitare)} studenti da sollecitare oggi",
                        f"Non hanno ancora ascoltato oggi:\n\n{righe}")
        except Exception:
            pass
    return len(da_sollecitare)


def render_aderenza_ascolti(conn):
    st.subheader("🎧 Aderenza agli ascolti MAPS")
    st.caption("Chi ha fatto l'ascolto del giorno e chi lo sta saltando. "
              "Usalo sia per intervenire in tempo, sia per far sentire "
              "seguita la persona.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return

    corso_f = st.selectbox("Corso", ["tutti"] + list(CORSI.keys()),
                           format_func=lambda k: CORSI.get(k, "Tutti i corsi"))
    cur = conn.cursor()
    if corso_f == "tutti":
        cur.execute("""SELECT email, corso, max(giorno) AS ultimo, max(completato_il) AS ultima_data,
                       count(*) AS fatti
                       FROM ascolti_maps GROUP BY email, corso ORDER BY ultima_data DESC""")
    else:
        cur.execute("""SELECT email, corso, max(giorno) AS ultimo, max(completato_il) AS ultima_data,
                       count(*) AS fatti
                       FROM ascolti_maps WHERE corso=%s
                       GROUP BY email, corso ORDER BY ultima_data DESC""", (corso_f,))
    righe = cur.fetchall()
    if not righe:
        st.info("Nessun ascolto ancora registrato.")
        return

    oggi = datetime.datetime.now()
    for r in righe:
        email = r[0] if not hasattr(r, "keys") else r["email"]
        corso = r[1] if not hasattr(r, "keys") else r["corso"]
        ultimo = r[2] if not hasattr(r, "keys") else r["ultimo"]
        ultima_data = r[3] if not hasattr(r, "keys") else r["ultima_data"]
        fatti = r[4] if not hasattr(r, "keys") else r["fatti"]

        giorni_fermo = None
        try:
            ud = ultima_data if ultima_data.tzinfo else ultima_data.replace(tzinfo=oggi.astimezone().tzinfo)
            giorni_fermo = (datetime.datetime.now(ud.tzinfo) - ud).days
        except Exception:
            pass

        if giorni_fermo is not None and giorni_fermo >= 3:
            badge, colore = "🔴", "In pausa da " + str(giorni_fermo) + " giorni"
        elif giorni_fermo is not None and giorni_fermo >= 1:
            badge, colore = "🟡", "Ultimo ascolto ieri" if giorni_fermo == 1 else f"Fermo da {giorni_fermo}gg"
        else:
            badge, colore = "🟢", "Ascolto fatto oggi"

        with st.expander(f"{badge} {email} — {CORSI.get(corso, corso)} · giorno {ultimo}/84 · {colore}"):
            st.markdown(f"**Lezioni completate:** {fatti}  ·  **Ultima:** giorno {ultimo}")
            if giorni_fermo and giorni_fermo >= 1:
                msg = (f"Ciao! Abbiamo notato che ti sei fermato/a all'ascolto di qualche "
                       f"giorno fa. Ricorda che la costanza fa la differenza nel percorso — "
                       f"ti aspettiamo per il giorno {ultimo+1}. 🎧")
                c1, c2 = st.columns(2)
                c1.text_area("Messaggio da inviare", msg, height=90, key=f"asc_msg_{email}_{corso}")
                from urllib.parse import quote
                c2.markdown(f"[📱 Apri su WhatsApp](https://wa.me/?text={quote(msg)})")

    st.caption("«In pausa» = nessun ascolto registrato da 3 o più giorni. "
              "Il dato arriva da LearnPress quando lo studente segna la "
              "lezione come completata.")
