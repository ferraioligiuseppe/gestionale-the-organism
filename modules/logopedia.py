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
    _assicura_tabella_obiettivi(conn)

    modo = st.radio("Sezione", ["📋 Valutazione + SMOF", "📅 Diario sedute",
                                "🎯 Obiettivi & monitoraggio", "📄 Relazione PDF"],
                    horizontal=True, key="logo_modo")
    if modo == "📅 Diario sedute":
        _render_diario(conn, paz_id)
        return
    if modo == "🎯 Obiettivi & monitoraggio":
        _render_obiettivi(conn, paz_id)
        return
    if modo == "📄 Relazione PDF":
        _render_relazione(conn, paz_id, paziente)
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

        try:
            from .stampa_helper import scheda_stampabile_html, bottone_stampa
            nome_p = ""
            if isinstance(paziente, dict):
                nome_p = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
            mf, lg, fl = dati.get("mf", {}), dati.get("lg", {}), dati.get("fl", {})
            html_val = scheda_stampabile_html(
                f"Valutazione logopedica — {nome_p or paz_id}",
                "Scheda SMOF — Studio The Organism",
                [("Anamnesi", [
                    ("Motivo", dati.get("motivo")), ("Inviante", dati.get("inviante")),
                    ("Diagnosi pregresse", dati.get("diagnosi_pregresse")),
                    ("Familiarità", dati.get("familiarita")),
                    ("Sviluppo linguistico", dati.get("sviluppo_linguistico")),
                    ("Alimentazione", dati.get("alimentazione")),
                    ("Respiro/sonno", dati.get("respiro_sonno")),
                ]),
                 ("SMOF — Miofunzionale", [(k.replace("_", " ").title(), v)
                                          for k, v in mf.items()]),
                 ("SMOF — Linguaggio/Fonologia", [(k.replace("_", " ").title(), v)
                                                  for k, v in lg.items()]),
                 ("SMOF — Fluenza/Balbuzie", [(k.replace("_", " ").title(),
                                              ", ".join(v) if isinstance(v, list) else v)
                                             for k, v in fl.items()]),
                 ("Profilo funzionale", [
                     ("Punti di forza", dati.get("punti_forza")),
                     ("Fragilità", dati.get("fragilita")),
                     ("Impatto funzionale", dati.get("impatto_funzionale")),
                     ("Ipotesi funzionale", dati.get("ipotesi")),
                     ("Priorità terapeutiche", dati.get("priorita")),
                 ])])
            bottone_stampa(html_val, f"logopedia_{nome_p or paz_id}",
                           key=f"logo_stampa_{paz_id}")
        except Exception:
            pass

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


# ══════════════════════════════════════════════════════════════════════
#  L3 — OBIETTIVI & MONITORAGGIO
# ══════════════════════════════════════════════════════════════════════

STATO_OB = ["🟦 In corso", "🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"]


