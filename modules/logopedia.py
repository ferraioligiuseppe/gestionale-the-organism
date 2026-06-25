# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  LOGOPEDIA — Valutazione logopedica PNEV con sezione SMOF (Matt. L1) ║
║                                                                      ║
║  Scheda clinica a tab che salva in cartella (tabella                 ║
║  logopedia_valutazioni, dati in JSON → flessibile) e confluisce nel  ║
║  Quadro storico / Assistente PNEV.                                   ║
║                                                                      ║
║  Tab:                                                                ║
║   1. Anamnesi logopedica                                            ║
║   2. Osservazione clinica (scale 0-5)                               ║
║   3. SMOF — Squilibri Muscolari Oro-Facciali                        ║
║        · Miofunzionale (respirazione, deglutizione, lingua…)        ║
║        · Linguaggio / Fonologia                                     ║
║        · Fluenza / Balbuzie                                         ║
║   4. Profilo funzionale + salvataggio                               ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import datetime
import streamlit as st

SCALA = ["—", "0 assente", "1", "2 emergente", "3 parziale", "4 adeguato", "5 generalizzato"]
SI_NO = ["—", "Sì", "No", "In parte"]


def _assicura_tabella(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS logopedia_valutazioni(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data TIMESTAMP DEFAULT NOW(),
            tipo TEXT, dati JSONB, sintesi TEXT);""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _ultima(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati FROM logopedia_valutazioni WHERE paziente_id=%s "
                    "ORDER BY data DESC LIMIT 1", (paz_id,))
        r = cur.fetchone()
        if r and r[0]:
            return r[0] if isinstance(r[0], dict) else json.loads(r[0])
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    return {}


def render_logopedia(conn=None, paz_id=None, paziente=None):
    st.header("🗣️ Logopedia PNEV")
    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    _assicura_tabella(conn)
    _assicura_tabella_sedute(conn)

    modo = st.radio("Sezione", ["📋 Valutazione + SMOF", "📅 Diario sedute"],
                    horizontal=True, key="logo_modo")
    if modo == "📅 Diario sedute":
        _render_diario(conn, paz_id)
        return

    st.caption("Valutazione logopedica con sezione SMOF (oro-mio-funzionale, "
               "linguaggio, fluenza). Si salva in cartella e confluisce nel "
               "Quadro storico e nell'Assistente PNEV.")

    pre = _ultima(conn, paz_id)
    if pre:
        st.success("Caricata l'ultima valutazione: i campi sono precompilati, "
                   "modificali e salva per crearne una nuova.")

    g = lambda *k: _get(pre, *k)
    dati = {}

    t1, t2, t3, t4 = st.tabs([
        "1 · Anamnesi", "2 · Osservazione", "3 · SMOF", "4 · Profilo & salva"])

    # ── 1. ANAMNESI ───────────────────────────────────────────────────
    with t1:
        st.markdown("#### Motivo dell'invio")
        dati["motivo"] = st.text_area(
            "Motivo / quesito", value=g("motivo"),
            placeholder="Ritardo di linguaggio, dislalia, deglutizione atipica, balbuzie…",
            key="logo_motivo")
        c1, c2 = st.columns(2)
        with c1:
            dati["inviante"] = st.selectbox(
                "Inviante", ["—", "Famiglia", "Pediatra", "NPI", "Scuola",
                             "Odontoiatra", "ORL", "Ortottista", "Altro"],
                index=_idx(["—", "Famiglia", "Pediatra", "NPI", "Scuola",
                            "Odontoiatra", "ORL", "Altro"], g("inviante")),
                key="logo_inviante")
        with c2:
            dati["diagnosi_pregresse"] = st.text_input(
                "Diagnosi / sospetti già presenti", value=g("diagnosi_pregresse"),
                key="logo_diag_pre")
        st.markdown("#### Anamnesi dello sviluppo")
        c3, c4 = st.columns(2)
        with c3:
            dati["gravidanza_parto"] = st.text_area(
                "Gravidanza e parto", value=g("gravidanza_parto"), height=80,
                key="logo_grav")
            dati["sviluppo_motorio"] = st.text_area(
                "Sviluppo motorio", value=g("sviluppo_motorio"), height=80,
                key="logo_mot")
            dati["alimentazione"] = st.text_area(
                "Alimentazione (suzione, svezzamento, masticazione, selettività)",
                value=g("alimentazione"), height=80, key="logo_alim")
        with c4:
            dati["sviluppo_linguistico"] = st.text_area(
                "Sviluppo linguistico (lallazione, prime parole/frasi)",
                value=g("sviluppo_linguistico"), height=80, key="logo_ling")
            dati["respiro_sonno"] = st.text_area(
                "Respirazione e sonno (respiro orale, russamento, apnee)",
                value=g("respiro_sonno"), height=80, key="logo_resp")
            dati["udito_orl"] = st.text_area(
                "Udito / ORL / odontoiatria (otiti, adenoidi, occlusione)",
                value=g("udito_orl"), height=80, key="logo_orl")
        dati["familiarita"] = st.text_input(
            "Familiarità (linguaggio, DSA, balbuzie, neurosviluppo)",
            value=g("familiarita"), key="logo_fam")

    # ── 2. OSSERVAZIONE ───────────────────────────────────────────────
    with t2:
        st.markdown("#### Osservazione clinica (scala 0–5)")
        oss = {}
        voci = ["Relazione / aggancio", "Attenzione / tenuta sul compito",
                "Comprensione consegne", "Comunicazione spontanea",
                "Gioco (funzionale/simbolico)", "Regolazione / frustrazione",
                "Affaticabilità"]
        cols = st.columns(2)
        for i, v in enumerate(voci):
            with cols[i % 2]:
                oss[v] = st.selectbox(v, SCALA,
                                      index=_idx(SCALA, g("osservazione", v)),
                                      key=f"logo_oss_{i}")
        dati["osservazione"] = oss
        dati["osservazione_note"] = st.text_area(
            "Note di osservazione", value=g("osservazione_note"), key="logo_oss_note")

    # ── 3. SMOF ───────────────────────────────────────────────────────
    with t3:
        st.markdown("### SMOF — Squilibri Muscolari Oro-Facciali")
        st.caption("Tre sotto-blocchi: oro-mio-funzionale, linguaggio/fonologia, "
                   "fluenza/balbuzie.")
        s1, s2, s3 = st.tabs(["👄 Miofunzionale", "🗨️ Linguaggio/Fonologia",
                              "🌀 Fluenza/Balbuzie"])

        # 3a — Oro-mio-funzionale
        with s1:
            mf = {}
            c1, c2 = st.columns(2)
            with c1:
                mf["respirazione"] = st.selectbox(
                    "Respirazione", ["—", "Nasale", "Orale", "Mista"],
                    index=_idx(["—", "Nasale", "Orale", "Mista"], g("mf", "respirazione")),
                    key="logo_mf_resp")
                mf["deglutizione"] = st.selectbox(
                    "Deglutizione", ["—", "Tipica", "Atipica", "Con interposizione linguale"],
                    index=_idx(["—", "Tipica", "Atipica", "Con interposizione linguale"],
                               g("mf", "deglutizione")), key="logo_mf_deg")
                mf["postura_linguale"] = st.text_input(
                    "Postura linguale (riposo/fonazione)", value=g("mf", "postura_linguale"),
                    key="logo_mf_post")
                mf["masticazione"] = st.selectbox(
                    "Masticazione", ["—", "Bilaterale", "Monolaterale", "Inefficace"],
                    index=_idx(["—", "Bilaterale", "Monolaterale", "Inefficace"],
                               g("mf", "masticazione")), key="logo_mf_mast")
            with c2:
                mf["frenulo"] = st.selectbox(
                    "Frenulo linguale", ["—", "Normale", "Corto/limitante", "Da valutare"],
                    index=_idx(["—", "Normale", "Corto/limitante", "Da valutare"],
                               g("mf", "frenulo")), key="logo_mf_fren")
                mf["tono_orofacciale"] = st.selectbox(
                    "Tono oro-facciale", ["—", "Normale", "Ipotono", "Ipertono", "Asimmetrie"],
                    index=_idx(["—", "Normale", "Ipotono", "Ipertono", "Asimmetrie"],
                               g("mf", "tono_orofacciale")), key="logo_mf_tono")
                mf["occlusione"] = st.text_input(
                    "Occlusione / palato (morso, cross-bite, palato ogivale)",
                    value=g("mf", "occlusione"), key="logo_mf_occl")
                mf["abitudini"] = st.text_input(
                    "Abitudini viziate (ciuccio, dito, onicofagia)",
                    value=g("mf", "abitudini"), key="logo_mf_abit")
            mf["competenza_labiale"] = st.selectbox(
                "Competenza labiale", SCALA, index=_idx(SCALA, g("mf", "competenza_labiale")),
                key="logo_mf_lab")
            mf["note"] = st.text_area("Note miofunzionali", value=g("mf", "note"),
                                      key="logo_mf_note")
            dati["mf"] = mf

        # 3b — Linguaggio / Fonologia
        with s2:
            lg = {}
            st.markdown("**Comprensione e produzione (scala 0–5)**")
            c1, c2 = st.columns(2)
            with c1:
                lg["comprensione"] = st.selectbox(
                    "Comprensione linguistica", SCALA,
                    index=_idx(SCALA, g("lg", "comprensione")), key="logo_lg_compr")
                lg["lessico"] = st.selectbox(
                    "Lessico (recettivo/espressivo)", SCALA,
                    index=_idx(SCALA, g("lg", "lessico")), key="logo_lg_less")
                lg["morfosintassi"] = st.selectbox(
                    "Morfosintassi", SCALA,
                    index=_idx(SCALA, g("lg", "morfosintassi")), key="logo_lg_morfo")
            with c2:
                lg["fonologia"] = st.selectbox(
                    "Fonologia / processi", SCALA,
                    index=_idx(SCALA, g("lg", "fonologia")), key="logo_lg_fono")
                lg["narrazione"] = st.selectbox(
                    "Narrazione / discorso", SCALA,
                    index=_idx(SCALA, g("lg", "narrazione")), key="logo_lg_narr")
                lg["metafonologia"] = st.selectbox(
                    "Metafonologia", SCALA,
                    index=_idx(SCALA, g("lg", "metafonologia")), key="logo_lg_meta")
            lg["intelligibilita"] = st.selectbox(
                "Intelligibilità in contesto non familiare",
                ["—", "Buona", "Parziale", "Ridotta", "Molto ridotta"],
                index=_idx(["—", "Buona", "Parziale", "Ridotta", "Molto ridotta"],
                           g("lg", "intelligibilita")), key="logo_lg_intel")
            lg["errori_tipici"] = st.text_area(
                "Errori tipici (sostituzioni, omissioni, distorsioni)",
                value=g("lg", "errori_tipici"), key="logo_lg_err")
            dati["lg"] = lg

        # 3c — Fluenza / Balbuzie
        with s3:
            fl = {}
            fl["presente"] = st.selectbox(
                "Disfluenza presente?", SI_NO, index=_idx(SI_NO, g("fl", "presente")),
                key="logo_fl_pres")
            c1, c2 = st.columns(2)
            with c1:
                fl["tipo"] = st.multiselect(
                    "Tipo di disfluenza",
                    ["Ripetizioni di suono", "Ripetizioni di sillaba",
                     "Prolungamenti", "Blocchi", "Esitazioni", "Revisioni"],
                    default=g("fl", "tipo") or [], key="logo_fl_tipo")
                fl["tensione"] = st.selectbox(
                    "Tensione / sforzo", SCALA, index=_idx(SCALA, g("fl", "tensione")),
                    key="logo_fl_tens")
            with c2:
                fl["secondari"] = st.text_input(
                    "Comportamenti secondari (tic, evitamenti, sguardo)",
                    value=g("fl", "secondari"), key="logo_fl_sec")
                fl["impatto"] = st.selectbox(
                    "Impatto comunicativo/emotivo", SCALA,
                    index=_idx(SCALA, g("fl", "impatto")), key="logo_fl_imp")
            fl["frequenza"] = st.text_input(
                "Frequenza/percentuale sillabe disfluenti (se misurata)",
                value=g("fl", "frequenza"), key="logo_fl_freq")
            fl["note"] = st.text_area("Note fluenza", value=g("fl", "note"),
                                      key="logo_fl_note")
            dati["fl"] = fl

    # ── 4. PROFILO & SALVA ────────────────────────────────────────────
    with t4:
        st.markdown("#### Profilo funzionale logopedico")
        dati["punti_forza"] = st.text_area(
            "Punti di forza", value=g("punti_forza"), key="logo_forza")
        dati["fragilita"] = st.text_area(
            "Fragilità prevalenti", value=g("fragilita"), key="logo_frag")
        dati["impatto_funzionale"] = st.text_area(
            "Impatto funzionale (vita quotidiana, scuola)",
            value=g("impatto_funzionale"), key="logo_impatto")
        dati["ipotesi"] = st.text_area(
            "Ipotesi funzionale", value=g("ipotesi"), key="logo_ipotesi")
        dati["priorita"] = st.text_area(
            "Priorità terapeutiche", value=g("priorita"), key="logo_prio")

        st.markdown("---")
        if st.button("💾 Salva valutazione in cartella", type="primary",
                     key="logo_save"):
            sintesi = _sintesi(dati)
            if _salva(conn, paz_id, dati, sintesi):
                st.success("Valutazione logopedica salvata. La trovi nel Quadro storico.")
            else:
                st.error("Salvataggio non riuscito.")


def _get(d, *keys):
    cur = d or {}
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, "")
        else:
            return ""
    return cur if cur is not None else ""


