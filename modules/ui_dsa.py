# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  DSA — Disturbi Specifici dell'Apprendimento                        ║
║  BDE · DDE-2 · MT / MT Avanzate · AC-MT 3 · CMF                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
from typing import Optional
import streamlit as st
import json
import datetime
import math


# ══════════════════════════════════════════════════════════════════════
#  UTILITÀ
# ══════════════════════════════════════════════════════════════════════

def _pct_z(z: float) -> float:
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
           + t * (-1.821255978 + t * 1.330274429))))
    p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return round((p if z >= 0 else 1 - p) * 100, 1)


def _badge_dsa(label: str, valore: str, livello: str) -> None:
    """livello: ok | border | clin"""
    colori = {"ok": "#2ea44f", "border": "#9a6700", "clin": "#cf222e"}
    c = colori.get(livello, "#444")
    st.markdown(
        f"<span style='background:{c};color:#fff;padding:3px 10px;"
        f"border-radius:5px;font-size:.92em;font-weight:bold'>"
        f"{label}: {valore}</span>",
        unsafe_allow_html=True
    )
    st.markdown("")


def _classifica_pct(pct: float) -> tuple[str, str]:
    if pct <= 5:   return "Deficitario",  "clin"
    if pct <= 16:  return "Sotto la norma", "border"
    if pct <= 84:  return "Nella norma",  "ok"
    return "Superiore", "ok"


def _salva_dsa(conn, paziente_id: int, tipo: str, dati: dict) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dsa_valutazioni (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                tipo TEXT NOT NULL,
                dati_json TEXT,
                data_valutazione DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO dsa_valutazioni (paziente_id, tipo, dati_json, data_valutazione)"
            " VALUES (%s, %s, %s, %s)",
            (paziente_id, tipo,
             json.dumps(dati, ensure_ascii=False, default=str),
             datetime.date.today().isoformat())
        )
        conn.commit()
        st.success(f"✅ {tipo} salvato.")
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


def _carica_dsa(conn, paziente_id: int, tipo: str) -> Optional[dict]:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT dati_json FROM dsa_valutazioni "
            "WHERE paziente_id=%s AND tipo=%s "
            "ORDER BY created_at DESC LIMIT 1",
            (paziente_id, tipo)
        )
        row = cur.fetchone()
        if row:
            raw = row[0] if not isinstance(row, dict) else row["dati_json"]
            return json.loads(raw)
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════
#  CMF — Valutazione Competenze Metafonologiche
#  (Marotta, Ronchetti, Trasciani, Vicari)
# ══════════════════════════════════════════════════════════════════════

_CMF_PROVE = [
    ("Riconoscimento rime",               "rime",       8),
    ("Riconoscimento sillaba iniziale",   "sill_iniz",  8),
    ("Riconoscimento fonema iniziale",    "fon_iniz",   8),
    ("Segmentazione sillabica",           "segm_sill",  8),
    ("Fusione sillabica",                 "fus_sill",   8),
    ("Segmentazione fonemica",            "segm_fon",   8),
    ("Fusione fonemica",                  "fus_fon",    8),
    ("Omissione sillaba iniziale",        "omiss_sill", 8),
    ("Omissione fonema iniziale",         "omiss_fon",  8),
]