def _assicura_tabella_obiettivi(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS logopedia_obiettivi(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            area TEXT, descrizione TEXT,
            baseline INT, attuale INT, target INT,
            stato TEXT, data_inizio DATE, data_rivalut DATE,
            note TEXT, creato TIMESTAMP DEFAULT NOW());""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _render_obiettivi(conn, paz_id):
    st.caption("Definisci gli obiettivi terapeutici e aggiornane il livello nel "
               "tempo (scala 0–10). Alla chiusura, l'esito confluisce "
               "nell'apprendimento PNEV.")

    with st.expander("➕ Nuovo obiettivo", expanded=True):
        with st.form("logo_ob_new", clear_on_submit=True):
            area = st.selectbox("Area", AREE_LAVORO, key="logo_ob_area")
            descr = st.text_input("Obiettivo (in positivo, osservabile)",
                                  placeholder="es. Deglutizione con postura linguale corretta",
                                  key="logo_ob_descr")
            c1, c2, c3 = st.columns(3)
            with c1:
                baseline = st.slider("Livello iniziale", 0, 10, 2, key="logo_ob_base")
            with c2:
                target = st.slider("Target", 0, 10, 8, key="logo_ob_targ")
            with c3:
                data_riv = st.date_input("Rivalutazione prevista",
                                         value=datetime.date.today() + datetime.timedelta(weeks=10),
                                         key="logo_ob_riv")
            if st.form_submit_button("💾 Crea obiettivo", type="primary"):
                if descr.strip():
                    if _salva_obiettivo(conn, paz_id, area, descr, baseline, target, data_riv):
                        st.success("Obiettivo creato.")
                        st.rerun()
                    else:
                        st.error("Salvataggio non riuscito.")
                else:
                    st.warning("Scrivi l'obiettivo.")

    st.markdown("#### Obiettivi del paziente")
    _elenco_obiettivi(conn, paz_id)


def _salva_obiettivo(conn, paz_id, area, descr, baseline, target, data_riv) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO logopedia_obiettivi(paziente_id, area, descrizione,
            baseline, attuale, target, stato, data_inizio, data_rivalut)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (paz_id, area, descr, int(baseline), int(baseline), int(target),
             "🟦 In corso", datetime.date.today(), data_riv))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco_obiettivi(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, area, descrizione, baseline, attuale, target,
            stato, data_inizio, data_rivalut FROM logopedia_obiettivi
            WHERE paziente_id=%s ORDER BY creato DESC""", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        righe = []
        try:
            conn.rollback()
        except Exception:
            pass
    if not righe:
        st.caption("Nessun obiettivo definito per ora.")
        return
    for rid, area, descr, base, attuale, target, stato, dini, driv in righe:
        st.markdown(f"**{descr}**  ·  _{area}_")
        # barra di avanzamento baseline → attuale → target
        rng = max(1, (target or 10) - (base or 0))
        prog = min(1.0, max(0.0, ((attuale or 0) - (base or 0)) / rng))
        st.progress(prog, text=f"{stato}  ·  {attuale}/{target} (partenza {base})")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            nuovo = st.slider("Livello attuale", 0, 10, int(attuale or 0),
                              key=f"logo_ob_upd_{rid}")
        with c2:
            nuovo_stato = st.selectbox("Stato", STATO_OB,
                                       index=STATO_OB.index(stato) if stato in STATO_OB else 0,
                                       key=f"logo_ob_st_{rid}")
        with c3:
            st.write("")
            st.write("")
            if st.button("💾", key=f"logo_ob_save_{rid}", help="Aggiorna"):
                _aggiorna_obiettivo(conn, rid, nuovo, nuovo_stato, paz_id, descr, area)
                st.rerun()
        if driv:
            st.caption(f"Rivalutazione prevista: {driv.strftime('%d/%m/%Y') if hasattr(driv,'strftime') else driv}")
        if st.button("🗑 Elimina", key=f"logo_ob_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM logopedia_obiettivi WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)


def _aggiorna_obiettivo(conn, rid, attuale, stato, paz_id, descr, area):
    try:
        cur = conn.cursor()
        cur.execute("UPDATE logopedia_obiettivi SET attuale=%s, stato=%s WHERE id=%s",
                    (int(attuale), stato, rid))
        conn.commit()
        # se chiuso, registra un esito (aggancio a Esiti / Apprendimento)
        if stato in ("🟢 Raggiunto", "🟡 Parziale", "⏸️ Sospeso"):
            esito = {"🟢 Raggiunto": "🟢 Migliorato", "🟡 Parziale": "🟡 Stabile / fermo",
                     "⏸️ Sospeso": "⚪ Non valutabile"}.get(stato, "⚪ Non valutabile")
            try:
                cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
                    id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
                    data TIMESTAMP DEFAULT NOW(),
                    intervento TEXT, esito TEXT, note TEXT);""")
                cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                            "VALUES(%s,%s,%s,%s)",
                            (paz_id, f"Logopedia — {area}: {descr}", esito,
                             "Da obiettivo logopedico"))
                conn.commit()
            except Exception:
                conn.rollback()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════
#  L4 — RELAZIONE LOGOPEDICA (bozza AI + carta intestata)
# ══════════════════════════════════════════════════════════════════════

