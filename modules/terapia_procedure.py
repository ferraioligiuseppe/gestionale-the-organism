# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  PROGRAMMA PNEV — Libreria procedure + protocollo del paziente       ║
║                                                                      ║
║  Il cuore "componibile" della terapia PNEV:                          ║
║                                                                      ║
║  📚 LIBRERIA PROCEDURE  — magazzino di procedure, organizzate per     ║
║     approccio (Terapia visiva, INPP, Movimenti ritmici, Miofunzio-   ║
║     nale, MAPS, Castagnini…) e, per la visiva, per STEP              ║
║     (Monoculare → Bioculare → Binoculare). Pre-riempita, editabile.  ║
║                                                                      ║
║  🧩 PROGRAMMA DEL PAZIENTE — il clinico PESCA le procedure (anche da  ║
║     approcci diversi) e compone il protocollo personale, che può     ║
║     VARIARE nel percorso (aggiungi/togli, fai avanzare di stato).    ║
║     Gli stati conclusi confluiscono negli Esiti → Apprendimento PNEV.║
╚══════════════════════════════════════════════════════════════════════╝
"""

import datetime
import streamlit as st

APPROCCI = ["Terapia visiva", "INPP / Riflessi primitivi", "Movimenti ritmici",
            "Terapia miofunzionale", "MAPS", "Castagnini", "Altro"]
STEP_VISIVA = ["🔵 Monoculare", "🟢 Bioculare", "🟣 Binoculare"]
STATI = ["⚪ Da iniziare", "🟦 In corso", "🟢 Acquisita", "⏸️ Sospesa"]

# ── Libreria iniziale (esempi da correggere: 2A) ──────────────────────
_SEED = [
    # Terapia visiva — Monoculare
    ("Terapia visiva", "🔵 Monoculare", "Anti-soppressione monoculare",
     "Attivare la consapevolezza del singolo occhio"),
    ("Terapia visiva", "🔵 Monoculare", "Flipper accomodativo monoculare",
     "Flessibilità accomodativa per occhio"),
    ("Terapia visiva", "🔵 Monoculare", "Motilità oculare monoculare",
     "Inseguimenti e saccadi per occhio"),
    ("Terapia visiva", "🔵 Monoculare", "Localizzazione / puntamento",
     "Coordinazione occhio-mano monoculare"),
    # Terapia visiva — Bioculare
    ("Terapia visiva", "🟢 Bioculare", "Anti-soppressione bioculare",
     "Mantenere entrambi gli occhi attivi insieme"),
    ("Terapia visiva", "🟢 Bioculare", "Flipper bioculare",
     "Flessibilità accomodativa con i due occhi"),
    ("Terapia visiva", "🟢 Bioculare", "Vergenze bioculari",
     "Avvio del controllo di convergenza/divergenza"),
    # Terapia visiva — Binoculare
    ("Terapia visiva", "🟣 Binoculare", "Vergenze fusionali",
     "Ampiezza e flessibilità di vergenza"),
    ("Terapia visiva", "🟣 Binoculare", "Stereopsi",
     "Sviluppo della visione tridimensionale"),
    ("Terapia visiva", "🟣 Binoculare", "Integrazione visuo-motoria binoculare",
     "Coordinazione visione-movimento in binoculare"),
    # INPP
    ("INPP / Riflessi primitivi", "—", "Inibizione TLR",
     "Integrazione del riflesso tonico labirintico"),
    ("INPP / Riflessi primitivi", "—", "Inibizione ATNR",
     "Integrazione del riflesso tonico asimmetrico del collo"),
    ("INPP / Riflessi primitivi", "—", "Inibizione STNR",
     "Integrazione del riflesso tonico simmetrico del collo"),
    ("INPP / Riflessi primitivi", "—", "Inibizione Moro",
     "Integrazione del riflesso di Moro"),
    ("INPP / Riflessi primitivi", "—", "Inibizione Spinale di Galant",
     "Integrazione del riflesso spinale di Galant"),
    # Movimenti ritmici
    ("Movimenti ritmici", "—", "RMT passivi",
     "Movimenti ritmici passivi (guidati)"),
    ("Movimenti ritmici", "—", "RMT attivi",
     "Movimenti ritmici attivi (autonomi)"),
    # Miofunzionale
    ("Terapia miofunzionale", "—", "Respirazione nasale",
     "Ripristino del pattern respiratorio nasale"),
    ("Terapia miofunzionale", "—", "Postura linguale a riposo",
     "Corretta postura della lingua a riposo"),
    ("Terapia miofunzionale", "—", "Deglutizione corretta",
     "Rieducazione della deglutizione"),
    ("Terapia miofunzionale", "—", "Tonificazione labiale",
     "Competenza e tono labiale"),
    # MAPS
    ("MAPS", "—", "Protocollo MAPS base",
     "Stimolazione multisensoriale MAPS"),
    # Castagnini
    ("Castagnini", "—", "Sequenze Castagnini",
     "Sequenze motorie secondo Castagnini"),
]


def _assicura_tabelle(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS terapia_libreria(
            id BIGSERIAL PRIMARY KEY, approccio TEXT, step TEXT,
            nome TEXT, obiettivo TEXT, istruzioni TEXT,
            attiva BOOLEAN DEFAULT TRUE, creato TIMESTAMP DEFAULT NOW());""")
        cur.execute("""CREATE TABLE IF NOT EXISTS terapia_programma(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            procedura_id BIGINT, approccio TEXT, step TEXT, nome TEXT,
            stato TEXT, note TEXT, data_inserim DATE DEFAULT CURRENT_DATE,
            creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
        # seed solo se la libreria è vuota
        cur.execute("SELECT COUNT(*) FROM terapia_libreria")
        if (cur.fetchone()[0] or 0) == 0:
            for appr, step, nome, ob in _SEED:
                cur.execute("INSERT INTO terapia_libreria(approccio, step, nome, obiettivo) "
                            "VALUES(%s,%s,%s,%s)", (appr, step, nome, ob))
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def render_programma(conn=None, paz_id=None, paziente=None):
    st.header("🧩 Programma PNEV — procedure")
    st.caption("Componi il protocollo del paziente pescando dalla libreria di "
               "procedure. Approcci come scaffali, procedure come mattoni: "
               "li combini e li fai variare durante il percorso.")

    if conn is None:
        st.info("Connessione non disponibile.")
        return

    _assicura_tabelle(conn)

    t_prog, t_libr = st.tabs(["🧩 Programma del paziente", "📚 Libreria procedure"])
    with t_prog:
        _render_programma_paziente(conn, paz_id)
    with t_libr:
        _render_libreria(conn)


# ══════════════════════════════════════════════════════════════════════
#  PROGRAMMA DEL PAZIENTE
# ══════════════════════════════════════════════════════════════════════

def _render_programma_paziente(conn, paz_id):
    if not paz_id:
        st.info("Seleziona prima un paziente (header in alto).")
        return

    # ── Aggiungi procedure dalla libreria ─────────────────────────────
    with st.expander("➕ Aggiungi procedure al programma", expanded=True):
        appr = st.selectbox("Approccio", APPROCCI, key="prog_add_appr")
        proc = _procedure_libreria(conn, appr)
        if not proc:
            st.caption("Nessuna procedura in libreria per questo approccio "
                       "(aggiungile nel tab Libreria).")
        else:
            etichette = {f"{p['step']+' · ' if p['step'] and p['step']!='—' else ''}{p['nome']}": p
                         for p in proc}
            scelte = st.multiselect("Procedure da aggiungere", list(etichette.keys()),
                                    key="prog_add_sel")
            if st.button("➕ Aggiungi al programma", type="primary", key="prog_add_btn"):
                n = 0
                for et in scelte:
                    p = etichette[et]
                    if _aggiungi_al_programma(conn, paz_id, p):
                        n += 1
                if n:
                    st.success(f"{n} procedure aggiunte al programma.")
                    st.rerun()

    # ── Programma attuale, raggruppato per approccio ──────────────────
    righe = _programma_paziente(conn, paz_id)
    if not righe:
        st.info("Programma ancora vuoto: aggiungi le prime procedure qui sopra.")
        return

    st.markdown("#### Protocollo attuale")
    per_appr = {}
    for r in righe:
        per_appr.setdefault(r["approccio"] or "—", []).append(r)

    for appr, lista in per_appr.items():
        st.markdown(f"##### {appr}")
        for r in lista:
            rid = r["id"]
            testa = f"**{r['nome']}**"
            if r.get("step") and r["step"] != "—":
                testa += f"  ·  _{r['step']}_"
            st.markdown(testa)
            c1, c2, c3 = st.columns([3, 3, 1])
            with c1:
                stato = st.selectbox(
                    "Stato", STATI,
                    index=STATI.index(r["stato"]) if r.get("stato") in STATI else 0,
                    key=f"prog_st_{rid}")
            with c2:
                note = st.text_input("Note", value=r.get("note") or "",
                                     key=f"prog_note_{rid}")
            with c3:
                st.write("")
                st.write("")
                if st.button("💾", key=f"prog_save_{rid}", help="Aggiorna"):
                    _aggiorna_programma(conn, rid, stato, note, paz_id, r)
                    st.rerun()
            if st.button("🗑 Togli dal programma", key=f"prog_del_{rid}"):
                _togli_dal_programma(conn, rid)
                st.rerun()
            st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                        unsafe_allow_html=True)


def _procedure_libreria(conn, approccio):
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, approccio, step, nome, obiettivo FROM terapia_libreria "
                    "WHERE approccio=%s AND attiva=TRUE ORDER BY step, nome", (approccio,))
        return [{"id": r[0], "approccio": r[1], "step": r[2], "nome": r[3],
                 "obiettivo": r[4]} for r in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _aggiungi_al_programma(conn, paz_id, p) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO terapia_programma(paziente_id, procedura_id, approccio,
            step, nome, stato) VALUES(%s,%s,%s,%s,%s,%s)""",
            (paz_id, p["id"], p["approccio"], p.get("step") or "—", p["nome"],
             "⚪ Da iniziare"))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _programma_paziente(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, approccio, step, nome, stato, note FROM terapia_programma
            WHERE paziente_id=%s ORDER BY approccio, step, creato""", (paz_id,))
        return [{"id": r[0], "approccio": r[1], "step": r[2], "nome": r[3],
                 "stato": r[4], "note": r[5]} for r in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _aggiorna_programma(conn, rid, stato, note, paz_id, r):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE terapia_programma SET stato=%s, note=%s WHERE id=%s",
                    (stato, note, rid))
        conn.commit()
        # esito → Apprendimento PNEV quando una procedura è acquisita/sospesa
        if stato in ("🟢 Acquisita", "⏸️ Sospesa"):
            esito = "🟢 Migliorato" if stato == "🟢 Acquisita" else "⚪ Non valutabile"
            try:
                cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
                    id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
                    data TIMESTAMP DEFAULT NOW(),
                    intervento TEXT, esito TEXT, note TEXT);""")
                cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                            "VALUES(%s,%s,%s,%s)",
                            (paz_id, f"{r.get('approccio','')} — {r.get('nome','')}",
                             esito, "Da procedura del programma"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _togli_dal_programma(conn, rid):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM terapia_programma WHERE id=%s", (rid,))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  LIBRERIA PROCEDURE
# ══════════════════════════════════════════════════════════════════════

def _render_libreria(conn):
    st.caption("Il magazzino delle procedure. Pre-riempito con esempi: correggi, "
               "aggiungi le tue, disattiva quelle che non usi.")

    with st.expander("➕ Nuova procedura", expanded=False):
        with st.form("libr_new", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                appr = st.selectbox("Approccio", APPROCCI, key="libr_appr")
            with c2:
                step = st.selectbox("Step (solo Terapia visiva)",
                                    ["—"] + STEP_VISIVA, key="libr_step")
            nome = st.text_input("Nome procedura", key="libr_nome")
            ob = st.text_input("Obiettivo", key="libr_ob")
            istr = st.text_area("Istruzioni (facoltative)", height=80, key="libr_istr")
            if st.form_submit_button("💾 Aggiungi alla libreria", type="primary"):
                if nome.strip():
                    if _salva_procedura(conn, appr, step, nome, ob, istr):
                        st.success("Procedura aggiunta.")
                        st.rerun()
                else:
                    st.warning("Scrivi il nome della procedura.")

    filtro = st.selectbox("Mostra approccio", ["Tutti"] + APPROCCI, key="libr_filtro")
    righe = _tutte_procedure(conn, None if filtro == "Tutti" else filtro)
    if not righe:
        st.caption("Libreria vuota.")
        return

    per_appr = {}
    for r in righe:
        per_appr.setdefault(r["approccio"] or "—", []).append(r)
    for appr, lista in per_appr.items():
        st.markdown(f"##### {appr}  ({len(lista)})")
        for r in lista:
            rid = r["id"]
            riga = f"{'🔴 ' if not r['attiva'] else ''}**{r['nome']}**"
            if r.get("step") and r["step"] != "—":
                riga += f"  ·  _{r['step']}_"
            if r.get("obiettivo"):
                riga += f" — {r['obiettivo']}"
            cc1, cc2 = st.columns([6, 1])
            with cc1:
                st.markdown(riga)
            with cc2:
                lbl = "Disattiva" if r["attiva"] else "Riattiva"
                if st.button(lbl, key=f"libr_tog_{rid}"):
                    _toggle_procedura(conn, rid, not r["attiva"])
                    st.rerun()


def _salva_procedura(conn, appr, step, nome, ob, istr) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO terapia_libreria(approccio, step, nome, obiettivo, istruzioni) "
                    "VALUES(%s,%s,%s,%s,%s)", (appr, step, nome, ob, istr))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _tutte_procedure(conn, approccio):
    try:
        cur = conn.cursor()
        if approccio:
            cur.execute("SELECT id, approccio, step, nome, obiettivo, attiva "
                        "FROM terapia_libreria WHERE approccio=%s ORDER BY step, nome",
                        (approccio,))
        else:
            cur.execute("SELECT id, approccio, step, nome, obiettivo, attiva "
                        "FROM terapia_libreria ORDER BY approccio, step, nome")
        return [{"id": r[0], "approccio": r[1], "step": r[2], "nome": r[3],
                 "obiettivo": r[4], "attiva": r[5]} for r in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _toggle_procedura(conn, rid, attiva):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE terapia_libreria SET attiva=%s WHERE id=%s", (attiva, rid))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