def _idx(opzioni, val):
    try:
        return opzioni.index(val) if val in opzioni else 0
    except Exception:
        return 0


def _sintesi(dati) -> str:
    parti = []
    if dati.get("motivo"):
        parti.append("Motivo: " + dati["motivo"][:120])
    if dati.get("ipotesi"):
        parti.append("Ipotesi: " + dati["ipotesi"][:120])
    if dati.get("priorita"):
        parti.append("Priorità: " + dati["priorita"][:120])
    return " · ".join(parti)


def _salva(conn, paz_id, dati, sintesi) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO logopedia_valutazioni(paziente_id, tipo, dati, sintesi) "
                    "VALUES(%s,%s,%s,%s)",
                    (paz_id, "valutazione", json.dumps(dati, ensure_ascii=False), sintesi))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════
#  L2 — DIARIO SEDUTE LOGOPEDICHE
# ══════════════════════════════════════════════════════════════════════

AREE_LAVORO = ["Oro-mio-funzionale", "Articolazione/Fonologia", "Linguaggio",
               "Fluenza/Balbuzie", "Deglutizione", "Respirazione",
               "Metafonologia", "Comunicazione/Pragmatica", "Altro"]
RISPOSTA = ["—", "🟢 Buona", "🟡 Parziale", "🔴 Scarsa"]


