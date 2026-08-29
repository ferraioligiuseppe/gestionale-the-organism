# -*- coding: utf-8 -*-
"""
modules/lead_sito.py

Contatti raccolti dal sito pnev.it (PNEV Games → invito → modulo dati).

Flusso:
  1. Il gioco rileva un segnale ripetuto nello stesso dominio funzionale
     (pnev-lead.js, logica centro/banda) e invita a lasciare i dati.
  2. Il genitore arriva su   ?lead=1&src=<gioco>&dom=<dominio>&n=<partite>&dev=<scostamento>
     compila nome/cognome/email/telefono/età e, subito dopo, il questionario
     di screening.
  3. Tutto finisce in `lead_sito` — NON in anagrafica: l'anagrafica si crea
     solo quando lo decidi tu da "📨 Contatti dal sito" (evita spam e
     doppioni). Alla conversione il questionario viene portato nella cartella.

Nota clinica: il dominio e lo scostamento sono indizi di screening, non
diagnosi. Sul sito il testo resta neutro; l'ipotesi clinica la leggi qui.
"""

import json
import datetime
import streamlit as st

# Domini clinici: la definizione unica sta in soglie_cliniche.py (server-side)
try:
    from modules.soglie_cliniche import DOMINI
except Exception:
    DOMINI = {
        "attenzione":   ("Attenzione e costanza", ""),
        "inibizione":   ("Controllo degli impulsi", ""),
        "occhiomano":   ("Coordinazione occhio-mano", ""),
        "oculomotor":   ("Controllo dei movimenti oculari", ""),
        "memoria":      ("Memoria di lavoro", ""),
        "flessibilita": ("Flessibilit\u00e0 nel cambiare regola", ""),
        "linguaggio":   ("Linguaggio e lettura", ""),
        "bilaterale":   ("Integrazione destra/sinistra", ""),
    }

QUESTIONARI = {
    "INPPS": "INPP-R \u2014 screening riflessi primitivi (Sally Goddard Blythe)",
    "MELILLO_BAMBINI": "Questionario neuro-evolutivo \u2014 bambini",
    "MELILLO_ADULTI": "Questionario neuro-evolutivo — adulti",
    "FISHER": "Questionario uditivo — bambini",
    "LINGUAGGIO_PNEV": "Screening linguaggio PNEV (3–6 anni)",
    "VISIONE_BAMBINI": "Questionario visivo — bambini",
    "VISIONE_ADULTI": "Questionario visivo — adulti",
}

# Dominio segnalato dai giochi → questionario più pertinente.
# (bambino, adulto)
QUEST_PER_DOMINIO = {
    "occhiomano":   ("INPPS",           "MELILLO_ADULTI"),
    "bilaterale":   ("INPPS",           "MELILLO_ADULTI"),
    "oculomotor":   ("VISIONE_BAMBINI", "VISIONE_ADULTI"),
    "linguaggio":   ("LINGUAGGIO_PNEV", "MELILLO_ADULTI"),
    "attenzione":   ("MELILLO_BAMBINI", "MELILLO_ADULTI"),
    "inibizione":   ("MELILLO_BAMBINI", "MELILLO_ADULTI"),
    "memoria":      ("MELILLO_BAMBINI", "MELILLO_ADULTI"),
    "flessibilita": ("MELILLO_BAMBINI", "MELILLO_ADULTI"),
}


def scegli_questionario(dominio, adulto=False):
    coppia = QUEST_PER_DOMINIO.get(dominio or "", ("INPPS", "MELILLO_ADULTI"))
    return coppia[1] if adulto else coppia[0]

STATI = ["nuovo", "contattato", "appuntamento fissato", "convertito", "archiviato"]


