# -*- coding: utf-8 -*-
"""
modules/sportivi.py

Integrazione di PNEV Sport Vision nel gestionale The Organism.

PNEV Sport Vision e' un'app separata su pnev.it (12 moduli di allenamento
visivo-sportivo). I dati restano nel browser del terapista e vengono
esportati a fine giornata come archivio JSON. Questo modulo:

  1) collega un codice paziente (pseudonimo, usato nell'app) al paziente
     vero della cartella clinica;
  2) importa l'archivio JSON esportato dall'app, evitando duplicati;
  3) mostra lo storico delle sedute per paziente, modulo per modulo.

Aggancio nel router (vedi INTEGRAZIONE_PNEV.py):
    from modules.sportivi import render_sportivi
    render_sportivi(paziente_id, paziente_nome)
"""

import json
from datetime import datetime

import streamlit as st

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Rome")
except Exception:
    _TZ = None

try:
    from modules.app_core import get_connection
except Exception:
    get_connection = None

SPORT_BASE_URL = "https://www.pnev.it/wp-content/uploads/giochi/sport"

MODULI = {
    "rotatore":      {"nome": "Rotatore",                 "cat": "Fissazione / lettura rapida"},
    "anaglifo":      {"nome": "Anaglifo",                 "cat": "Vergenza / soppressione"},
    "facilita":      {"nome": "Facilità",                 "cat": "Saccadi / accomodazione"},
    "reazione":      {"nome": "Tempo di reazione",        "cat": "Tempo di reazione"},
    "periferica":    {"nome": "Visione periferica",       "cat": "Campo utile"},
    "anticipazione": {"nome": "Timing di anticipazione",  "cat": "Timing"},
    "memoria":       {"nome": "Memoria e sequenze",       "cat": "Memoria di lavoro"},
    "mano":          {"nome": "Velocità della mano",      "cat": "Latenza / esecuzione"},
    "sequenza":      {"nome": "Tachistoscopio a sequenze","cat": "Percezione rapida"},
    "segnali":       {"nome": "Segnali",                  "cat": "Metronomo / comandi sonori"},
    "tabelle":       {"nome": "Tabelle",                  "cat": "Hart Chart / saccadi / slap-tap"},
    "procedure":     {"nome": "Procedure",                "cat": "Registro del lavoro sul corpo"},
}
ORDINE = ["rotatore", "anaglifo", "facilita", "reazione", "periferica",
          "anticipazione", "memoria", "mano", "sequenza", "segnali",
          "tabelle", "procedure"]