def _assicura_tabella_sedute(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS logopedia_sedute(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data_seduta DATE, numero INT,
            aree TEXT, obiettivo TEXT, attivita TEXT,
            risposta TEXT, compiti TEXT, note TEXT,
            creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _render_diario(conn, paz_id):
    st.caption("Quaderno di lavoro: registra ogni seduta logopedica. Le sedute "
               "entrano nel Quadro storico del paziente.")

    # conteggio per numerazione automatica
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM logopedia_sedute WHERE paziente_id=%s", (paz_id,))
        n_fatte = cur.fetchone()[0] or 0
    except Exception:
        n_fatte = 0
        try:
            conn.rollback()
        except Exception:
            pass

    with st.expander("➕ Nuova seduta", expanded=True):
        with st.form("logo_seduta", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                data_s = st.date_input("Data seduta", value=datetime.date.today(),
                                       key="logo_sd_data")
            with c2:
                numero = st.number_input("N° seduta", min_value=1, step=1,
                                         value=int(n_fatte) + 1, key="logo_sd_num")
            aree = st.multiselect("Aree di lavoro", AREE_LAVORO, key="logo_sd_aree")
            obiettivo = st.text_input("Obiettivo della seduta", key="logo_sd_ob")
            attivita = st.text_area("Attività svolte", height=90, key="logo_sd_att")
            c3, c4 = st.columns(2)
            with c3:
                risposta = st.selectbox("Risposta del bambino", RISPOSTA, key="logo_sd_risp")
            with c4:
                compiti = st.text_input("Compiti a casa", key="logo_sd_comp")
            note = st.text_area("Note", height=70, key="logo_sd_note")
            if st.form_submit_button("💾 Salva seduta", type="primary"):
                if _salva_seduta(conn, paz_id, data_s, numero, aree, obiettivo,
                                 attivita, risposta, compiti, note):
                    st.success(f"Seduta n° {numero} salvata.")
                    st.rerun()
                else:
                    st.error("Salvataggio non riuscito.")

    st.markdown(f"#### Sedute registrate ({n_fatte})")
    _elenco_sedute(conn, paz_id)


def _salva_seduta(conn, paz_id, data_s, numero, aree, ob, att, risp, comp, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO logopedia_sedute(paziente_id, data_seduta, numero,
            aree, obiettivo, attivita, risposta, compiti, note)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, data_s, int(numero), ", ".join(aree), ob, att, risp, comp, note))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco_sedute(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, data_seduta, numero, aree, obiettivo, attivita,
            risposta, compiti, note FROM logopedia_sedute
            WHERE paziente_id=%s ORDER BY data_seduta DESC, numero DESC""", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try:
            conn.rollback()
        except Exception:
            pass
    if not righe:
        st.caption("Nessuna seduta registrata per ora.")
        return
    for rid, ds, num, aree, ob, att, risp, comp, note in righe:
        ds_str = ds.strftime("%d/%m/%Y") if ds else ""
        titolo = f"**Seduta n° {num}** — {ds_str}"
        if risp and risp != "—":
            titolo += f"  ·  {risp}"
        st.markdown(titolo)
        if aree:
            st.caption("Aree: " + aree)
        if ob:
            st.markdown(f"🎯 {ob}")
        if att:
            st.markdown(att)
        det = []
        if comp:
            det.append(f"📝 Compiti: {comp}")
        if note:
            det.append(note)
        if det:
            st.caption(" · ".join(det))
        if st.button("🗑 Elimina", key=f"logo_sd_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM logopedia_sedute WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)