# Norme CMF per fascia scolastica (media corr., DS) — dati Marotta et al.
_CMF_NORME: dict[str, dict[str, tuple[float, float]]] = {
    "Scuola d'infanzia (3–5 aa)": {
        "rime":      (5.2, 2.1), "sill_iniz": (4.8, 2.2),
        "segm_sill": (4.1, 2.3),
    },
    "1ª elementare (inizio)": {
        "rime":      (6.4, 1.8), "sill_iniz": (6.1, 1.9),
        "fon_iniz":  (3.2, 2.0), "segm_sill": (6.0, 1.8),
        "fus_sill":  (5.8, 2.0),
    },
    "1ª elementare (fine)": {
        "rime":      (7.1, 1.3), "sill_iniz": (7.0, 1.4),
        "fon_iniz":  (5.5, 1.8), "segm_sill": (7.0, 1.3),
        "fus_sill":  (6.8, 1.5), "segm_fon":  (4.2, 2.1),
        "fus_fon":   (4.0, 2.2),
    },
    "2ª–3ª elementare": {
        "rime":      (7.6, 0.9), "sill_iniz": (7.5, 1.0),
        "fon_iniz":  (6.8, 1.2), "segm_sill": (7.5, 0.9),
        "fus_sill":  (7.3, 1.1), "segm_fon":  (6.1, 1.5),
        "fus_fon":   (6.0, 1.6), "omiss_sill":(5.8, 1.8),
        "omiss_fon": (5.0, 2.0),
    },
    "4ª–5ª elementare": {
        "rime":      (7.9, 0.5), "sill_iniz": (7.8, 0.6),
        "fon_iniz":  (7.5, 0.9), "segm_sill": (7.8, 0.6),
        "fus_sill":  (7.6, 0.8), "segm_fon":  (7.2, 1.1),
        "fus_fon":   (7.0, 1.3), "omiss_sill":(6.9, 1.4),
        "omiss_fon": (6.5, 1.7),
    },
}