# ══════════════════════════════════════════════════════════ dati
def init_lead_db(conn):
    """Crea le tabelle con RLS multi-studio. Idempotente."""
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lead_visite (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                src_gioco   TEXT,
                dominio     TEXT,
                tipo_segnale TEXT,
                eta         INT,
                creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("ALTER TABLE lead_visite ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE lead_visite FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='lead_visite' AND policyname='lead_visite_studio') THEN
                    CREATE POLICY lead_visite_studio ON lead_visite
                        USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                        WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
                END IF;
            END $$;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lead_sito (
                id             BIGSERIAL PRIMARY KEY,
                studio_id      BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                nome           TEXT,
                cognome        TEXT,
                email          TEXT,
                telefono       TEXT,
                codice_fiscale TEXT,
                verificato     BOOLEAN DEFAULT false,
                token_verifica TEXT,
                eta_bambino    TEXT,
                per_chi        TEXT,
                src_gioco      TEXT,
                dominio        TEXT,
                n_segnali      INT,
                scostamento    REAL,
                consenso       BOOLEAN DEFAULT false,
                quest_tipo     TEXT,
                quest_json     JSONB,
                quest_sintesi  TEXT,
                stato          TEXT DEFAULT 'nuovo',
                note           TEXT,
                paziente_id    BIGINT,
                creato_il      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_lead_sito_stato
                       ON lead_sito (stato, creato_il DESC);""")
        cur.execute("ALTER TABLE lead_sito ADD COLUMN IF NOT EXISTS codice_fiscale TEXT;")
        cur.execute("ALTER TABLE lead_sito ADD COLUMN IF NOT EXISTS verificato BOOLEAN DEFAULT false;")
        cur.execute("ALTER TABLE lead_sito ADD COLUMN IF NOT EXISTS token_verifica TEXT;")
        cur.execute("ALTER TABLE lead_sito ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE lead_sito FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='lead_sito' AND policyname='lead_sito_studio') THEN
                    CREATE POLICY lead_sito_studio ON lead_sito
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


def _notifica_nuovo_contatto(dati, dom_label=""):
    """Avvisa per email che è arrivato un contatto dal sito. Silenzioso se
    lo SMTP non è configurato: il contatto è già salvato, la mail è un extra."""
    try:
        from modules.ui_questionari import _invia_email
        dest = (st.secrets.get("smtp", {}).get("NOTIFICA_A")
                or st.secrets.get("smtp", {}).get("USERNAME"))
        if not dest:
            return
        nome = f"{dati.get('cognome','')} {dati.get('nome','')}".strip()
        corpo = (
            f"Nuovo contatto dal sito pnev.it\n\n"
            f"Nome: {nome}\n"
            f"Email: {dati.get('email','—')}\n"
            f"Cellulare: {dati.get('telefono','—')}\n"
            f"Per chi: {dati.get('per_chi','—')}\n"
            f"Età: {dati.get('eta_bambino','—')}\n"
            f"Area segnalata dai giochi: {dom_label or '—'}\n"
            f"Gioco d'origine: {dati.get('src_gioco','—')}\n\n"
            f"Lo trovi nel gestionale in «Contatti dal sito»."
        )
        _invia_email(dest, f"PNEV — nuovo contatto dal sito: {nome}", corpo)
    except Exception:
        pass


def salva_lead(conn, dati):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO lead_sito
                (nome, cognome, email, telefono, eta_bambino, per_chi,
                 src_gioco, dominio, n_segnali, scostamento, consenso)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (dati.get("nome"), dati.get("cognome"), dati.get("email"),
              dati.get("telefono"), dati.get("eta_bambino"), dati.get("per_chi"),
              dati.get("src_gioco"), dati.get("dominio"), dati.get("n_segnali"),
              dati.get("scostamento"), bool(dati.get("consenso"))))
        new_id = cur.fetchone()[0]
        conn.commit()
        return int(new_id)
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def aggiorna_questionario(conn, lead_id, tipo, q_json, sintesi):
    cur = conn.cursor()
    try:
        cur.execute("""UPDATE lead_sito
                       SET quest_tipo=%s, quest_json=%s, quest_sintesi=%s
                       WHERE id=%s""",
                    (tipo, json.dumps(q_json, ensure_ascii=False, default=str),
                     sintesi, lead_id))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def lista_lead(conn, stato=None, limite=300):
    cur = conn.cursor()
    try:
        if stato and stato != "tutti":
            cur.execute("""SELECT * FROM lead_sito WHERE stato=%s
                           ORDER BY creato_il DESC LIMIT %s""", (stato, limite))
        else:
            cur.execute("""SELECT * FROM lead_sito
                           ORDER BY creato_il DESC LIMIT %s""", (limite,))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def aggiorna_stato(conn, lead_id, stato, note=None):
    cur = conn.cursor()
    try:
        if note is None:
            cur.execute("UPDATE lead_sito SET stato=%s WHERE id=%s", (stato, lead_id))
        else:
            cur.execute("UPDATE lead_sito SET stato=%s, note=%s WHERE id=%s",
                        (stato, note, lead_id))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def elimina_lead(conn, lead_id):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM lead_sito WHERE id=%s", (lead_id,))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _g(row, chiave, default=None):
    """Lettura tollerante: dict-cursor o tupla."""
    try:
        v = row[chiave] if hasattr(row, "keys") else None
        return v if v is not None else default
    except Exception:
        return default


def registra_visita(conn, src, dom, tipo, eta):
    """Traccia l'arrivo sulla pagina (anonimo: nessun dato personale)."""
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO lead_visite (src_gioco, dominio, tipo_segnale, eta)
                       VALUES (%s,%s,%s,%s)""",
                    (src or None, dom or None, tipo or None,
                     int(eta) if str(eta).isdigit() else None))
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
    finally:
        try: cur.close()
        except Exception: pass


def statistiche_imbuto(conn, giorni=90):
    """Numeri dell'imbuto: visite → dati → questionari → pazienti."""
    cur = conn.cursor()
    out = {}
    try:
        cur.execute("""SELECT count(*) FROM lead_visite
                       WHERE creato_il > now() - (%s || ' days')::interval""", (giorni,))
        out["visite"] = int(cur.fetchone()[0] or 0)
        cur.execute("""SELECT count(*) FROM lead_sito
                       WHERE creato_il > now() - (%s || ' days')::interval""", (giorni,))
        out["contatti"] = int(cur.fetchone()[0] or 0)
        cur.execute("""SELECT count(*) FROM lead_sito
                       WHERE quest_sintesi IS NOT NULL
                         AND creato_il > now() - (%s || ' days')::interval""", (giorni,))
        out["questionari"] = int(cur.fetchone()[0] or 0)
        cur.execute("""SELECT count(*) FROM lead_sito
                       WHERE paziente_id IS NOT NULL
                         AND creato_il > now() - (%s || ' days')::interval""", (giorni,))
        out["pazienti"] = int(cur.fetchone()[0] or 0)
        cur.execute("""SELECT dominio, count(*) FROM lead_visite
                       WHERE creato_il > now() - (%s || ' days')::interval
                       GROUP BY dominio ORDER BY 2 DESC""", (giorni,))
        out["per_dominio"] = [(r[0] if not hasattr(r, "keys") else r["dominio"],
                               r[1] if not hasattr(r, "keys") else r["count"])
                              for r in cur.fetchall()]
        cur.execute("""SELECT src_gioco, count(*) FROM lead_visite
                       WHERE creato_il > now() - (%s || ' days')::interval
                       GROUP BY src_gioco ORDER BY 2 DESC LIMIT 12""", (giorni,))
        out["per_gioco"] = [(r[0] if not hasattr(r, "keys") else r["src_gioco"],
                             r[1] if not hasattr(r, "keys") else r["count"])
                            for r in cur.fetchall()]
        return out
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def render_statistiche(conn):
    st.markdown("##### 📊 L'imbuto: da chi gioca a chi diventa paziente")
    giorni = st.selectbox("Periodo", [30, 90, 180, 365],
                          format_func=lambda g: f"ultimi {g} giorni",
                          index=1, key="lead_stat_giorni")
    try:
        s = statistiche_imbuto(conn, giorni)
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.info(f"Statistiche non ancora disponibili ({e}).")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Arrivati dal gioco", s["visite"])
    c2.metric("Hanno lasciato i dati", s["contatti"],
              f"{round(s['contatti']/s['visite']*100)}%" if s["visite"] else None)
    c3.metric("Questionario finito", s["questionari"],
              f"{round(s['questionari']/s['contatti']*100)}%" if s["contatti"] else None)
    c4.metric("Diventati pazienti", s["pazienti"],
              f"{round(s['pazienti']/s['contatti']*100)}%" if s["contatti"] else None)

    if s["visite"] == 0:
        st.caption("Nessun arrivo dai giochi in questo periodo.")
        return

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Da quale area**")
        for d, n in s["per_dominio"]:
            st.markdown(f"- {DOMINI.get(d, ('—',''))[0] or '(non indicata)'}: **{n}**")
    with cc2:
        st.markdown("**Da quale gioco**")
        for g, n in s["per_gioco"]:
            st.markdown(f"- {g or '(non indicato)'}: **{n}**")

    st.caption("«Arrivati dal gioco» conta i click sull'invito, non le partite: "
              "per il traffico complessivo del sito serve uno strumento di "
              "statistiche web. Nessun dato personale in questa tabella.")


def _notifica_maps_completato(livello, nome, extra=""):
    """Avvisa per email che un paziente ha completato un livello MAPS.
    Silenzioso se lo SMTP non è configurato."""
    try:
        from modules.ui_questionari import _invia_email
        dest = (st.secrets.get("smtp", {}).get("NOTIFICA_A")
                or st.secrets.get("smtp", {}).get("USERNAME"))
        if not dest:
            return
        corpo = (
            f"Un paziente ha completato il livello MAPS: {livello}\n\n"
            f"Nome/riferimento: {nome or '—'}\n"
            f"{extra}\n\n"
            f"Nessuna azione necessaria: è solo una notifica di avanzamento."
        )
        _invia_email(dest, f"PNEV — MAPS completato: {livello} ({nome or '—'})", corpo)
    except Exception:
        pass


# ══════════════════════════════════════ ping pubblico (no login) — fine livello MAPS
def ui_public_maps_done(get_conn):
    """Endpoint silenzioso: il player MAPS lo richiama a fine ultimo giorno
    di un livello (?maps_done=1&livello=basic&nome=...). Non mostra nulla
    di significativo: manda solo la notifica email e un pixel 1x1."""
    qp = st.query_params
    livello = qp.get("livello", "—")
    nome = qp.get("nome", "")
    extra = f"Sequenza/giorno: {qp.get('seq','—')}" if qp.get("seq") else ""
    _notifica_maps_completato(livello, nome, extra)
    st.markdown(
        "<div style='font-family:sans-serif;color:#999;font-size:12px;padding:20px'>ok</div>",
        unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════ pagina pubblica
def ui_public_lead_page(get_conn):
    """Pagina pubblica (no login): modulo contatti + questionario di screening."""
    qp = st.query_params
    def _p(k, d=""):
        v = qp.get(k, d)
        return (v[0] if isinstance(v, list) and v else v) or d

    src = _p("src"); dom = _p("dom"); n = _p("n", "0"); dev = _p("dev", "0")
    tipo_seg = _p("tipo", "specifico")
    dom2 = _p("dom2"); domini_tutti = _p("domini"); eta_gioco = _p("eta")

    # Pacchetto grezzo dai giochi: il criterio clinico si applica QUI,
    # non nel file pubblico su pnev.it.
    _raw = _p("raw")
    if _raw:
        try:
            from modules.soglie_cliniche import decodifica_payload, calcola_segnale
            _storico = decodifica_payload(_raw)
            if _storico:
                if not eta_gioco:
                    for _p0 in _storico:
                        if _p0.get("eta"):
                            eta_gioco = str(_p0["eta"]); break
                _seg = calcola_segnale(_storico)
                if _seg:
                    dom = _seg.get("dominio") or ""
                    dom2 = _seg.get("dominio2") or ""
                    tipo_seg = _seg.get("tipo", "specifico")
                    n = str(_seg.get("n", 0))
                    dev = str(_seg.get("dev", 0))
                    domini_tutti = ",".join(_seg.get("domini", []) or [])
        except Exception:
            pass

    dom_label, dom_nota = DOMINI.get(dom, ("", ""))
    dom2_label = DOMINI.get(dom2, ("", ""))[0] if dom2 else ""

    st.markdown("""<style>
      #MainMenu, footer, header {visibility:hidden}
      .block-container{max-width:760px;padding-top:2rem}
    </style>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="border-left:5px solid #1D6B44;background:#F2F8F4;'
        'padding:18px 22px;border-radius:12px;margin-bottom:22px">'
        '<div style="font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;'
        'color:#4b7a60;font-weight:700">Studio The Organism · Metodo PNEV</div>'
        '<div style="font-size:1.5rem;font-weight:800;color:#14502F;margin-top:4px">'
        'Approfondiamo insieme</div></div>', unsafe_allow_html=True)

    if tipo_seg == "globale":
        st.info("Dai giochi è emersa fatica in **più aree diverse**. Può dipendere "
                "da tante cose — anche solo stanchezza o poca familiarità con i "
                "giochi. Proprio perché il quadro è ampio, il passo utile non è un "
                "test su una singola abilità ma uno sguardo d'insieme: partiamo "
                "da qualche domanda sulla storia dello sviluppo.")
    elif tipo_seg == "convergenza" and dom_label and dom2_label:
        st.info(f"Dai giochi emergono insieme **{dom_label}** e **{dom2_label}**: "
                f"due aree che nello sviluppo si sostengono a vicenda. Quando "
                f"cedono insieme il dato è più informativo — non è una diagnosi, "
                f"ma vale la pena guardarlo bene.")
    elif dom_label:
        st.info(f"Dai giochi è emerso un segnale ripetuto nell'area **{dom_label}** "
                f"({n} partite). Non è una diagnosi: serve una valutazione vera per "
                f"capire se c'è qualcosa su cui lavorare — e spesso la risposta è "
                f"rassicurante.")
    else:
        st.info("Lascia i tuoi dati e ti ricontattiamo per capire insieme se una "
                "valutazione può essere utile.")

    conn = get_conn()
    try:
        init_lead_db(conn)
    except Exception as e:
        st.error(f"Servizio momentaneamente non disponibile ({e}).")
        return

    lead_id = st.session_state.get("_lead_id")

    # Traccia l'arrivo una sola volta per sessione (anonimo)
    if not st.session_state.get("_lead_visita_tracciata"):
        registra_visita(conn, src, dom, tipo_seg, eta_gioco)
        st.session_state["_lead_visita_tracciata"] = True

    # ── Passo 1: i contatti ──────────────────────────────────────────
    if not lead_id:
        with st.form("form_lead"):
            st.markdown("#### I tuoi dati")
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome *")
            cognome = c2.text_input("Cognome *")
            c3, c4 = st.columns(2)
            email = c3.text_input("Email *")
            telefono = c4.text_input("Cellulare *")
            per_chi = st.radio("Per chi stai chiedendo?",
                               ["Per mio figlio / mia figlia", "Per me stesso/a"],
                               horizontal=True)
            eta = st.text_input("Età (del bambino o la tua)")
            consenso = st.checkbox(
                "Ho letto l'informativa privacy e acconsento al trattamento dei "
                "dati per essere ricontattato/a. *")
            st.caption("I dati sono trattati dallo Studio The Organism ai soli fini "
                      "del ricontatto (GDPR art. 6.1.a). Puoi chiederne la "
                      "cancellazione in qualsiasi momento.")
            inviato = st.form_submit_button("Invia e continua →", type="primary",
                                            use_container_width=True)

        if inviato:
            manca = [l for l, v in [("Nome", nome), ("Cognome", cognome),
                                     ("Email", email), ("Cellulare", telefono)]
                     if not (v or "").strip()]
            if manca:
                st.error("Campi obbligatori mancanti: " + ", ".join(manca))
            elif "@" not in email or "." not in email.split("@")[-1]:
                st.error("L'indirizzo email non sembra valido.")
            elif not consenso:
                st.error("Serve il consenso al trattamento dei dati per procedere.")
            else:
                try:
                    new_id = salva_lead(conn, {
                        "nome": nome.strip(), "cognome": cognome.strip(),
                        "email": email.strip(), "telefono": telefono.strip(),
                        "eta_bambino": (eta or "").strip(), "per_chi": per_chi,
                        "src_gioco": src, "dominio": dom,
                        "n_segnali": int(n) if str(n).isdigit() else None,
                        "scostamento": float(dev) if dev not in ("", None) else None,
                        "consenso": True,
                    })
                    st.session_state["_lead_id"] = new_id
                    st.session_state["_lead_adulto"] = ("me stesso" in per_chi.lower())
                    st.session_state["_lead_tipo"] = tipo_seg
                    _notifica_nuovo_contatto({
                        "nome": nome.strip(), "cognome": cognome.strip(),
                        "email": email.strip(), "telefono": telefono.strip(),
                        "per_chi": per_chi, "eta_bambino": (eta or "").strip(),
                        "src_gioco": src,
                    }, dom_label)
                    st.rerun()
                except Exception as e:
                    st.error(f"Non è stato possibile salvare: {e}")
        return

    # ── Passo 2: il questionario di screening ────────────────────────
    st.success("Dati registrati. Ti ricontattiamo noi — nel frattempo, se hai "
              "cinque minuti, questo questionario ci fa arrivare molto più preparati.")

    adulto = bool(st.session_state.get("_lead_adulto"))
    # Quadro globale: nessun questionario mirato, si parte dalla storia
    if st.session_state.get("_lead_tipo") == "globale":
        tipo = "ANAMNESI_GLOBALE"
    else:
        tipo = scegli_questionario(dom, adulto)
    st.markdown("---")
    st.markdown("#### Questionario di screening")

    if tipo == "ANAMNESI_GLOBALE":
        st.caption("Poche domande sulla storia dello sviluppo: sono quelle che "
                  "orientano di più quando il quadro è ampio.")
        try:
            from modules.app_core import inpps_collect_ui
        except Exception:
            inpps_collect_ui = None
        if inpps_collect_ui is None:
            st.info("Non disponibile ora: ti ricontattiamo noi.")
            return
        with st.form("form_lead_glob"):
            q_data, q_sintesi = inpps_collect_ui(prefix="lead_glob", existing=None)
            ok = st.form_submit_button("📤 Invia le risposte", type="primary",
                                       use_container_width=True)
        if ok and q_data is not None:
            try:
                aggiorna_questionario(conn, lead_id, "INPPS", q_data, q_sintesi)
                st.balloons()
                st.success("Ricevuto, grazie. Ti ricontattiamo a breve.")
                st.session_state.pop("_lead_id", None)
            except Exception as e:
                st.error(f"Errore nell'invio: {e}")
        return

    st.caption(QUESTIONARI.get(tipo, ""))
    if tipo == "INPPS":
        st.caption("Fonte: INPP — Institute for Neuro-Physiological Psychology (Chester, UK), "
                  "questionario di Sally Goddard Blythe. È uno strumento di screening: "
                  "segnala qualcosa da approfondire, non è una diagnosi.")
    if dom_label:
        st.caption(f"Scelto in base all'area emersa dai giochi: {dom_label}.")

    q_data, q_sintesi, ok = None, "", False

    if tipo == "LINGUAGGIO_PNEV":
        try:
            from modules.questionario_linguaggio import (
                linguaggio_breve_ui, mostra_esito_breve)
        except Exception as e:
            st.info(f"Il questionario non è disponibile ora: te lo invieremo per email. ({e})")
            return
        st.caption("Nove domande, due minuti. Nato per la fascia in cui gli "
                  "strumenti disponibili non arrivano più.")
        try:
            q_data, q_sintesi, _p = linguaggio_breve_ui(prefix="lead_ling", pubblico=True)
        except Exception as e:
            st.error(f"Errore nel questionario: {e}")
            return
        st.markdown("---")
        mostra_esito_breve(q_data, pubblico=True)
        st.markdown("---")
        ok = st.button("📤 Invia le risposte", type="primary", use_container_width=True)

    elif tipo == "INPPS":
        try:
            from modules.app_core import inpps_collect_ui
        except Exception:
            inpps_collect_ui = None
        if inpps_collect_ui is None:
            st.info("Il questionario non è disponibile ora: te lo invieremo per email.")
            return
        with st.form("form_lead_quest"):
            q_data, q_sintesi = inpps_collect_ui(prefix="lead_inpps", existing=None)
            ok = st.form_submit_button("📤 Invia questionario", type="primary",
                                       use_container_width=True)
    else:
        try:
            from modules.pnev.ui_questionari_pnev import (
                melillo_adulti_ui, melillo_bambini_ui, fisher_auditivo_bambini_ui,
                visione_bambini_ui, visione_adulti_ui,
            )
        except Exception as e:
            st.info(f"Il questionario non è disponibile ora: te lo invieremo per email. ({e})")
            return
        fn = {"MELILLO_ADULTI": melillo_adulti_ui,
              "MELILLO_BAMBINI": melillo_bambini_ui,
              "FISHER": fisher_auditivo_bambini_ui,
              "VISIONE_BAMBINI": visione_bambini_ui,
              "VISIONE_ADULTI": visione_adulti_ui}.get(tipo)
        if fn is None:
            st.info("Questionario non riconosciuto: te lo invieremo per email.")
            return
        # Questi questionari hanno widget interattivi: niente st.form
        chiave = f"_lead_q_{lead_id}"
        if chiave not in st.session_state:
            st.session_state[chiave] = {}
        try:
            q_data, q_sintesi = fn(prefix=f"lead_{tipo.lower()}",
                                   existing=st.session_state[chiave])
            st.session_state[chiave] = q_data
        except Exception as e:
            st.error(f"Errore nel questionario: {e}")
            return
        st.markdown("---")
        ok = st.button("📤 Invia questionario", type="primary", use_container_width=True)

    if ok and q_data is not None:
        try:
            aggiorna_questionario(conn, lead_id, tipo, q_data, q_sintesi)
            st.balloons()
            st.success("Ricevuto, grazie. Ti ricontattiamo a breve.")
            st.session_state.pop("_lead_id", None)
        except Exception as e:
            st.error(f"Errore nell'invio: {e}")


def converti_in_paziente(conn, lead_id, row):
    """Crea l'anagrafica dal contatto e collega il lead. Ritorna paziente_id."""
    cognome = (_g(row, "cognome", "") or "").strip().upper()
    nome = (_g(row, "nome", "") or "").strip().title()
    tel = (_g(row, "telefono", "") or "").strip()
    email = (_g(row, "email", "") or "").strip()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO pazienti (cognome, nome, telefono, email, stato_paziente) "
            "VALUES (%s,%s,%s,%s,'ATTIVO') RETURNING id",
            (cognome, nome, tel, email))
        pid = int(cur.fetchone()[0])
        cur.execute("UPDATE lead_sito SET paziente_id=%s, stato='convertito' WHERE id=%s",
                    (pid, lead_id))
        conn.commit()
        return pid
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _link_firma_privacy(paziente_id, minore=False):
    """Link pubblico di firma, riusando il sistema di firma già in uso."""
    from modules.app_core import _make_sign_token, _public_sign_url
    doc = "privacy_minore" if minore else "privacy_adulto"
    tok = _make_sign_token(int(paziente_id), doc, 48 * 3600)
    return _public_sign_url(tok)


def _canali_invio(url, nome=""):
    """Righe di invio del link firma: email, WhatsApp, Telegram."""
    from urllib.parse import quote
    from modules.app_core import _whatsapp_link, _mailto_link
    saluto = f"Gentile {nome}, " if nome else ""
    testo = (f"{saluto}per completare la registrazione firmi il consenso privacy "
             f"a questo link (valido 48 ore): {url}")
    st.markdown(f"- 📧 **Email** → {_mailto_link('Consenso privacy — Studio The Organism', testo)}")
    st.markdown(f"- 💬 **WhatsApp** → {_whatsapp_link(testo)}")
    st.markdown("- ✈️ **Telegram** → "
                f"https://t.me/share/url?url={quote(url)}&text={quote(testo)}")
    st.code(url, language=None)


# ══════════════════════════════════════════════ lista nel gestionale
def _cf_valido(cf):
    """Controllo formale del codice fiscale italiano (formato + carattere di controllo)."""
    import re as _re
    cf = (cf or "").strip().upper()
    if not _re.match(r"^[A-Z]{6}\d{2}[A-EHLMPRST]\d{2}[A-Z]\d{3}[A-Z]$", cf):
        return False
    dispari = {
        '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
        'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
        'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
        'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23,
    }
    pari = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
        'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
        'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25,
    }
    tot = 0
    for i, ch in enumerate(cf[:15]):
        tot += dispari[ch] if i % 2 == 0 else pari[ch]
    attesa = chr(ord('A') + tot % 26)
    return cf[15] == attesa


def _invia_email_conferma_sale(email, nome, token):
    try:
        from modules.ui_questionari import _invia_email
        link = f"https://gestionale-the-organism.streamlit.app/?sale_conferma={token}"
        corpo = (f"Ciao {nome},\n\nPer confermare la richiesta di informazioni sulla Stanza del Sale, "
                 f"clicca su questo link:\n\n{link}\n\n"
                 f"Se non hai richiesto tu, ignora questa email.")
        _invia_email(email, "Stanza del Sale — confermi la richiesta?", corpo)
    except Exception:
        pass


def ui_public_richiesta_sale(get_conn):
    """Pagina pubblica (no login): richiesta informazioni Stanza del Sale
    (haloterapia). Semplice modulo di contatto, nessun questionario."""
    st.markdown("""<style>
      #MainMenu, footer, header {visibility:hidden}
      .block-container{max-width:600px;padding-top:2rem}
    </style>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="border-left:5px solid #1D6B44;background:#F2F8F4;'
        'padding:18px 22px;border-radius:12px;margin-bottom:22px">'
        '<div style="font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;'
        'color:#4b7a60;font-weight:700">Studio The Organism · Stanza del Sale</div>'
        '<div style="font-size:1.4rem;font-weight:800;color:#14502F;margin-top:4px">'
        'Richiedi informazioni o prenota una seduta</div></div>', unsafe_allow_html=True)

    conn = get_conn()
    try:
        init_lead_db(conn)
    except Exception as e:
        st.error(f"Servizio momentaneamente non disponibile ({e}).")
        return

    if st.session_state.get("_sale_inviato"):
        st.success("Richiesta ricevuta, grazie! Ti ricontattiamo a breve per fissare la seduta.")
        return

    if st.session_state.get("_sale_email_inviata"):
        st.success("Ti abbiamo mandato un'email di conferma. Apri la posta e clicca sul link: "
                   "confermiamo così la richiesta ed evitiamo richieste false.")
        st.caption("Non arriva? Controlla anche lo spam.")
        return

    with st.form("form_sale"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome *")
        cognome = c2.text_input("Cognome *")
        c3, c4 = st.columns(2)
        email = c3.text_input("Email *")
        telefono = c4.text_input("Cellulare *")
        codice_fiscale = st.text_input("Codice fiscale *").strip().upper()
        interesse = st.selectbox("Cosa ti interessa?",
                                  ["Informazioni generali", "Prenotare una seduta singola",
                                   "Un pacchetto di più sedute", "Offerta in corso"])
        note = st.text_area("Note (facoltativo)", height=80,
                             placeholder="Es. per un bambino, per allergie/asma, orari preferiti...")
        consenso = st.checkbox(
            "Ho letto l'informativa privacy e acconsento al trattamento dei "
            "dati per essere ricontattato/a. *")
        st.caption("I dati sono trattati dallo Studio The Organism ai soli fini "
                  "del ricontatto (GDPR art. 6.1.a). Puoi chiederne la "
                  "cancellazione in qualsiasi momento.")
        inviato = st.form_submit_button("Invia richiesta →", type="primary",
                                        use_container_width=True)

    if inviato:
        manca = [l for l, v in [("Nome", nome), ("Cognome", cognome),
                                 ("Email", email), ("Cellulare", telefono),
                                 ("Codice fiscale", codice_fiscale)]
                 if not (v or "").strip()]
        if manca:
            st.error("Campi obbligatori mancanti: " + ", ".join(manca))
        elif "@" not in email or "." not in email.split("@")[-1]:
            st.error("L'indirizzo email non sembra valido.")
        elif len(codice_fiscale) != 16 or not _cf_valido(codice_fiscale):
            st.error("Il codice fiscale non è valido: controlla di averlo scritto correttamente.")
        elif not consenso:
            st.error("Serve il consenso al trattamento dei dati per procedere.")
        else:
            try:
                import secrets as _secrets
                token = _secrets.token_urlsafe(24)
                new_id = salva_lead(conn, {
                    "nome": nome.strip(), "cognome": cognome.strip(),
                    "email": email.strip(), "telefono": telefono.strip(),
                    "eta_bambino": "", "per_chi": f"Stanza del Sale — {interesse}",
                    "src_gioco": "stanza_sale", "dominio": "", "consenso": True,
                })
                cur = conn.cursor()
                cur.execute("UPDATE lead_sito SET codice_fiscale=%s, token_verifica=%s WHERE id=%s",
                            (codice_fiscale, token, new_id))
                conn.commit()
                if (note or "").strip():
                    aggiorna_stato(conn, new_id, "nuovo", note.strip())
                _invia_email_conferma_sale(email.strip(), nome.strip(), token)
                st.session_state["_sale_email_inviata"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Non è stato possibile salvare: {e}")


def ui_public_richiesta_sale_conferma(get_conn):
    """Pagina pubblica (no login): conferma via link email la richiesta Stanza del Sale."""
    conn = get_conn()
    try:
        init_lead_db(conn)
    except Exception as e:
        st.error(f"Servizio non disponibile: {e}")
        return
    st.markdown("""<style>
      #MainMenu, footer, header {visibility:hidden}
      .block-container{max-width:520px;padding-top:2rem}
    </style>""", unsafe_allow_html=True)

    token = st.query_params.get("sale_conferma", "")
    cur = conn.cursor()
    cur.execute("SELECT id, nome, cognome, email, telefono, per_chi, verificato FROM lead_sito WHERE token_verifica = %s LIMIT 1", (token,))
    r = cur.fetchone()
    if not r:
        st.error("Link non valido o già usato.")
        return
    lid, nome, cognome, email, telefono, per_chi, verificato = r
    if not verificato:
        cur.execute("UPDATE lead_sito SET verificato = true WHERE id = %s", (lid,))
        conn.commit()
        _notifica_nuovo_contatto({
            "nome": nome, "cognome": cognome, "email": email, "telefono": telefono,
            "per_chi": per_chi, "eta_bambino": "", "src_gioco": "stanza_sale",
        }, "Stanza del Sale")
    st.success("Email confermata! Grazie: ti ricontattiamo a breve per fissare la seduta.")


def render_contatti_sito(conn):
    st.subheader("📨 Contatti dal sito")
    st.caption("Persone che hanno lasciato i dati dopo i giochi su pnev.it. "
              "L'anagrafica si crea solo quando lo decidi tu.")
    try:
        init_lead_db(conn)
    except Exception as e:
        st.error(f"Tabella contatti non disponibile: {e}")
        return

    with st.expander("📊 Statistiche dell'imbuto", expanded=False):
        render_statistiche(conn)

    with st.expander("✉️ Prova la notifica email", expanded=False):
        st.caption("Verifica che l'avviso di nuovo contatto funzioni.")
        try:
            cfg = st.secrets.get("smtp", {})
            dest = cfg.get("NOTIFICA_A") or cfg.get("USERNAME")
            st.markdown(f"Destinatario avvisi: **{dest or '(non configurato)'}**")
        except Exception:
            dest = None
        if st.button("Invia email di prova", key="lead_test_mail"):
            try:
                from modules.ui_questionari import _invia_email
                _invia_email(dest, "PNEV — prova notifica contatti",
                             "Se leggi questa email, la notifica dei nuovi "
                             "contatti dal sito funziona.")
                st.success(f"Inviata a {dest}. Controlla anche la posta indesiderata.")
            except Exception as e:
                st.error(f"Invio non riuscito: {e}")

    filtro = st.radio("Mostra", ["tutti"] + STATI, horizontal=True, key="lead_filtro")
    try:
        righe = lista_lead(conn, None if filtro == "tutti" else filtro)
    except Exception as e:
        st.error(f"Errore lettura contatti: {e}")
        return

    if not righe:
        st.info("Nessun contatto per questo filtro.")
        return

    st.caption(f"{len(righe)} contatti")
    for r in righe:
        lid = _g(r, "id")
        nome = f"{_g(r,'cognome','') or ''} {_g(r,'nome','') or ''}".strip() or "(senza nome)"
        creato = _g(r, "creato_il")
        try:
            data = creato.strftime("%d/%m/%Y %H:%M") if creato else ""
        except Exception:
            data = str(creato or "")
        dom = _g(r, "dominio") or ""
        dom_label, dom_nota = DOMINI.get(dom, ("", ""))
        stato = _g(r, "stato", "nuovo")
        badge = {"nuovo": "🔵", "contattato": "🟡", "appuntamento fissato": "🟠",
                 "convertito": "🟢", "archiviato": "⚫"}.get(stato, "🔵")
        titolo = f"{badge} {nome} — {data}"
        if dom_label:
            titolo += f" · {dom_label}"

        with st.expander(titolo):
            c1, c2 = st.columns(2)
            c1.markdown(f"**Email:** {_g(r,'email','—')}")
            c1.markdown(f"**Cellulare:** {_g(r,'telefono','—')}")
            c2.markdown(f"**Per chi:** {_g(r,'per_chi','—')}")
            c2.markdown(f"**Età:** {_g(r,'eta_bambino','—')}")

            if dom_label:
                dev = _g(r, "scostamento")
                n_seg = _g(r, "n_segnali")
                gravita = ("marcato" if (dev or 0) >= 2 else "moderato")
                st.markdown(
                    f"**Segnale dai giochi** — area *{dom_label}*, "
                    f"{n_seg or '?'} partite fuori banda, scostamento medio "
                    f"**{dev if dev is not None else '?'}×** la banda di tolleranza "
                    f"({gravita}). Gioco d'origine: `{_g(r,'src_gioco','—')}`.")
                if dom_nota:
                    st.caption(f"Lettura clinica: {dom_nota}")

            if _g(r, "quest_sintesi"):
                if st.checkbox("📋 Mostra questionario compilato", key=f"lead_qs_{lid}"):
                    st.write(_g(r, "quest_sintesi"))
            elif _g(r, "quest_tipo"):
                st.caption("Questionario iniziato ma non completato.")
            else:
                st.caption("Nessun questionario compilato.")

            st.markdown("---")
            # ── Privacy: conversione + link di firma ──────────────────
            paz_id = _g(r, "paziente_id")
            if paz_id:
                st.success(f"Anagrafica creata (paziente id {paz_id}).")
                minore = "figlio" in (_g(r, "per_chi", "") or "").lower()
                st.markdown("**Consenso privacy da firmare** (link valido 48 ore, "
                           "firma col dito da telefono; torna qui firmato)")
                try:
                    url = _link_firma_privacy(paz_id, minore=minore)
                    _canali_invio(url, _g(r, "nome", "") or "")
                except Exception as e:
                    st.error(f"Impossibile generare il link firma: {e}")

                st.markdown("---")
                st.markdown("**Altri questionari da inviare**")
                st.caption("Sul sito ne compila uno solo (quello dell'area emersa "
                          "dai giochi). Gli altri li mandi da qui, quando serve.")
                if st.checkbox("📋 Scegli e invia un questionario", key=f"lead_qinv_{lid}"):
                    try:
                        from modules.ui_questionari import render_genera_link_email
                        render_genera_link_email(conn, paz_id)
                    except Exception as e:
                        st.error(f"Invio questionari non disponibile: {e}")
            else:
                st.caption("Il consenso al ricontatto è già stato dato sul sito. "
                          "Il consenso privacy completo (dati sanitari) si firma "
                          "creando l'anagrafica.")
                if st.button("👤 Crea anagrafica e prepara privacy da firmare",
                             key=f"lead_conv_{lid}", type="primary",
                             use_container_width=True):
                    try:
                        converti_in_paziente(conn, lid, r)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore nella conversione: {e}")

            st.markdown("---")
            cc1, cc2 = st.columns([3, 1])
            nuovo_stato = cc1.selectbox("Stato", STATI,
                                        index=STATI.index(stato) if stato in STATI else 0,
                                        key=f"lead_st_{lid}")
            note = st.text_area("Note", value=_g(r, "note", "") or "",
                                height=68, key=f"lead_nt_{lid}")
            b1, b2 = st.columns(2)
            if b1.button("💾 Salva", key=f"lead_sv_{lid}", use_container_width=True):
                try:
                    aggiorna_stato(conn, lid, nuovo_stato, note)
                    st.success("Aggiornato.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
            if b2.button("🗑️ Elimina", key=f"lead_del_{lid}", use_container_width=True):
                try:
                    elimina_lead(conn, lid)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