_SCHEMA_LOGO = (
    "Redigi una bozza di RELAZIONE LOGOPEDICA secondo il Metodo PNEV, sui dati "
    "logopedici qui sotto. Articola ESATTAMENTE in queste sezioni:\n"
    "1. Dati identificativi\n"
    "2. Motivo dell'invio\n"
    "3. Anamnesi essenziale\n"
    "4. Profilo oro-mio-funzionale (SMOF)\n"
    "5. Profilo linguistico (comprensione, produzione, fonologia)\n"
    "6. Fluenza\n"
    "7. Sintesi del profilo funzionale\n"
    "8. Obiettivi e percorso\n"
    "9. Indicazioni e conclusioni\n\n"
    "NON scrivere intestazione né firma (aggiunte a parte). Attieniti ai dati; "
    "dove mancano, scrivi «da approfondire».\n\n"
    "=== DATI IDENTIFICATIVI ===\n{IDENT}\n\n=== DATI LOGOPEDICI ===\n"
)


def _dati_logopedici(conn, paz_id) -> str:
    parti = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati, sintesi, data FROM logopedia_valutazioni "
                    "WHERE paziente_id=%s ORDER BY data DESC LIMIT 1", (paz_id,))
        r = cur.fetchone()
        if r and r[0]:
            d = r[0] if isinstance(r[0], dict) else json.loads(r[0])
            parti.append("VALUTAZIONE + SMOF:")
            parti.append(json.dumps(d, ensure_ascii=False, indent=1))
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        cur = conn.cursor()
        cur.execute("SELECT numero, data_seduta, obiettivo, risposta FROM logopedia_sedute "
                    "WHERE paziente_id=%s ORDER BY data_seduta DESC LIMIT 15", (paz_id,))
        sd = cur.fetchall()
        if sd:
            parti.append("\nSEDUTE:")
            for num, ds, ob, risp in sd:
                parti.append(f"- n°{num} {ds}: {ob or ''} ({risp or ''})")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        cur = conn.cursor()
        cur.execute("SELECT descrizione, area, baseline, attuale, target, stato "
                    "FROM logopedia_obiettivi WHERE paziente_id=%s", (paz_id,))
        ob = cur.fetchall()
        if ob:
            parti.append("\nOBIETTIVI:")
            for descr, area, base, att, targ, stato in ob:
                parti.append(f"- {descr} [{area}]: {stato} {att}/{targ} (da {base})")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    return "\n".join(parti).strip()


def _render_relazione(conn, paz_id, paziente):
    st.caption("Bozza di relazione logopedica PNEV con carta intestata e firma. "
               "L'AI scrive, tu correggi e stampi.")

    try:
        from .ai_estrazione import genera_testo, ai_disponibile
        from .diagnosi_assistita import INTESTAZIONE, FIRMA, _identificativi
    except Exception as e:
        st.error(f"Moduli AI/diagnosi non disponibili: {e}")
        return

    if not isinstance(paziente, dict) or not (paziente.get("Cognome") or paziente.get("Nome")):
        try:
            from .quadro_storico import carica_paziente
            p = carica_paziente(conn, paz_id)
            if p:
                paziente = p
        except Exception:
            pass

    dati = _dati_logopedici(conn, paz_id)
    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()

    if not dati:
        st.info("Nessun dato logopedico ancora salvato: compila prima Valutazione, "
                "Diario o Obiettivi.")

    key = f"logo_rel_{paz_id}"
    disabled = not (ai_disponibile() and dati)
    if st.button("🤖 Genera bozza relazione", type="primary", disabled=disabled):
        ident = _identificativi(paziente)
        sistema = ("Sei un logopedista dello Studio The Organism che redige relazioni "
                   "secondo il Metodo PNEV. Italiano, registro clinico, terza persona. "
                   "NON inventare dati: usa solo quelli forniti.")
        with st.spinner("L'AI sta scrivendo la relazione…"):
            corpo = genera_testo(_SCHEMA_LOGO.replace("{IDENT}", ident) + dati,
                                 sistema=sistema)
        if corpo.startswith("⚠️"):
            st.session_state[key] = corpo
        else:
            st.session_state[key] = INTESTAZIONE + "\n\n" + corpo.strip() + "\n\n" + FIRMA
    if not ai_disponibile():
        st.caption("AI non configurata: la relazione automatica richiede la chiave nei Secrets.")

    testo = st.text_area("Relazione (modificabile)",
                         value=st.session_state.get(key, ""), height=460,
                         key=f"logo_rel_txt_{paz_id}")
    st.download_button("⬇️ Scarica (.txt)", data=testo or "",
                       file_name=f"relazione_logopedica_{nome or paz_id}.txt",
                       mime="text/plain", key=f"logo_rel_dl_{paz_id}")