def render_cmf(conn, paziente_id: int) -> None:
    st.subheader("🔤 CMF — Valutazione Competenze Metafonologiche")
    st.caption("Marotta, Ronchetti, Trasciani, Vicari · Scuola d'infanzia → 5ª elementare")

    fascia = st.selectbox("Fascia scolastica", list(_CMF_NORME.keys()),
                          key="cmf_fascia")
    norme_fascia = _CMF_NORME[fascia]
    prove_disponibili = [(n, k, mx) for n, k, mx in _CMF_PROVE
                         if k in norme_fascia]

    dati_cmf: dict[str, int] = {}
    st.markdown("#### Punteggi grezzi (items corretti)")
    cols = st.columns(min(len(prove_disponibili), 3))
    risultati: list[dict] = []

    for i, (nome, chiave, massimo) in enumerate(prove_disponibili):
        with cols[i % 3]:
            v = st.number_input(f"{nome} (max {massimo})",
                                min_value=0, max_value=massimo,
                                value=0, step=1, key=f"cmf_{chiave}")
            dati_cmf[chiave] = int(v)
            m, ds = norme_fascia[chiave]
            z = (v - m) / ds if ds else 0
            pct = _pct_z(z)
            cl, livello = _classifica_pct(pct)
            st.caption(f"Norma: {m:.1f}±{ds:.1f} | {pct:.0f}°pct → {cl}")
            risultati.append({"prova": nome, "punteggio": v, "pct": pct,
                              "classificazione": cl, "livello": livello})

    # Sintesi
    st.markdown("---")
    st.markdown("#### Profilo CMF")
    deficit = [r for r in risultati if r["livello"] == "clin"]
    border  = [r for r in risultati if r["livello"] == "border"]

    if deficit:
        st.error(f"🔴 Deficit ({len(deficit)} prove): " +
                 ", ".join(r["prova"] for r in deficit))
    if border:
        st.warning(f"🟡 Borderline ({len(border)} prove): " +
                   ", ".join(r["prova"] for r in border))
    if not deficit and not border:
        st.success("🟢 Competenze metafonologiche nella norma")

    note = st.text_area("Note CMF", height=68, key="cmf_note")
    if st.button("💾 Salva CMF", type="primary", key="salva_cmf"):
        _salva_dsa(conn, paziente_id, "CMF", {
            "fascia": fascia, "punteggi": dati_cmf,
            "risultati": risultati, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════
#  DDE-2 — Batteria per la Dislessia e Disortografia Evolutiva
# ══════════════════════════════════════════════════════════════════════

_DDE2_PROVE = [
    # (nome, chiave, usa_tempo, usa_errori)
    ("1. Lettura di parole (LP)",      "lp",  True,  True),
    ("2. Lettura di non-parole (LNP)", "lnp", True,  True),
    ("3. Lettura di un brano (LB)",    "lb",  True,  True),
    ("4. Dettato di parole (DP)",      "dp",  False, True),
    ("5. Dettato di non-parole (DNP)", "dnp", False, True),
    ("6. Dettato di frasi (DF)",       "df",  False, True),
    ("7. Scrittura spontanea (SS)",    "ss",  False, True),
]

# Norme DDE-2 per classe (tempo medio prova LP in sec, DS; errori media, DS)
# Fonte: Sartori, Job, Tressoldi 1995 / Tressoldi & Cornoldi 2000
_DDE2_NORME_LP: dict[str, tuple[float, float, float, float]] = {
    # classe: (media_tempo, ds_tempo, media_errori, ds_errori)
    "1ª fine":  (145.0, 60.0,  8.5, 5.2),
    "2ª fine":  (80.0,  35.0,  3.8, 3.0),
    "3ª fine":  (60.0,  25.0,  2.5, 2.2),
    "4ª fine":  (48.0,  18.0,  1.8, 1.8),
    "5ª fine":  (40.0,  15.0,  1.2, 1.4),
    "1ª media": (34.0,  12.0,  0.8, 1.0),
    "2ª media": (29.0,  10.0,  0.5, 0.8),
    "3ª media": (26.0,   9.0,  0.4, 0.7),
}

def render_dde2(conn, paziente_id: int) -> None:
    st.subheader("📖 DDE-2 — Batteria per la Valutazione della Dislessia e Disortografia")
    st.caption("Tressoldi, Stella, Facchin · Scuola primaria e media")

    classe = st.selectbox("Classe scolastica", list(_DDE2_NORME_LP.keys()),
                          key="dde2_classe")

    dati_prove: dict[str, dict] = {}
    for nome, chiave, usa_tempo, usa_errori in _DDE2_PROVE:
        with st.expander(nome, expanded=(chiave in ("lp", "dp"))):
            c1, c2 = st.columns(2)
            if usa_tempo:
                with c1:
                    tempo = st.number_input("Tempo (sec)", min_value=0.0,
                                            max_value=600.0, value=0.0,
                                            step=0.5, key=f"dde2_{chiave}_t")
                dati_prove[chiave] = {"tempo": float(tempo)}
            else:
                dati_prove[chiave] = {}

            if usa_errori:
                with (c2 if usa_tempo else c1):
                    errori = st.number_input("Errori", min_value=0,
                                             max_value=100, value=0,
                                             step=1, key=f"dde2_{chiave}_e")
                    dati_prove[chiave]["errori"] = int(errori)

            # Classificazione per LP con norme
            if chiave == "lp" and classe in _DDE2_NORME_LP:
                mt, dst, me, dse = _DDE2_NORME_LP[classe]
                if dati_prove[chiave].get("tempo", 0) > 0:
                    z_t = (dati_prove[chiave]["tempo"] - mt) / dst
                    pct_t = _pct_z(-z_t)
                    cl_t, lv_t = _classifica_pct(pct_t)
                    st.caption(f"Velocità: {pct_t:.0f}°pct → **{cl_t}**")
                if dati_prove[chiave].get("errori", 0) >= 0:
                    z_e = (dati_prove[chiave]["errori"] - me) / dse if dse else 0
                    pct_e = _pct_z(-z_e)
                    cl_e, lv_e = _classifica_pct(pct_e)
                    st.caption(f"Accuratezza: {pct_e:.0f}°pct → **{cl_e}**")

    # Sintesi diagnosi
    st.markdown("---")
    st.markdown("#### Interpretazione qualitativa")
    st.caption("⚠️ La diagnosi clinica richiede il confronto con le tavole normative complete del manuale per classe e mese.")

    tipo_lettura = st.multiselect(
        "Profilo lettura (seleziona quanto applicabile)",
        ["Lenta e accurata", "Veloce e inaccurata", "Lenta e inaccurata",
         "Nella norma", "Solo non-parole deficitarie", "Solo brano deficitario"],
        key="dde2_profilo"
    )
    note = st.text_area("Note DDE-2", height=80, key="dde2_note")

    if st.button("💾 Salva DDE-2", type="primary", key="salva_dde2"):
        _salva_dsa(conn, paziente_id, "DDE-2", {
            "classe": classe, "prove": dati_prove,
            "profilo_lettura": tipo_lettura, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════
#  BDE — Batteria per la Diagnosi della Dislessia e Disortografia
# ══════════════════════════════════════════════════════════════════════

def render_bde(conn, paziente_id: int) -> None:
    st.subheader("📚 BDE — Batteria Diagnosi Dislessia/Disortografia Evolutiva")
    st.caption("Valutazione lettura e scrittura · Scuola primaria")

    classe = st.selectbox("Classe", [
        "1ª primaria (fine)", "2ª primaria", "3ª primaria",
        "4ª primaria", "5ª primaria"
    ], key="bde_classe")

    st.markdown("#### Lettura")
    c1, c2 = st.columns(2)
    with c1:
        lp_tempo  = st.number_input("Lettura Parole — Tempo (sec)", min_value=0.0,
                                    max_value=300.0, value=0.0, step=0.5, key="bde_lp_t")
        lp_err    = st.number_input("Lettura Parole — Errori",      min_value=0,
                                    max_value=80, value=0, step=1, key="bde_lp_e")
        lnp_tempo = st.number_input("Lettura Non-Parole — Tempo (sec)", min_value=0.0,
                                    max_value=300.0, value=0.0, step=0.5, key="bde_lnp_t")
        lnp_err   = st.number_input("Lettura Non-Parole — Errori",      min_value=0,
                                    max_value=40, value=0, step=1, key="bde_lnp_e")
    with c2:
        lb_tempo  = st.number_input("Lettura Brano — Tempo (sec)",  min_value=0.0,
                                    max_value=600.0, value=0.0, step=0.5, key="bde_lb_t")
        lb_err    = st.number_input("Lettura Brano — Errori",       min_value=0,
                                    max_value=50, value=0, step=1, key="bde_lb_e")
        lb_compr  = st.number_input("Comprensione Brano (dom. corrette / totali)",
                                    min_value=0.0, max_value=1.0, value=0.0,
                                    step=0.1, key="bde_lb_compr")

    st.markdown("#### Scrittura")
    c3, c4 = st.columns(2)
    with c3:
        dp_err  = st.number_input("Dettato Parole — Errori", min_value=0,
                                  max_value=80, value=0, step=1, key="bde_dp_e")
        dnp_err = st.number_input("Dettato Non-Parole — Errori", min_value=0,
                                  max_value=40, value=0, step=1, key="bde_dnp_e")
    with c4:
        df_err  = st.number_input("Dettato Frasi — Errori", min_value=0,
                                  max_value=40, value=0, step=1, key="bde_df_e")
        tipo_err = st.multiselect("Tipo errori prevalenti",
                                  ["Fonologici", "Non fonologici", "Omissioni",
                                   "Separazioni/fusioni", "Accentazione",
                                   "Inversioni"], key="bde_tipo_err")

    st.caption("⚠️ Confronta con le tavole normative del manuale BDE per classe e periodo dell'anno")

    note = st.text_area("Note BDE", height=80, key="bde_note")
    if st.button("💾 Salva BDE", type="primary", key="salva_bde"):
        _salva_dsa(conn, paziente_id, "BDE", {
            "classe": classe,
            "lettura": {
                "parole_tempo": float(lp_tempo), "parole_errori": int(lp_err),
                "non_parole_tempo": float(lnp_tempo), "non_parole_errori": int(lnp_err),
                "brano_tempo": float(lb_tempo), "brano_errori": int(lb_err),
                "brano_comprensione": float(lb_compr),
            },
            "scrittura": {
                "parole_errori": int(dp_err), "non_parole_errori": int(dnp_err),
                "frasi_errori": int(df_err), "tipo_errori": tipo_err,
            },
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════
#  MT / MT Avanzate — Prove di Lettura (Cornoldi & Colpo)
# ══════════════════════════════════════════════════════════════════════

# Norme MT semplificate (velocità sill/sec, media e DS) per classe
_MT_NORME_VEL: dict[str, tuple[float, float]] = {
    # classe: (media_sill_sec, ds)
    "1ª fine":       (1.8, 0.7),
    "2ª inizio":     (2.4, 0.8),
    "2ª fine":       (3.2, 0.9),
    "3ª inizio":     (3.5, 0.8),
    "3ª fine":       (4.0, 0.9),
    "4ª inizio":     (4.3, 0.8),
    "4ª fine":       (4.8, 0.9),
    "5ª inizio":     (5.0, 0.9),
    "5ª fine":       (5.4, 0.9),
    "1ª media":      (5.8, 1.0),
    "2ª media":      (6.2, 1.0),
    "3ª media":      (6.6, 1.0),
    "Liceo 1°":      (7.0, 1.1),
    "Liceo 2°-5°":   (7.5, 1.1),
}

# Norme comprensione: punteggio grezzo medio e DS
_MT_NORME_COMPR: dict[str, tuple[float, float]] = {
    "1ª fine":     (5.2, 1.8),  "2ª inizio":   (5.5, 1.7),
    "2ª fine":     (6.0, 1.7),  "3ª inizio":   (6.2, 1.7),
    "3ª fine":     (6.5, 1.6),  "4ª inizio":   (6.8, 1.6),
    "4ª fine":     (7.0, 1.5),  "5ª inizio":   (7.2, 1.5),
    "5ª fine":     (7.4, 1.4),  "1ª media":    (7.6, 1.4),
    "2ª media":    (7.8, 1.3),  "3ª media":    (8.0, 1.3),
    "Liceo 1°":    (8.2, 1.3),  "Liceo 2°-5°": (8.5, 1.2),
}

_MT_CLASSI_VEL = [
    (5, "Criterio avanzato"),
    (4, "Criterio richiesto"),
    (3, "Accettabile"),
    (2, "Richiede miglioramento"),
    (1, "Non sufficiente"),
]

def _classifica_mt_vel(z: float) -> str:
    pct = _pct_z(z)
    if pct >= 75: return "Criterio avanzato"
    if pct >= 45: return "Criterio richiesto"
    if pct >= 25: return "Accettabile"
    if pct >= 5:  return "Richiede miglioramento"
    return "Non sufficiente"


def render_mt(conn, paziente_id: int) -> None:
    st.subheader("📖 MT / MT Avanzate — Prove di Lettura (Cornoldi & Colpo)")
    st.caption("Decifrazione (velocità + accuratezza) e comprensione del testo")

    tab_std, tab_av = st.tabs(["MT Standard (1ª–3ª media)", "MT Avanzate (liceo)"])

    for tab, classi_disponibili, nome_test in [
        (tab_std, [k for k in _MT_NORME_VEL if "Liceo" not in k], "MT"),
        (tab_av,  [k for k in _MT_NORME_VEL if "Liceo" in k], "MT-Avanzate"),
    ]:
        with tab:
            if not classi_disponibili:
                st.info("Nessuna classe disponibile per questa versione.")
                continue

            classe = st.selectbox("Classe / Periodo",
                                  classi_disponibili, key=f"mt_{nome_test}_cl")

            # Sillabe totali del brano (dipende dal protocollo)
            sillabe_brano = st.number_input("Sillabe totali nel brano",
                                            min_value=1, max_value=2000,
                                            value=300, step=10,
                                            key=f"mt_{nome_test}_sill")
            c1, c2 = st.columns(2)
            with c1:
                tempo_sec = st.number_input("Tempo lettura (sec)",
                                            min_value=0.0, max_value=600.0,
                                            value=0.0, step=0.5,
                                            key=f"mt_{nome_test}_tempo")
                errori_lett = st.number_input("Errori di decifrazione",
                                              min_value=0, max_value=200,
                                              value=0, step=1,
                                              key=f"mt_{nome_test}_err")
            with c2:
                domande_tot = st.number_input("Domande comprensione (totale)",
                                              min_value=1, max_value=20,
                                              value=10, step=1,
                                              key=f"mt_{nome_test}_dom_tot")
                domande_ok  = st.number_input("Domande corrette",
                                              min_value=0,
                                              max_value=int(domande_tot),
                                              value=0, step=1,
                                              key=f"mt_{nome_test}_dom_ok")

            # Calcoli
            vel_sill_sec = round(sillabe_brano / tempo_sec, 2) if tempo_sec > 0 else 0.0
            compr_pct_raw = round(domande_ok / domande_tot * 10, 1) if domande_tot > 0 else 0.0

            st.markdown("---")
            if vel_sill_sec > 0 and classe in _MT_NORME_VEL:
                m_v, ds_v = _MT_NORME_VEL[classe]
                z_v = (vel_sill_sec - m_v) / ds_v
                cl_v = _classifica_mt_vel(z_v)
                col1, col2 = st.columns(2)
                col1.metric("Velocità (sill/sec)", f"{vel_sill_sec:.2f}")
                col2.metric("Criterio velocità", cl_v)

            if classe in _MT_NORME_COMPR:
                m_c, ds_c = _MT_NORME_COMPR[classe]
                z_c = (compr_pct_raw - m_c) / ds_c
                pct_c = _pct_z(z_c)
                cl_c, lv_c = _classifica_pct(pct_c)
                col3, col4 = st.columns(2)
                col3.metric("Comprensione (/ 10)", f"{compr_pct_raw:.1f}")
                col4.metric("Classificazione", cl_c)

            note = st.text_area("Note MT", height=68, key=f"mt_{nome_test}_note")
            if st.button(f"💾 Salva {nome_test}", type="primary",
                         key=f"salva_{nome_test}"):
                _salva_dsa(conn, paziente_id, nome_test, {
                    "classe": classe,
                    "sillabe_brano": int(sillabe_brano),
                    "tempo_sec": float(tempo_sec),
                    "errori_decifrazione": int(errori_lett),
                    "vel_sill_sec": vel_sill_sec,
                    "domande_tot": int(domande_tot),
                    "domande_ok": int(domande_ok),
                    "compr_score": compr_pct_raw,
                    "note": note,
                    "data": datetime.date.today().isoformat(),
                })


# ══════════════════════════════════════════════════════════════════════
#  AC-MT 3 — Test di Valutazione delle Abilità di Calcolo
#  (Cornoldi, Lucangeli, Bellina)
# ══════════════════════════════════════════════════════════════════════

_ACMT_PROVE = [
    # (nome, chiave, max_punteggio, ha_tempo)
    ("Dettato di numeri",           "dett_num",  20, False),
    ("Discriminazione di quantità", "discr_q",   12, False),
    ("Enumerazione",                "enum",      12, True),
    ("Calcolo scritto — Addizioni", "calc_add",  10, True),
    ("Calcolo scritto — Sottrazioni","calc_sott", 10, True),
    ("Calcolo scritto — Moltiplicazioni","calc_molt", 10, True),
    ("Calcolo scritto — Divisioni", "calc_div",  10, True),
    ("Calcolo mentale",             "calc_ment", 10, True),
    ("Giudizio di numerosità",      "giud_num",  10, False),
    ("Conoscenza di fatti aritmetici","fatti_ar", 10, False),
]

_ACMT_NORME: dict[str, dict[str, tuple[float, float]]] = {
    # classe: {chiave: (media, ds)}
    "2ª primaria INGRESSO": {
        "dett_num": (16.2, 3.1), "calc_add": (7.1, 2.4),
        "calc_sott": (5.8, 2.6),
    },
    "2ª primaria": {
        "dett_num": (18.0, 2.5), "calc_add": (8.5, 1.8),
        "calc_sott": (7.2, 2.2), "calc_ment": (6.4, 2.1),
    },
    "3ª primaria": {
        "dett_num": (19.0, 1.8), "calc_add": (9.2, 1.3),
        "calc_sott": (8.5, 1.8), "calc_molt": (6.8, 2.4),
        "calc_ment": (7.1, 1.9),
    },
    "4ª primaria": {
        "dett_num": (19.5, 1.2), "calc_add": (9.6, 0.9),
        "calc_sott": (9.1, 1.4), "calc_molt": (8.2, 2.0),
        "calc_div": (6.5, 2.5), "calc_ment": (7.8, 1.7),
        "fatti_ar": (8.2, 1.8),
    },
    "5ª primaria": {
        "dett_num": (19.8, 0.8), "calc_add": (9.8, 0.6),
        "calc_sott": (9.5, 1.0), "calc_molt": (9.0, 1.5),
        "calc_div": (8.2, 2.0), "calc_ment": (8.4, 1.5),
        "fatti_ar": (9.0, 1.4),
    },
}

def render_acmt3(conn, paziente_id: int) -> None:
    st.subheader("🔢 AC-MT 3 — Abilità di Calcolo (Cornoldi, Lucangeli, Bellina)")
    st.caption("2ª primaria → 5ª primaria · Calcolo scritto e mentale")

    classe = st.selectbox("Classe", list(_ACMT_NORME.keys()), key="acmt_classe")
    norme_classe = _ACMT_NORME[classe]

    dati_prove: dict[str, dict] = {}
    risultati: list[dict] = []

    prove_disponibili = [(n, k, mx, ht) for n, k, mx, ht in _ACMT_PROVE
                         if k in norme_classe]

    st.markdown("#### Prove")
    for nome, chiave, massimo, ha_tempo in prove_disponibili:
        with st.expander(nome, expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                punteggio = st.number_input(f"Punteggio (max {massimo})",
                                            min_value=0, max_value=massimo,
                                            value=0, step=1,
                                            key=f"acmt_{chiave}_p")
            if ha_tempo:
                with c2:
                    tempo = st.number_input("Tempo (sec)", min_value=0.0,
                                            max_value=300.0, value=0.0,
                                            step=0.5, key=f"acmt_{chiave}_t")
            else:
                tempo = None

            m, ds = norme_classe[chiave]
            z = (punteggio - m) / ds if ds else 0
            pct = _pct_z(z)
            cl, lv = _classifica_pct(pct)
            st.caption(f"Norma: {m:.1f}±{ds:.1f} | {pct:.0f}°pct → **{cl}**")

            dati_prove[chiave] = {
                "punteggio": int(punteggio),
                "tempo": float(tempo) if tempo is not None else None,
                "pct": pct, "classificazione": cl,
            }
            risultati.append({"prova": nome, "pct": pct, "livello": lv})

    # Sintesi
    st.markdown("---")
    deficit = [r for r in risultati if r["livello"] == "clin"]
    border  = [r for r in risultati if r["livello"] == "border"]

    if deficit:
        st.error("🔴 Deficit: " + ", ".join(r["prova"] for r in deficit))
    if border:
        st.warning("🟡 Borderline: " + ", ".join(r["prova"] for r in border))
    if not deficit and not border:
        st.success("🟢 Profilo aritmetico nella norma")

    note = st.text_area("Note AC-MT 3", height=68, key="acmt_note")
    if st.button("💾 Salva AC-MT 3", type="primary", key="salva_acmt"):
        _salva_dsa(conn, paziente_id, "AC-MT-3", {
            "classe": classe, "prove": dati_prove,
            "risultati": risultati, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def render_dsa(conn, paziente_id: int) -> None:
    """
    Entry point sezione DSA.
    Chiama da app_main_router.py:
        from .ui_dsa import render_dsa
        render_dsa(conn, paziente_id)
    """
    st.title("📚 Valutazione DSA — Disturbi Specifici dell'Apprendimento")
    st.caption(f"Paziente ID: {paziente_id}")

    test_dsa = st.radio(
        "Seleziona batteria",
        ["CMF — Metafonologia", "DDE-2 — Dislessia/Disortografia",
         "BDE — Diagnosi Dislessia", "MT / MT Avanzate — Lettura",
         "AC-MT 3 — Calcolo"],
        horizontal=False, key="dsa_test_sel"
    )
    st.markdown("---")

    if test_dsa == "CMF — Metafonologia":
        render_cmf(conn, paziente_id)
    elif test_dsa == "DDE-2 — Dislessia/Disortografia":
        render_dde2(conn, paziente_id)
    elif test_dsa == "BDE — Diagnosi Dislessia":
        render_bde(conn, paziente_id)
    elif test_dsa == "MT / MT Avanzate — Lettura":
        render_mt(conn, paziente_id)
    elif test_dsa == "AC-MT 3 — Calcolo":
        render_acmt3(conn, paziente_id)