# ---------------------------------------------------------------- DB
def _init_db(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sv_codici (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                codice      TEXT NOT NULL,
                paziente_id BIGINT,
                creato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (studio_id, codice)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sv_sessioni (
                id           BIGSERIAL PRIMARY KEY,
                studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                sessione_id  TEXT NOT NULL,
                paziente_id  BIGINT,
                codice       TEXT,
                modulo       TEXT,
                quando       TIMESTAMPTZ,
                durata_sec   INT,
                prove        INT,
                indici       JSONB,
                parametri    JSONB,
                calibrazione JSONB,
                raw          JSONB,
                creato_il    TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (studio_id, sessione_id)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sv_sessioni_paziente ON sv_sessioni (paziente_id, quando DESC);")
        for tbl, pol in (("sv_codici", "sv_codici_studio"), ("sv_sessioni", "sv_sessioni_studio")):
            cur.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
            cur.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = '{tbl}' AND policyname = '{pol}') THEN
                        CREATE POLICY {pol} ON {tbl}
                            USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                            WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
                    END IF;
                END $$;
            """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _get_codice(conn, paziente_id):
    cur = conn.cursor()
    cur.execute("SELECT codice FROM sv_codici WHERE paziente_id = %s LIMIT 1", (paziente_id,))
    r = cur.fetchone()
    return r[0] if r else None


def _set_codice(conn, paziente_id, codice):
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sv_codici WHERE codice = %s", (codice,))
        existing = cur.fetchone()
        if existing:
            cur.execute("UPDATE sv_codici SET paziente_id = %s WHERE codice = %s", (paziente_id, codice))
        else:
            cur.execute("INSERT INTO sv_codici (codice, paziente_id) VALUES (%s, %s)", (codice, paziente_id))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise


def _paziente_per_codice(conn, codice):
    cur = conn.cursor()
    cur.execute("SELECT paziente_id FROM sv_codici WHERE codice = %s", (codice,))
    r = cur.fetchone()
    return int(r[0]) if r and r[0] is not None else None


def _importa_record(conn, rec):
    """Inserisce un record dell'archivio JSON. Ritorna True se nuovo, False se duplicato."""
    sess_id = str(rec.get("id") or "")
    if not sess_id:
        return False
    codice = rec.get("codice")
    paziente_id = _paziente_per_codice(conn, codice) if codice else None
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO sv_sessioni
                (sessione_id, paziente_id, codice, modulo, quando, durata_sec, prove,
                 indici, parametri, calibrazione, raw)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (studio_id, sessione_id) DO NOTHING
            RETURNING id
        """, (
            sess_id, paziente_id, codice, rec.get("modulo"), rec.get("quando"),
            rec.get("durataSec"), rec.get("prove"),
            json.dumps(rec.get("indici") or {}, ensure_ascii=False),
            json.dumps(rec.get("parametri") or {}, ensure_ascii=False),
            json.dumps(rec.get("calibrazione")) if rec.get("calibrazione") is not None else None,
            json.dumps(rec, ensure_ascii=False),
        ))
        row = cur.fetchone()
        conn.commit()
        return row is not None
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise


def _lista_sessioni(conn, paziente_id, limite=300):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, modulo, quando, durata_sec, prove, indici, parametri
        FROM sv_sessioni WHERE paziente_id = %s ORDER BY quando DESC LIMIT %s
    """, (paziente_id, limite))
    return cur.fetchall()


def _fmt_data(dt):
    if dt is None:
        return ""
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        if _TZ is not None and dt.tzinfo is not None:
            dt = dt.astimezone(_TZ)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


def _genera_codice(cognome, nome, data_nascita):
    """Codice deterministico: 2 lettere cognome + 2 lettere nome + ddmmyy nascita."""
    import re as _re
    c = _re.sub(r"[^A-Za-zÀ-ÿ]", "", (cognome or "")).upper()[:2] or "XX"
    n = _re.sub(r"[^A-Za-zÀ-ÿ]", "", (nome or "")).upper()[:2] or "XX"
    dd = ""
    if data_nascita:
        try:
            d = data_nascita
            if isinstance(d, str):
                d = datetime.fromisoformat(d[:10])
            dd = d.strftime("%d%m%y")
        except Exception:
            dd = ""
    return f"{c}{n}{dd}" or None


def _codice_univoco(conn, base):
    """Se il codice base è già usato da un altro paziente, aggiunge un suffisso numerico."""
    cur = conn.cursor()
    candidato = base
    i = 1
    while True:
        cur.execute("SELECT paziente_id FROM sv_codici WHERE codice = %s", (candidato,))
        r = cur.fetchone()
        if not r:
            return candidato
        i += 1
        candidato = f"{base}{i}"


# ---------------------------------------------------------------- UI
def _sez_codice(conn, paziente_id, paziente_nome, cognome=None, nome=None, data_nascita=None):
    st.write("PNEV Sport Vision non usa il nome del paziente: usa un **codice** che si "
             "digita nella targhetta in alto a destra di ogni modulo. Viene generato in automatico "
             "e resta salvato qui, così non si perde.")
    attuale = _get_codice(conn, paziente_id)
    if not attuale:
        base = _genera_codice(cognome, nome, data_nascita)
        if base:
            attuale = _codice_univoco(conn, base)
            try:
                _set_codice(conn, paziente_id, attuale)
            except Exception as e:
                st.error(f"Errore nella generazione del codice: {e}")
                attuale = None
    if attuale:
        st.text_input("Codice paziente (Sport Vision)", value=attuale, key="sv_codice_ro", disabled=True)
        st.caption(f"Codice collegato a {paziente_nome or 'questo paziente'}: **{attuale}** — usalo nella targhetta dell'app.")
    st.divider()
    st.caption("Serve un codice diverso? Puoi impostarlo manualmente qui sotto.")
    manuale = st.text_input("Codice manuale (opzionale)", value="", key="sv_codice_input",
                             placeholder="es. AB12CD").strip().upper()
    if st.button("🔗 Collega questo codice al paziente", disabled=not manuale):
        try:
            _set_codice(conn, paziente_id, manuale)
            st.success(f"Codice **{manuale}** collegato a {paziente_nome or 'questo paziente'}.")
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")


def _sez_apri(conn, paziente_id):
    codice = _get_codice(conn, paziente_id)
    if not codice:
        st.info("Collega prima un codice paziente (tab **Codice paziente**).")
        return
    suffix = f"?codice={codice}"
    st.link_button("▶️ Apri PNEV Sport Vision (indice)", f"{SPORT_BASE_URL}/sport.html{suffix}",
                    use_container_width=True)
    st.caption("Il codice è già in coda al link: comparirà da solo nella targhetta.")
    st.markdown("**Moduli**")
    cols = st.columns(3)
    for i, slug in enumerate(ORDINE):
        info = MODULI[slug]
        with cols[i % 3]:
            try:
                st.link_button(info["nome"], f"{SPORT_BASE_URL}/{slug}.html{suffix}", use_container_width=True)
            except Exception:
                st.markdown(f"- [{info['nome']}]({SPORT_BASE_URL}/{slug}.html{suffix})")
            st.caption(info["cat"])


def _sez_importa(conn):
    st.write("Carica qui l'archivio JSON esportato da **Andamento → Esporta** dentro Sport Vision. "
             "Le sedute vengono assegnate al paziente in base al codice, se già collegato; "
             "altrimenti resteranno da assegnare finché non colleghi quel codice.")
    up = st.file_uploader("Archivio JSON", type=["json"], key="sv_upload")
    if up is not None:
        try:
            dati = json.loads(up.read().decode("utf-8"))
            righe = dati if isinstance(dati, list) else [dati]
        except Exception as e:
            st.error(f"File non leggibile: {e}")
            return
        if st.button("📥 Importa", type="primary"):
            nuove, dupl = 0, 0
            for rec in righe:
                try:
                    if _importa_record(conn, rec):
                        nuove += 1
                    else:
                        dupl += 1
                except Exception as e:
                    st.error(f"Errore su un record: {e}")
                    break
            st.success(f"{nuove} sedute nuove importate, {dupl} già presenti.")


def _sez_storico(conn, paziente_id):
    if not paziente_id:
        st.info("Seleziona un paziente per vedere lo storico.")
        return
    righe = _lista_sessioni(conn, int(paziente_id))
    if not righe:
        st.info("Ancora nessuna seduta Sport Vision per questo paziente. Importa l'archivio nella tab dedicata.")
        return
    st.caption(f"{len(righe)} sedute")
    for r in righe:
        rid, modulo, quando, durata, prove, indici, parametri = r
        nome_mod = MODULI.get(modulo, {}).get("nome", modulo)
        with st.expander(f"{_fmt_data(quando)} — {nome_mod}" + (f" · {prove} prove" if prove else "")):
            if durata:
                st.caption(f"Durata: {durata // 60}′{durata % 60:02d}″")
            if isinstance(indici, dict) and indici:
                st.table([{"Indice": k, "Valore": v} for k, v in indici.items()])
            if isinstance(parametri, dict) and parametri:
                st.caption("Parametri: " + ", ".join(f"{k}={v}" for k, v in parametri.items()))


def _init_kit_db(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sv_kit_richieste (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                nome        TEXT,
                cognome     TEXT,
                indirizzo   TEXT,
                data_nascita DATE,
                codice      TEXT,
                spedito     BOOLEAN DEFAULT false,
                creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("ALTER TABLE sv_kit_richieste ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE sv_kit_richieste FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'sv_kit_richieste' AND policyname = 'sv_kit_richieste_studio') THEN
                    CREATE POLICY sv_kit_richieste_studio ON sv_kit_richieste
                        USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                        WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
                END IF;
            END $$;
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _notifica_kit_richiesto(nome, cognome, indirizzo, codice):
    try:
        from modules.ui_questionari import _invia_email
        import streamlit as _st
        dest = (_st.secrets.get("smtp", {}).get("NOTIFICA_A")
                or _st.secrets.get("smtp", {}).get("USERNAME"))
        if not dest:
            return
        corpo = (f"Nuova richiesta kit anaglifico da PNEV Sport Vision\n\n"
                 f"Nome: {cognome} {nome}\nIndirizzo: {indirizzo}\nCodice generato: {codice}\n\n"
                 f"Lo trovi nel gestionale in PNEV Sport Vision.")
        _invia_email(dest, f"PNEV Sport Vision — richiesta kit: {cognome} {nome}", corpo)
    except Exception:
        pass


def ui_public_kit_sportivo(get_conn):
    """Pagina pubblica (no login): richiesta kit anaglifico + generazione codice.
    Pensata per essere incorporata via iframe in inizia.html su pnev.it."""
    conn = get_conn()
    try:
        _init_kit_db(conn)
    except Exception as e:
        st.error(f"Servizio non disponibile: {e}")
        return

    st.markdown("""<style>
      #MainMenu, footer, header {visibility:hidden}
      .block-container{max-width:520px;padding-top:1.2rem}
    </style>""", unsafe_allow_html=True)

    codice_generato = st.session_state.get("_kit_codice")
    if codice_generato:
        st.success(f"Fatto! Il tuo codice è **{codice_generato}** — usalo per iniziare il tuo programma.")
        st.link_button("Vai al mio programma →",
                        f"{SPORT_BASE_URL}/programma.html?codice={codice_generato}",
                        use_container_width=True)
        return

    st.markdown("#### Richiedi il tuo kit anaglifico gratuito")
    st.caption("Ti mandiamo gli occhialini rosso/ciano e generiamo il tuo codice personale per iniziare il programma.")
    with st.form("form_kit_sportivo"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome *")
        cognome = c2.text_input("Cognome *")
        indirizzo = st.text_input("Indirizzo di spedizione *", placeholder="Via, civico, città, CAP")
        data_nascita = st.date_input("Data di nascita *", value=None,
                                      min_value=datetime(1930, 1, 1), max_value=datetime.now())
        inviato = st.form_submit_button("Genera il mio codice →", type="primary", use_container_width=True)

    if inviato:
        manca = [l for l, v in [("Nome", nome), ("Cognome", cognome), ("Indirizzo", indirizzo)]
                 if not (v or "").strip()]
        if not data_nascita:
            manca.append("Data di nascita")
        if manca:
            st.error("Campi obbligatori mancanti: " + ", ".join(manca))
            return
        try:
            base = _genera_codice(cognome, nome, data_nascita.isoformat())
            codice = _codice_univoco(conn, base)
            cur = conn.cursor()
            cur.execute("""INSERT INTO sv_kit_richieste (nome, cognome, indirizzo, data_nascita, codice)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (nome.strip(), cognome.strip(), indirizzo.strip(), data_nascita.isoformat(), codice))
            conn.commit()
            _set_codice(conn, None, codice)  # registra il codice anche in sv_codici, senza paziente ancora
        except Exception as e:
            st.error(f"Errore: {e}")
            return
        _notifica_kit_richiesto(nome.strip(), cognome.strip(), indirizzo.strip(), codice)
        st.session_state["_kit_codice"] = codice
        st.rerun()


def _lista_richieste_kit(conn, solo_da_spedire=False):
    cur = conn.cursor()
    if solo_da_spedire:
        cur.execute("SELECT id, nome, cognome, indirizzo, data_nascita, codice, spedito, creato_il FROM sv_kit_richieste WHERE spedito = false ORDER BY creato_il DESC")
    else:
        cur.execute("SELECT id, nome, cognome, indirizzo, data_nascita, codice, spedito, creato_il FROM sv_kit_richieste ORDER BY creato_il DESC LIMIT 300")
    return cur.fetchall()


def _segna_spedito(conn, rid):
    cur = conn.cursor()
    cur.execute("UPDATE sv_kit_richieste SET spedito = true WHERE id = %s", (rid,))
    conn.commit()


def _sez_richieste_kit(conn):
    try:
        _init_kit_db(conn)
    except Exception as e:
        st.error(f"Tabella richieste non disponibile: {e}")
        return
    solo = st.checkbox("Mostra solo da spedire", value=True, key="sv_kit_solo")
    righe = _lista_richieste_kit(conn, solo)
    if not righe:
        st.info("Nessuna richiesta.")
        return
    st.caption(f"{len(righe)} richieste")
    for rid, nome, cognome, indirizzo, dn, codice, spedito, creato in righe:
        with st.expander(f"{'✅' if spedito else '📦'} {cognome} {nome} — {codice}"):
            st.markdown(f"**Indirizzo:** {indirizzo}")
            st.markdown(f"**Data di nascita:** {_fmt_data(dn)}")
            st.markdown(f"**Richiesto il:** {_fmt_data(creato)}")
            if not spedito:
                if st.button("📮 Segna come spedito", key=f"sv_kit_sp_{rid}"):
                    _segna_spedito(conn, rid)
                    st.rerun()


def render_sportivi(paziente_id=None, paziente_nome=None, cognome=None, nome=None, data_nascita=None):
    st.header("🏃 PNEV Sport Vision")

    if get_connection is None:
        st.error("Connessione al database non disponibile.")
        return
    conn = get_connection()

    try:
        _init_db(conn)
    except Exception as e:
        st.warning(f"Inizializzazione tabelle Sport Vision: {e}")

    if paziente_id is None:
        st.info("Seleziona un paziente dalla cartella per collegare un codice e vedere lo storico.")
        return

    st.caption(f"Paziente: {paziente_nome or ''} (id {int(paziente_id)})")
    t_codice, t_apri, t_importa, t_storico, t_kit = st.tabs(
        ["🔗 Codice paziente", "▶️ Apri un modulo", "📥 Importa archivio", "🕓 Storico", "📦 Richieste kit"])
    with t_codice:
        _sez_codice(conn, paziente_id, paziente_nome, cognome, nome, data_nascita)
    with t_apri:
        _sez_apri(conn, paziente_id)
    with t_importa:
        _sez_importa(conn)
    with t_storico:
        _sez_storico(conn, paziente_id)
    with t_kit:
        _sez_richieste_kit(conn)
