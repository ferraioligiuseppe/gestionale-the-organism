#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║         GESTIONALE THE ORGANISM — NUOVI MODULI                      ║
║         File unico — 11 Aprile 2026                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  SEZIONE A — NPS Bambini/Adulti     (render_nps)                    ║
║  SEZIONE B — Caso Clinico Seed      (seed_caso_clinico)             ║
║  SEZIONE C — Report PDF con Grafici (genera_report_pdf)             ║
║  SEZIONE D — Diagnosi → Piano VT    (render_piano_vt)               ║
║  SEZIONE E — Widget DEM / K-D       (render_dem_widget,             ║
║                                      render_kd_widget)              ║
║  SEZIONE F — Export Statistici      (render_export_statistici)      ║
╠══════════════════════════════════════════════════════════════════════╣
║  ISTRUZIONI:                                                        ║
║  1. Salva come modules/gestionale_new_modules.py                    ║
║  2. In app_core.py o app_main_router.py aggiungi:                   ║
║       from modules.gestionale_new_modules import (                  ║
║           render_nps, seed_caso_clinico, genera_report_pdf,         ║
║           render_piano_vt, render_dem_widget,                       ║
║           render_kd_widget, render_export_statistici                ║
║       )                                                             ║
║  3. Aggiungi a requirements.txt:                                    ║
║       matplotlib>=3.8.0                                             ║
║       reportlab>=4.2.0                                              ║
║       openpyxl>=3.1.0                                               ║
║       pandas>=2.0.0                                                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import json
import math
import io
import base64
import datetime
import time

# ──────────────────────────────────────────────────────────────────────
# GUARD: import opzionali (non bloccanti)
# ──────────────────────────────────────────────────────────────────────
try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    _HAS_MATPLOTLIB = True
except ImportError:
    _HAS_MATPLOTLIB = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE A — NPS: Valutazione Neuropsicologica Bambini / Adulti
# ══════════════════════════════════════════════════════════════════════

# ── Tabelle normative semplificate ────────────────────────────────────

# Classificazione per punteggio composito (QI / indice)
_CI_CLASSI = [
    (130, 999, "Molto Superiore",   "≥ 130"),
    (120, 129, "Superiore",         "120–129"),
    (110, 119, "Medio-Alto",        "110–119"),
    (90,  109, "Nella Media",       "90–109"),
    (80,   89, "Medio-Basso",       "80–89"),
    (70,   79, "Limite",            "70–79"),
    (0,    69, "Estremamente Basso","< 70"),
]

def _classifica_ci(punteggio: float) -> str:
    for lo, hi, label, _ in _CI_CLASSI:
        if lo <= punteggio <= hi:
            return label
    return "n.d."

def _percentile_da_ci(ci: float) -> float:
    """Approssimazione percentile da punteggio composito (μ=100, σ=15)."""
    try:
        z = (ci - 100) / 15.0
        # Approssimazione polinomiale della CDF normale
        t = 1 / (1 + 0.2316419 * abs(z))
        poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 +
               t * (-1.821255978 + t * 1.330274429))))
        p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
        return round((p if z >= 0 else 1 - p) * 100, 1)
    except Exception:
        return 50.0

# Subtest WISC-V bambini (punteggio scalato 1-19, media 10 ds 3)
_WISC5_SUBTEST = {
    "VCI": [
        ("Comprensione verbale",  "cv"),
        ("Vocabolario",           "voc"),
        ("Similitudini",          "sim"),
        ("Informazioni",          "inf"),   # supplementare
    ],
    "VSI": [
        ("Disegno con cubi",      "dc"),
        ("Puzzle visivo",         "pv"),
    ],
    "FRI": [
        ("Matrici",               "mat"),
        ("Bilance",               "bil"),
        ("Aritmetica",            "ar"),    # supplementare
    ],
    "WMI": [
        ("Memoria di cifre",      "mc"),
        ("Sequenze numeri-lettere","snl"),
        ("Picturespam",           "ps"),    # supplementare
    ],
    "PSI": [
        ("Cifrario",              "cif"),
        ("Ricerca di simboli",    "rs"),
        ("Cancellazione",         "can"),   # supplementare
    ],
}

# Subtest WAIS-IV adulti
_WAIS4_SUBTEST = {
    "VCI": [
        ("Vocabolario",           "voc"),
        ("Similitudini",          "sim"),
        ("Informazioni",          "inf"),
    ],
    "IRP": [
        ("Disegno con cubi",      "dc"),
        ("Matrici",               "mat"),
        ("Puzzle visivo",         "pv"),   # supplementare
    ],
    "IMT": [
        ("Memoria di cifre",      "mc"),
        ("Aritmetica",            "ar"),
        ("Sequenze numeri-lettere","snl"),  # supplementare
    ],
    "IVE": [
        ("Cifrario",              "cif"),
        ("Ricerca di simboli",    "rs"),
        ("Cancellazione",         "can"),  # supplementare
    ],
}

# Classificazione subtest scalato
def _classifica_scalato(ps: float) -> str:
    if ps >= 16: return "Molto Superiore"
    if ps >= 13: return "Superiore"
    if ps >= 12: return "Medio-Alto"
    if ps >= 8:  return "Nella Media"
    if ps >= 7:  return "Medio-Basso"
    if ps >= 4:  return "Limite"
    return "Estremamente Basso"

# ── Helper UI ────────────────────────────────────────────────────────

def _scalato_input(label: str, key: str, supplementare: bool = False) -> Optional[int]:
    lbl = f"{'🔸 ' if supplementare else ''}{label}"
    val = st.number_input(
        lbl, min_value=1, max_value=19, value=10, step=1, key=key,
        help="Punteggio scalato 1–19 (media 10, DS 3)"
    )
    return int(val)

def _calcola_indice(scalati: list) -> float:
    """Media dei punteggi scalati → composito approssimato (μ=100, σ=15)."""
    if not scalati:
        return 100.0
    m = sum(scalati) / len(scalati)
    return round(100 + (m - 10) * 5, 1)

def _mostra_badge_ci(indice: float) -> None:
    pct = _percentile_da_ci(indice)
    cl  = _classifica_ci(indice)
    colori = {
        "Molto Superiore":   "#1a7f37",
        "Superiore":         "#2ea44f",
        "Medio-Alto":        "#6e7781",
        "Nella Media":       "#0969da",
        "Medio-Basso":       "#9a6700",
        "Limite":            "#cf222e",
        "Estremamente Basso":"#82071e",
    }
    c = colori.get(cl, "#444")
    st.markdown(
        f"""<div style='background:{c};color:white;padding:8px 16px;
        border-radius:8px;display:inline-block;font-weight:bold;font-size:1.1em'>
        Indice composito: {indice:.0f} &nbsp;|&nbsp; {cl} &nbsp;|&nbsp; {pct:.0f}° percentile
        </div>""",
        unsafe_allow_html=True
    )
    st.markdown("")

# ── Rey AVLT ─────────────────────────────────────────────────────────

_REY_TRIALS = ["I","II","III","IV","V","Interferenza B","Richiamo","Riconoscimento"]

def _sezione_rey(prefisso: str) -> dict:
    st.markdown("##### Rey AVLT — Lista A (15 parole)")
    dati = {}
    cols = st.columns(len(_REY_TRIALS))
    for i, trial in enumerate(_REY_TRIALS):
        with cols[i]:
            dati[f"{prefisso}_rey_{i}"] = st.number_input(
                trial, min_value=0, max_value=15 if i != 7 else 30,
                value=0, step=1, key=f"{prefisso}_rey_{i}",
                label_visibility="visible"
            )
    # curva apprendimento
    apprendimento = [dati.get(f"{prefisso}_rey_{j}", 0) for j in range(5)]
    tot = sum(apprendimento)
    st.caption(f"Totale I–V = **{tot}** | Curva: {' → '.join(str(v) for v in apprendimento)}")
    return dati

# ── Trail Making ──────────────────────────────────────────────────────

def _sezione_trail(prefisso: str) -> dict:
    st.markdown("##### Trail Making Test (TMT)")
    c1, c2, c3 = st.columns(3)
    with c1:
        tma = st.number_input("TMT-A (sec)", min_value=0.0, max_value=300.0,
                              value=0.0, step=0.5, key=f"{prefisso}_tmt_a")
    with c2:
        tmb = st.number_input("TMT-B (sec)", min_value=0.0, max_value=600.0,
                              value=0.0, step=0.5, key=f"{prefisso}_tmt_b")
    with c3:
        ratio = round(tmb / tma, 2) if tma > 0 else 0.0
        st.metric("Rapporto B/A", f"{ratio:.2f}", help="Norma attesa ≤ 3.0")
    err_a = st.number_input("Errori TMT-A", min_value=0, max_value=20,
                            value=0, step=1, key=f"{prefisso}_tmt_erri_a")
    err_b = st.number_input("Errori TMT-B", min_value=0, max_value=20,
                            value=0, step=1, key=f"{prefisso}_tmt_erri_b")
    return {"tmt_a": tma, "tmt_b": tmb, "rapporto_ba": ratio,
            "err_a": err_a, "err_b": err_b}

# ── MoCA ──────────────────────────────────────────────────────────────

_MOCA_ITEMS = [
    ("Visuospaziale/Esecutivo", 5),
    ("Denominazione", 3),
    ("Attenzione", 6),
    ("Linguaggio", 3),
    ("Astrazione", 2),
    ("Memoria differita", 5),
    ("Orientamento", 6),
]

def _sezione_moca(prefisso: str) -> dict:
    st.markdown("##### MoCA (Montreal Cognitive Assessment)")
    totale = 0
    dati = {}
    for nome, massimo in _MOCA_ITEMS:
        v = st.number_input(f"{nome} (max {massimo})",
                            min_value=0, max_value=massimo,
                            value=0, step=1, key=f"{prefisso}_moca_{nome}")
        dati[nome] = int(v)
        totale += int(v)
    anni_istruzione = st.number_input("Anni istruzione", min_value=0,
                                      max_value=30, value=13, step=1,
                                      key=f"{prefisso}_moca_istr")
    if anni_istruzione <= 12:
        totale_adj = totale + 1
        st.caption(f"Totale grezzo: {totale} → Corretto per istruzione: **{totale_adj}/30**")
    else:
        totale_adj = totale
        st.caption(f"Totale: **{totale_adj}/30**")

    if totale_adj >= 26:
        st.success("✅ Punteggio nella norma (≥26)")
    elif totale_adj >= 18:
        st.warning("⚠️ Lieve deterioramento cognitivo (18–25)")
    else:
        st.error("🔴 Compromissione significativa (<18)")
    dati["totale_adj"] = totale_adj
    return dati

# ── FAB ───────────────────────────────────────────────────────────────

_FAB_ITEMS = [
    "Concettualizzazione",
    "Flessibilità mentale",
    "Programmazione motoria",
    "Sensibilità all'interferenza",
    "Controllo inibitorio",
    "Autonomia ambientale",
]

def _sezione_fab(prefisso: str) -> dict:
    st.markdown("##### FAB (Frontal Assessment Battery)")
    totale = 0
    dati = {}
    cols = st.columns(3)
    for i, nome in enumerate(_FAB_ITEMS):
        with cols[i % 3]:
            v = st.number_input(nome, min_value=0, max_value=3,
                                value=0, step=1, key=f"{prefisso}_fab_{i}")
            dati[nome] = int(v)
            totale += int(v)
    st.caption(f"Totale FAB: **{totale}/18** — Norma: ≥ 13")
    dati["totale"] = totale
    return dati

# ── Stroop ────────────────────────────────────────────────────────────

def _sezione_stroop(prefisso: str) -> dict:
    st.markdown("##### Test di Stroop")
    c1, c2 = st.columns(2)
    with c1:
        parole = st.number_input("Parole (P) — item/sec", min_value=0.0,
                                 max_value=200.0, value=0.0, step=0.5,
                                 key=f"{prefisso}_stroop_p")
        colori = st.number_input("Colori (C) — item/sec", min_value=0.0,
                                 max_value=150.0, value=0.0, step=0.5,
                                 key=f"{prefisso}_stroop_c")
    with c2:
        parole_colori = st.number_input("Parole-Colori (PC) — item/sec",
                                        min_value=0.0, max_value=100.0,
                                        value=0.0, step=0.5,
                                        key=f"{prefisso}_stroop_pc")
        interferenza = round(parole_colori - ((parole * colori) / (parole + colori)), 2) \
                       if (parole + colori) > 0 else 0.0
        st.metric("Indice interferenza", f"{interferenza:.2f}")
    return {"parole": parole, "colori": colori,
            "parole_colori": parole_colori, "interferenza": interferenza}

# ── Diagnosi automatica NPS ───────────────────────────────────────────

def _diagnosi_nps(dati: dict) -> list:
    diagnosi = []
    ci_keys = [k for k in dati if k.endswith("_ci")]
    for k in ci_keys:
        val = dati[k]
        if isinstance(val, (int, float)) and val < 80:
            nome = k.replace("_ci", "").replace("_", " ").upper()
            diagnosi.append(f"Indice {nome} nella fascia limite/deficit ({val:.0f})")
    if "moca" in dati and isinstance(dati.get("moca"), dict):
        t = dati["moca"].get("totale_adj", 30)
        if t < 26:
            diagnosi.append(f"MoCA < 26 (punteggio {t}): monitorare deterioramento cognitivo")
    if "tmt_a" in dati and "tmt_b" in dati:
        if dati["tmt_b"] > 0 and dati["tmt_a"] > 0:
            ratio = dati["tmt_b"] / dati["tmt_a"]
            if ratio > 4.0:
                diagnosi.append(f"Rapporto TMT B/A = {ratio:.1f}: difficoltà nella flessibilità cognitiva")
    return diagnosi if diagnosi else ["Profilo neuropsicologico nei limiti della norma"]

# ── RENDER NPS principale ─────────────────────────────────────────────

def render_nps(conn, paziente_id: int) -> None:
    """
    Entry point principale. Chiama da app_core.py:
        render_nps(conn, paziente_id)
    """
    st.subheader("🧠 Valutazione Neuropsicologica (NPS)")

    tab_bimbo, tab_adulto = st.tabs(["👶 Bambini (WISC-V)", "🧑 Adulti (WAIS-IV / MoCA)"])

    # ── TAB BAMBINI ──────────────────────────────────────────────────
    with tab_bimbo:
        st.markdown("#### WISC-V — Wechsler Intelligence Scale for Children (5ª ed.)")
        dati_wisc = {}
        indici_wisc = {}
        all_scalati_wisc = []

        for indice, subtest_list in _WISC5_SUBTEST.items():
            with st.expander(f"📊 {indice}", expanded=True):
                scalati_indice = []
                cols = st.columns(len(subtest_list))
                for i, (nome, chiave) in enumerate(subtest_list):
                    supplementare = (i >= 2) and indice in ("FRI", "WMI", "PSI")
                    with cols[i]:
                        val = st.number_input(
                            f"{'🔸 ' if supplementare else ''}{nome}",
                            min_value=1, max_value=19, value=10, step=1,
                            key=f"wisc_{indice}_{chiave}",
                            help="Punteggio scalato 1–19"
                        )
                        dati_wisc[chiave] = int(val)
                        if not supplementare or i < 2:
                            scalati_indice.append(int(val))

                ci = _calcola_indice(scalati_indice)
                indici_wisc[indice] = ci
                all_scalati_wisc.extend(scalati_indice)
                _mostra_badge_ci(ci)

        # QI Totale
        st.markdown("---")
        st.markdown("#### QI Totale")
        ci_totale = _calcola_indice(list(indici_wisc.values()))
        _mostra_badge_ci(ci_totale)

        # Rey AVLT
        st.markdown("---")
        dati_rey_b = _sezione_rey("bimbo")

        # TMT (dai 8 anni)
        st.markdown("---")
        dati_tmt_b = _sezione_trail("bimbo")

        # Osservazioni cliniche
        st.markdown("---")
        st.markdown("#### Note cliniche")
        note_bimbo = st.text_area(
            "Osservazioni, comportamento durante la valutazione, indicazioni",
            height=100, key="nps_note_bimbo"
        )

        # Diagnosi
        st.markdown("---")
        st.markdown("#### 🔍 Sintesi diagnostica automatica")
        payload_b = {**{f"{k}_ci": v for k, v in indici_wisc.items()},
                     "qi_totale_ci": ci_totale, **dati_tmt_b}
        for d in _diagnosi_nps(payload_b):
            st.info(d)

        # Salvataggio
        if st.button("💾 Salva NPS Bambini", type="primary", key="salva_nps_bimbo"):
            _salva_nps(conn, paziente_id, "bambino", {
                "wisc_subtest": dati_wisc,
                "indici_wisc": indici_wisc,
                "qi_totale": ci_totale,
                "rey_avlt": dati_rey_b,
                "tmt": dati_tmt_b,
                "note": note_bimbo,
                "diagnosi": _diagnosi_nps(payload_b),
                "data": datetime.date.today().isoformat(),
            })

    # ── TAB ADULTI ───────────────────────────────────────────────────
    with tab_adulto:
        st.markdown("#### WAIS-IV — Wechsler Adult Intelligence Scale (4ª ed.)")
        dati_wais = {}
        indici_wais = {}

        for indice, subtest_list in _WAIS4_SUBTEST.items():
            with st.expander(f"📊 {indice}", expanded=True):
                scalati_indice = []
                cols = st.columns(len(subtest_list))
                for i, (nome, chiave) in enumerate(subtest_list):
                    supplementare = (i >= 2)
                    with cols[i]:
                        val = st.number_input(
                            f"{'🔸 ' if supplementare else ''}{nome}",
                            min_value=1, max_value=19, value=10, step=1,
                            key=f"wais_{indice}_{chiave}"
                        )
                        dati_wais[chiave] = int(val)
                        if not supplementare:
                            scalati_indice.append(int(val))

                ci = _calcola_indice(scalati_indice)
                indici_wais[indice] = ci
                _mostra_badge_ci(ci)

        st.markdown("---")
        ci_totale_adulto = _calcola_indice(list(indici_wais.values()))
        st.markdown("#### QI Totale (IQ)")
        _mostra_badge_ci(ci_totale_adulto)

        # MoCA
        st.markdown("---")
        dati_moca = _sezione_moca("adulto")

        # FAB
        st.markdown("---")
        dati_fab = _sezione_fab("adulto")

        # Stroop
        st.markdown("---")
        dati_stroop = _sezione_stroop("adulto")

        # Rey AVLT
        st.markdown("---")
        dati_rey_a = _sezione_rey("adulto")

        # TMT
        st.markdown("---")
        dati_tmt_a = _sezione_trail("adulto")

        # Note
        st.markdown("---")
        note_adulto = st.text_area(
            "Osservazioni cliniche",
            height=100, key="nps_note_adulto"
        )

        # Diagnosi
        st.markdown("---")
        st.markdown("#### 🔍 Sintesi diagnostica automatica")
        payload_a = {**{f"{k}_ci": v for k, v in indici_wais.items()},
                     "qi_totale_ci": ci_totale_adulto,
                     "moca": dati_moca, **dati_tmt_a}
        for d in _diagnosi_nps(payload_a):
            st.info(d)

        # Salvataggio
        if st.button("💾 Salva NPS Adulti", type="primary", key="salva_nps_adulto"):
            _salva_nps(conn, paziente_id, "adulto", {
                "wais_subtest": dati_wais,
                "indici_wais": indici_wais,
                "qi_totale": ci_totale_adulto,
                "moca": dati_moca,
                "fab": dati_fab,
                "stroop": dati_stroop,
                "rey_avlt": dati_rey_a,
                "tmt": dati_tmt_a,
                "note": note_adulto,
                "diagnosi": _diagnosi_nps(payload_a),
                "data": datetime.date.today().isoformat(),
            })


def _salva_nps(conn, paziente_id: int, tipo: str, dati: dict) -> None:
    """Salva/aggiorna i dati NPS nella tabella nps_valutazioni."""
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nps_valutazioni (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                tipo TEXT NOT NULL,
                dati_json TEXT,
                data_valutazione DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO nps_valutazioni (paziente_id, tipo, dati_json, data_valutazione)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (paziente_id, tipo, json.dumps(dati, ensure_ascii=False),
               dati.get("data", datetime.date.today().isoformat())))
        conn.commit()
        st.success(f"✅ NPS ({tipo}) salvato correttamente.")
    except Exception as e:
        st.error(f"Errore salvataggio NPS: {e}")


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE B — Caso Clinico Completo di Esempio (Seed)
# ══════════════════════════════════════════════════════════════════════

CASO_CLINICO_SEED = {
    "anagrafica": {
        "nome": "Marco",
        "cognome": "Esposito",
        "data_nascita": "2016-03-14",
        "eta": 10,
        "sesso": "M",
        "scuola": "Scuola Primaria Classe 4ª",
        "medico_curante": "Dott. Russo",
        "note_anamnestiche": (
            "Nato a 38+3 settimane, parto spontaneo. "
            "Segnalazione da parte della maestra per difficoltà di lettura, "
            "distrazione in classe, faticabilità visiva. "
            "La madre riferisce che il bambino porta spesso le mani agli occhi "
            "mentre legge e salta le righe frequentemente."
        ),
    },
    "anamnesi_catagnini": {
        "gravidanza_settimane": 38,
        "tipo_parto": "Spontaneo",
        "degenza_post_parto_giorni": 3,
        "allattamento": "Materno fino a 8 mesi",
        "sviluppo_motorio": {
            "sorriso_sociale_mesi": 2,
            "posizione_seduta_mesi": 7,
            "gattonamento_mesi": 9,
            "cammino_mesi": 14,
            "linguaggio_prime_parole_mesi": 12,
            "note": "Gattonamento breve, tendeva a trascinarsi"
        },
        "anamnesi_patologica": "Otiti ricorrenti (3 episodi entro i 3 anni). "
                               "Lieve ipoacusia conduttiva risolta."
    },
    "inpp": {
        "indice_disfunzione_pct": 42.5,
        "riflessi_attivi": ["RTAC", "RTTC", "Moro parziale"],
        "coordinazione": "Difficoltà nel cammino in tandem e sui talloni",
        "lateralita": "Destra per mano, sinistra per occhio — lateralità incrociata",
        "oculomotoria_score": 6,
        "note": "Romberg positivo, difficoltà skip"
    },
    "vvf": {
        "AV_lontan_dx": "10/10",
        "AV_lontan_sx": "10/10",
        "AV_vicino_dx": "10/10",
        "AV_vicino_sx": "10/10",
        "stereopsi": "60 secondi d'arco",
        "ppc": 12.5,
        "cover_test_dist": "Ortoforia",
        "cover_test_vicino": "Esoforia 4Δ",
        "DEM_tipo": "IV",
        "DEM_errori": 8,
        "DEM_tempo_A": 52.0,
        "DEM_tempo_C": 187.0,
        "DEM_ratio": 3.60,
        "KD_card1": 28.5,
        "KD_card2": 35.2,
        "KD_card3": 41.8,
        "KD_errori_tot": 4,
        "NSUCO_pursuit": 3,
        "NSUCO_saccadi": 3,
        "convergenza_cm": 8.5,
        "divergenza_cm": 18.0,
        "MEM_retinoscopy": "+0.50",
        "focus_flex_bino_cpm": 5,
        "diagnosi_funzionale": [
            "Disfunzione oculomotoria: DEM tipo IV con ratio > 3",
            "Insufficienza di convergenza (PPC = 12.5 cm)",
            "Esoforia al vicino 4Δ",
            "Riduzione flessibilità accomodativa binoculare",
        ]
    },
    "tvps": {
        "discriminazione_visiva_scaled": 8,
        "memoria_visiva_scaled": 6,
        "relazioni_spaziali_scaled": 7,
        "costanza_forma_scaled": 9,
        "memoria_visiva_sequenziale_scaled": 5,
        "figura_sfondo_scaled": 7,
        "chiusura_visiva_scaled": 8,
        "standard_score": 91,
        "percentile": 27,
        "classificazione": "Nella Media (fascia bassa)"
    },
    "nps": {
        "tipo": "bambino",
        "qi_totale": 96,
        "indici_wisc": {"VCI": 102, "VSI": 94, "FRI": 98, "WMI": 88, "PSI": 85},
        "note": "WMI e PSI nella fascia medio-bassa. Coerente con difficoltà oculomotorie.",
        "rey_avlt_totale_I_V": 41,
        "tmt_a": 38.0,
        "tmt_b": 92.0,
        "rapporto_ba": 2.42
    },
    "piano_vt_suggerito": {
        "obiettivi": [
            "Integrazione riflesso RTAC e RTTC",
            "Miglioramento convergenza (target PPC ≤ 5 cm)",
            "Incremento flessibilità accomodativa binoculare (target ≥ 8 cpm)",
            "Allenamento inseguimento lento e saccadi di precisione",
            "Riduzione esoforia al vicino"
        ],
        "esercizi_settimana_1_4": [
            "Esercizi di rotolamento e gattonamento (integrazione RTAC)",
            "Pencil push-up convergenza 5×10 ripetizioni",
            "Brock string: 3 perle, partendo da 50 cm",
            "Saccadi su barra di lettere (Hart chart) 5 min/die"
        ],
        "esercizi_settimana_5_12": [
            "Computer Orthoptics: vergenze a step BI/BE",
            "Flippers ±2.00 monoculare poi binoculare",
            "Jumping saccadi su sinottoforo/vectogrammi",
            "Attività motorie in schema crociato (marcia)"
        ],
        "rivalutazione_mesi": 3,
        "note": "Priorità integrazione riflessi + convergenza. "
                "Monitorare lettura scolastica ogni 4 settimane."
    }
}


def seed_caso_clinico(conn, verbose: bool = True) -> Optional[int]:
    """
    Inserisce il caso clinico di esempio nel DB.
    Ritorna il paziente_id creato.

    Uso:
        paziente_id = seed_caso_clinico(conn)
    """
    seed = CASO_CLINICO_SEED
    ana  = seed["anagrafica"]
    try:
        cur = conn.cursor()

        # 1. Inserisci paziente
        cur.execute("""
            INSERT INTO pazienti (nome, cognome, data_nascita, sesso, note)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (ana["nome"], ana["cognome"], ana["data_nascita"],
              ana["sesso"],
              f"[CASO DEMO] {ana['note_anamnestiche'][:200]}"))
        paziente_id = cur.fetchone()[0]

        # 2. Anamnesi Catagnini
        cur.execute("""
            INSERT INTO anamnesi_catagnini (paziente_id, dati_json)
            VALUES (%s, %s)
        """, (paziente_id,
              json.dumps(seed["anamnesi_catagnini"], ensure_ascii=False)))

        # 3. INPP
        cur.execute("""
            INSERT INTO inpp_neuromotorio (paziente_id, dati_json)
            VALUES (%s, %s)
        """, (paziente_id,
              json.dumps(seed["inpp"], ensure_ascii=False)))

        # 4. VVF
        cur.execute("""
            INSERT INTO valutazioni_visive (paziente_id, dati_json)
            VALUES (%s, %s)
        """, (paziente_id,
              json.dumps(seed["vvf"], ensure_ascii=False)))

        # 5. NPS
        cur.execute("""
            INSERT INTO nps_valutazioni (paziente_id, tipo, dati_json)
            VALUES (%s, %s, %s)
        """, (paziente_id, "bambino",
              json.dumps(seed["nps"], ensure_ascii=False)))

        conn.commit()

        if verbose:
            st.success(
                f"✅ Caso demo inserito: **{ana['nome']} {ana['cognome']}** "
                f"(ID paziente: {paziente_id})"
            )
        return paziente_id

    except Exception as e:
        if verbose:
            st.error(f"Errore seed caso clinico: {e}")
        return None


def render_seed_panel(conn) -> None:
    """
    Pannello Streamlit per inserire il caso di esempio.
    Aggiungilo nella sezione Amministrazione / Test del gestionale.
    """
    st.subheader("🧪 Caso Clinico Demo — End-to-End")
    st.info(
        "Inserisce un paziente fittizio con dati completi: "
        "Catagnini, INPP, VVF (DEM tipo IV, PPC ridotta), TVPS, NPS e piano VT. "
        "Utile per testare il flusso completo fino alla generazione della relazione AI."
    )
    with st.expander("📋 Anteprima dati"):
        st.json(CASO_CLINICO_SEED)
    if st.button("🚀 Inserisci caso demo nel DB", type="primary"):
        seed_caso_clinico(conn)


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE C — Report PDF con Grafici (TVPS, DEM, INPP)
# ══════════════════════════════════════════════════════════════════════

def _fig_to_bytes(fig) -> bytes:
    """Converte figura matplotlib in bytes PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white")
    buf.seek(0)
    return buf.read()


def _grafico_tvps(tvps_data: dict) -> bytes:
    """Bar chart orizzontale dei subtest TVPS."""
    if not _HAS_MATPLOTLIB:
        return b""
    subtest = [
        "Discriminazione visiva", "Memoria visiva",
        "Relazioni spaziali", "Costanza forma",
        "Memoria vis. sequenziale", "Figura-sfondo",
        "Chiusura visiva"
    ]
    chiavi = [
        "discriminazione_visiva_scaled", "memoria_visiva_scaled",
        "relazioni_spaziali_scaled", "costanza_forma_scaled",
        "memoria_visiva_sequenziale_scaled", "figura_sfondo_scaled",
        "chiusura_visiva_scaled"
    ]
    valori = [tvps_data.get(k, 10) for k in chiavi]
    colori = ["#2ea44f" if v >= 10 else ("#9a6700" if v >= 7 else "#cf222e")
              for v in valori]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(subtest, valori, color=colori, edgecolor="white", height=0.6)
    ax.axvline(x=10, color="#0969da", linewidth=1.5, linestyle="--", label="Media (10)")
    ax.axvline(x=7,  color="#cf222e", linewidth=1,   linestyle=":",  label="Cut-off (7)")
    ax.set_xlim(0, 19)
    ax.set_xlabel("Punteggio scalato")
    ax.set_title("TVPS-3 — Profilo subtest", fontweight="bold", pad=10)
    ax.legend(loc="lower right", fontsize=8)
    for bar, val in zip(bars, valori):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, fontweight="bold")
    fig.tight_layout()
    b = _fig_to_bytes(fig)
    plt.close(fig)
    return b


def _grafico_dem(vvf_data: dict) -> bytes:
    """Radar / indicatori DEM."""
    if not _HAS_MATPLOTLIB:
        return b""
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))

    # Grafico 1: Tempi A, C e ratio
    ax = axes[0]
    labels = ["Tempo A\n(sec)", "Tempo C\n(sec)", "Ratio\nC/A"]
    valori = [
        vvf_data.get("DEM_tempo_A", 0),
        vvf_data.get("DEM_tempo_C", 0),
        vvf_data.get("DEM_ratio", 0)
    ]
    norme  = [35, 70, 2.2]   # norma approssimata 8-10 anni
    colori_bar = ["#2ea44f" if v <= n else "#cf222e"
                  for v, n in zip(valori, norme)]
    ax.bar(labels, valori, color=colori_bar, edgecolor="white")
    for i, (v, n) in enumerate(zip(valori, norme)):
        ax.plot([i - 0.4, i + 0.4], [n, n], "k--", linewidth=1.5)
        ax.text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=9,
                fontweight="bold")
    ax.set_title("DEM — Tempi e Ratio", fontweight="bold")
    ax.set_ylabel("Valore")

    # Grafico 2: Tipo DEM
    ax2 = axes[1]
    tipo = vvf_data.get("DEM_tipo", "I")
    tipi  = ["I", "II", "III", "IV"]
    desc  = ["Oculomotorio\nnormale", "Accomodativo",
             "Verbale", "Oculomotorio\n+ verbale"]
    colori_tipo = ["#d1fae5" if t != tipo else "#cf222e" for t in tipi]
    for i, (t, d, c) in enumerate(zip(tipi, desc, colori_tipo)):
        ax2.bar(i, 1, color=c, edgecolor="#333", linewidth=1.5)
        ax2.text(i, 0.5, f"Tipo {t}\n{d}", ha="center", va="center",
                 fontsize=8, fontweight="bold" if t == tipo else "normal")
    ax2.set_ylim(0, 1.5)
    ax2.set_xticks([])
    ax2.set_yticks([])
    ax2.set_title(f"DEM — Classificazione (attuale: Tipo {tipo})", fontweight="bold")

    fig.tight_layout()
    b = _fig_to_bytes(fig)
    plt.close(fig)
    return b


def _grafico_inpp(inpp_data: dict) -> bytes:
    """Radar chart INPP per categoria."""
    if not _HAS_MATPLOTLIB:
        return b""
    categorie = ["Coordinazione", "Sviluppo\nMotorio", "Cerebellare",
                 "Riflessi\nPrimitivi", "Riflessi\nPosturali",
                 "Lateralità", "Oculomotoria"]
    # In produzione leggi dal JSON; qui usiamo dati simulati
    raw_vals = inpp_data.get("valori_per_categoria",
                             [2.1, 1.8, 1.5, 3.2, 2.4, 2.8, 2.6])
    N = len(categorie)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]
    raw_vals_plot = list(raw_vals) + [raw_vals[0]]

    fig, ax = plt.subplots(figsize=(5, 5),
                           subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categorie, size=8)
    ax.set_ylim(0, 4)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["1", "2", "3", "4"], size=7)
    ax.plot(angles, raw_vals_plot, "o-", linewidth=2, color="#cf222e")
    ax.fill(angles, raw_vals_plot, alpha=0.25, color="#cf222e")
    ax.set_title("INPP — Profilo per categoria\n(media punteggio 0–4)",
                 fontweight="bold", pad=20)

    indice = inpp_data.get("indice_disfunzione_pct", 0)
    fig.text(0.5, 0.02,
             f"Indice disfunzione globale: {indice:.1f}%",
             ha="center", fontsize=10, color="#82071e", fontweight="bold")
    b = _fig_to_bytes(fig)
    plt.close(fig)
    return b


def _grafico_wisc_wais(indici: dict, titolo: str = "WISC-V") -> bytes:
    """Bar chart degli indici compositi con banda norma."""
    if not _HAS_MATPLOTLIB:
        return b""
    nomi  = list(indici.keys())
    valori = [float(v) for v in indici.values()]
    colori_bar = []
    for v in valori:
        if v >= 110:   colori_bar.append("#2ea44f")
        elif v >= 90:  colori_bar.append("#0969da")
        elif v >= 80:  colori_bar.append("#9a6700")
        else:          colori_bar.append("#cf222e")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    bars = ax.bar(nomi, valori, color=colori_bar, edgecolor="white", width=0.55)
    ax.axhspan(90, 110, alpha=0.1, color="#0969da", label="Fascia norma (90–110)")
    ax.axhline(100, color="#0969da", linewidth=1, linestyle="--")
    ax.set_ylim(60, 145)
    ax.set_ylabel("Indice composito")
    ax.set_title(f"{titolo} — Profilo indici", fontweight="bold")
    ax.legend(fontsize=8)
    for bar, val in zip(bars, valori):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val:.0f}", ha="center", fontsize=10, fontweight="bold")
    fig.tight_layout()
    b = _fig_to_bytes(fig)
    plt.close(fig)
    return b


def genera_report_pdf(paziente_info: dict, vvf_data: dict,
                      tvps_data: dict, inpp_data: dict,
                      nps_data: dict, note_cliniche: str = "") -> bytes:
    """
    Genera un PDF clinico completo con grafici.

    Parametri:
        paziente_info  : dict con nome, cognome, data_nascita, eta
        vvf_data       : dict con DEM_tipo, DEM_tempo_A, ecc.
        tvps_data      : dict con subtest TVPS
        inpp_data      : dict con indice_disfunzione_pct, ecc.
        nps_data       : dict con indici_wisc/wais, qi_totale
        note_cliniche  : testo libero aggiuntivo

    Ritorna:
        bytes del PDF
    """
    if not _HAS_REPORTLAB:
        st.error("ReportLab non installato. Aggiungi 'reportlab>=4.2.0' a requirements.txt")
        return b""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story  = []

    H1 = ParagraphStyle("H1", parent=styles["Heading1"],
                         textColor=colors.HexColor("#0d1117"),
                         spaceAfter=6)
    H2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=colors.HexColor("#0969da"),
                         spaceAfter=4)
    BODY = ParagraphStyle("BODY", parent=styles["Normal"],
                           fontSize=10, leading=14, spaceAfter=4)
    SMALL = ParagraphStyle("SMALL", parent=styles["Normal"],
                            fontSize=8, leading=11, textColor=colors.grey)
    CAPTION = ParagraphStyle("CAPTION", parent=styles["Normal"],
                              fontSize=9, leading=12, alignment=TA_CENTER,
                              textColor=colors.HexColor("#444444"))

    # ── Intestazione ─────────────────────────────────────────────────
    story.append(Paragraph("The Organism — Report Clinico Integrato", H1))
    story.append(HRFlowable(width="100%", thickness=2,
                            color=colors.HexColor("#0969da")))
    story.append(Spacer(1, 0.3 * cm))

    nome_completo = (f"{paziente_info.get('nome', '')} "
                     f"{paziente_info.get('cognome', '')}").strip()
    data_gen = paziente_info.get("data_nascita", "n.d.")
    eta_str  = f"{paziente_info.get('eta', '')} anni"
    data_rep = datetime.date.today().strftime("%d/%m/%Y")

    info_table = [
        ["Paziente:", nome_completo, "Data report:", data_rep],
        ["Nato il:",  data_gen,      "Età:",         eta_str],
    ]
    t = Table(info_table, colWidths=[3 * cm, 7 * cm, 3 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("FONTNAME",    (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1),  "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))

    # ── 1. Grafici TVPS ───────────────────────────────────────────────
    story.append(Paragraph("1. TVPS-3 — Elaborazione Visiva", H2))
    tvps_png = _grafico_tvps(tvps_data)
    if tvps_png:
        img = RLImage(io.BytesIO(tvps_png), width=14 * cm, height=7 * cm)
        story.append(img)
        ss  = tvps_data.get("standard_score", "n.d.")
        pct = tvps_data.get("percentile", "n.d.")
        cl  = tvps_data.get("classificazione", "")
        story.append(Paragraph(
            f"Standard Score: <b>{ss}</b> | {pct}° percentile | {cl}",
            CAPTION
        ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 2. Grafici DEM ────────────────────────────────────────────────
    story.append(Paragraph("2. DEM — Developmental Eye Movement Test", H2))
    dem_png = _grafico_dem(vvf_data)
    if dem_png:
        img = RLImage(io.BytesIO(dem_png), width=14 * cm, height=5.5 * cm)
        story.append(img)
        story.append(Paragraph(
            f"Tipo {vvf_data.get('DEM_tipo', '?')} | "
            f"Errori: {vvf_data.get('DEM_errori', 0)} | "
            f"Ratio C/A: {vvf_data.get('DEM_ratio', 0):.2f}",
            CAPTION
        ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 3. Grafici INPP ───────────────────────────────────────────────
    story.append(Paragraph("3. INPP — Profilo Neuromotorio", H2))
    inpp_png = _grafico_inpp(inpp_data)
    if inpp_png:
        img = RLImage(io.BytesIO(inpp_png), width=9 * cm, height=9 * cm)
        story.append(img)
        story.append(Paragraph(
            f"Indice disfunzione globale: "
            f"<b>{inpp_data.get('indice_disfunzione_pct', 0):.1f}%</b>",
            CAPTION
        ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 4. NPS ────────────────────────────────────────────────────────
    story.append(Paragraph("4. Profilo Neuropsicologico (NPS)", H2))
    indici_nps = nps_data.get("indici_wisc") or nps_data.get("indici_wais", {})
    titolo_nps = "WISC-V" if "indici_wisc" in nps_data else "WAIS-IV"
    if indici_nps:
        nps_png = _grafico_wisc_wais(indici_nps, titolo_nps)
        if nps_png:
            img = RLImage(io.BytesIO(nps_png), width=13 * cm, height=6.5 * cm)
            story.append(img)
            qi = nps_data.get("qi_totale", "n.d.")
            story.append(Paragraph(
                f"QI Totale: <b>{qi}</b> — {_classifica_ci(float(qi)) if str(qi).isdigit() else ''}",
                CAPTION
            ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 5. Note cliniche ──────────────────────────────────────────────
    if note_cliniche:
        story.append(Paragraph("5. Note Cliniche", H2))
        story.append(Paragraph(note_cliniche.replace("\n", "<br/>"), BODY))
        story.append(Spacer(1, 0.3 * cm))

    # ── Footer ────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#cccccc")))
    story.append(Paragraph(
        f"Documento generato da Gestionale The Organism il {data_rep}. "
        "Uso riservato al professionista sanitario.",
        SMALL
    ))

    doc.build(story)
    return buf.getvalue()


def render_report_pdf_ui(conn, paziente_id: int) -> None:
    """
    Pannello Streamlit per generare e scaricare il report PDF.
    """
    st.subheader("📄 Report PDF con Grafici")
    st.caption("Genera un PDF clinico con grafici TVPS, DEM, INPP e NPS.")

    # Carica dati dal DB (stub: in produzione leggi le tabelle reali)
    try:
        cur = conn.cursor()
        cur.execute("SELECT nome, cognome, data_nascita FROM pazienti WHERE id=%s",
                    (paziente_id,))
        row = cur.fetchone()
        paziente_info = {
            "nome": row[0] if row else "",
            "cognome": row[1] if row else "",
            "data_nascita": str(row[2]) if row else "",
            "eta": "",
        }
    except Exception:
        paziente_info = {}

    note = st.text_area("Note aggiuntive per il report", height=80,
                        key="report_note_extra")

    seed = CASO_CLINICO_SEED  # fallback sui dati demo
    if st.button("🖨️ Genera PDF", type="primary"):
        if not _HAS_REPORTLAB:
            st.error("Installa reportlab: `pip install reportlab`")
            return
        if not _HAS_MATPLOTLIB:
            st.error("Installa matplotlib: `pip install matplotlib`")
            return
        with st.spinner("Generazione PDF in corso..."):
            pdf_bytes = genera_report_pdf(
                paziente_info=paziente_info or seed["anagrafica"],
                vvf_data=seed["vvf"],
                tvps_data=seed["tvps"],
                inpp_data=seed["inpp"],
                nps_data=seed["nps"],
                note_cliniche=note,
            )
        if pdf_bytes:
            st.download_button(
                label="⬇️ Scarica Report PDF",
                data=pdf_bytes,
                file_name=f"report_clinico_{paziente_id}_{datetime.date.today()}.pdf",
                mime="application/pdf",
            )
            st.success("PDF generato con successo.")


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE D — Diagnosi → Piano VT (Vision Therapy)
# ══════════════════════════════════════════════════════════════════════

# Mapping diagnosi → obiettivi + esercizi
_PIANO_VT_MAP = {
    "Insufficienza di convergenza": {
        "obiettivi": [
            "Ridurre PPC a ≤ 5 cm con recupero",
            "Eliminare sintomi astenopici al vicino",
            "Potenziare le vergenze fusionali positive (VFP)",
        ],
        "esercizi": [
            ("Brock String",         "3 nodi a 50 / 30 / 15 cm — 5 min 2×/die"),
            ("Pencil Push-Up",       "15 cm → 7 cm × 10 rip., 3 serie/die"),
            ("Computer Orthoptics",  "Step vergenze BI→BE, partendo da ±4Δ"),
            ("Vectogrammi",          "Quoits/Clown: salti di vergenza 2 min"),
            ("Hart Chart saccadi",   "Near-far flips su lettera bersaglio"),
        ],
        "durata_settimane": 12,
        "rivalutazione_mesi": 3,
    },
    "Disfunzione oculomotoria: DEM tipo IV": {
        "obiettivi": [
            "DEM ratio C/A ≤ 2.5",
            "Ridurre errori DEM < 3",
            "Automatizzare inseguimenti lenti e saccadi di precisione",
        ],
        "esercizi": [
            ("Hart Chart saccadi",   "Monoculare poi binoculare, 3 × 1 min"),
            ("Palleggio numeri",     "Palla con numeri scritti, catch & read"),
            ("Metronomo saccadi",    "Barre di lettere a ritmo 40-60 bpm"),
            ("VisualEdge / RightEye","Software saccadi: precision tracking"),
            ("Rotazioni oculari",    "Cerchi ampi → cerchi piccoli, 3 × 20"),
        ],
        "durata_settimane": 10,
        "rivalutazione_mesi": 2,
    },
    "Riduzione flessibilità accomodativa binoculare": {
        "obiettivi": [
            "Flessibilità binoculare ≥ 8 cpm con ±2.00",
            "Eliminare astenopia da lavoro prolungato al vicino",
        ],
        "esercizi": [
            ("Flippers ±1.50",       "Mono DX → mono SX → bino, 1 min × 3"),
            ("Flippers ±2.00",       "Dopo 3 settimane, bino, 2 min × 3"),
            ("Arti letter chart",    "Flip +/-2 leggendo riga per riga"),
            ("Push-away",            "Accommodazione-vergenza integrata"),
        ],
        "durata_settimane": 8,
        "rivalutazione_mesi": 2,
    },
    "Esoforia al vicino": {
        "obiettivi": [
            "Ridurre esoforia < 2Δ al vicino",
            "Incrementare VFN (vergenze fusionali negative) ≥ 10/14",
        ],
        "esercizi": [
            ("Prismi base-IN",       "Lettura con prismi BI, 10 min"),
            ("Vectogrammi BO",       "Salti vergenza base-out"),
            ("Brock String BO",      "Nodi a 50 cm con SLIP bias"),
        ],
        "durata_settimane": 8,
        "rivalutazione_mesi": 2,
    },
    "Riflesso RTAC attivo": {
        "obiettivi": [
            "Integrazione riflesso RTAC entro 8-12 settimane",
            "Coordinazione occhio-mano migliorata",
        ],
        "esercizi": [
            ("Rotolamento controllato", "Da supino, rotola al pavimento 5×/sessione"),
            ("Esercizio RTAC Goddard",  "Posizione supina, capo ruotato, estende braccio omolatale 20×"),
            ("Reptile crawl",           "Strisciamento in schema omolaterale 5 min"),
            ("Marcia schema crociato",  "Esasperata, 5 min/die"),
        ],
        "durata_settimane": 12,
        "rivalutazione_mesi": 3,
    },
    "Riflesso RTTC attivo": {
        "obiettivi": [
            "Integrazione riflesso RTTC",
            "Riduzione tensione posturale cervicale",
        ],
        "esercizi": [
            ("Esercizio RTTC Goddard",  "Posizione carponi, flesso-estendi testa 20×"),
            ("Cat-cow yoga",            "Colonna in sync con respiro, 3 min"),
            ("Gattonamento controllato","Schema omolaterale e controlaterale, 5 min"),
        ],
        "durata_settimane": 10,
        "rivalutazione_mesi": 3,
    },
    "default": {
        "obiettivi": [
            "Miglioramento generale dell'efficienza visiva",
            "Potenziamento integrazione visuo-motoria",
        ],
        "esercizi": [
            ("Brock String",  "Base per tutta la VT — 5 min/die"),
            ("Hart Chart",    "Saccadi e accomodazione — 5 min/die"),
        ],
        "durata_settimane": 8,
        "rivalutazione_mesi": 2,
    },
}

_FASI_VT = [
    ("Fase 1 — Monoculare",  1,  4,
     "Normalizza funzioni monoculari (accomodazione, oculomotricità)"),
    ("Fase 2 — Binoculare",  5,  9,
     "Integra funzioni binoculari (vergenze, fusione, stereoacuità)"),
    ("Fase 3 — Integrazione",10, 12,
     "Generalizza in attività scolastiche/lavorative"),
]


def _piano_vt_da_diagnosi(diagnosi_list: list) -> dict:
    """Costruisce piano VT completo dalle diagnosi funzionali."""
    obiettivi_uniq = []
    esercizi_totali = []
    max_settimane   = 0
    max_rivalutaz   = 0
    fonti_usate     = []

    for d in diagnosi_list:
        matched = None
        for chiave, dati in _PIANO_VT_MAP.items():
            if chiave.lower() in d.lower() or d.lower() in chiave.lower():
                matched = (chiave, dati)
                break
        if not matched:
            matched = ("default", _PIANO_VT_MAP["default"])

        chiave, dati = matched
        fonti_usate.append(chiave)
        for o in dati["obiettivi"]:
            if o not in obiettivi_uniq:
                obiettivi_uniq.append(o)
        esercizi_totali.extend(dati["esercizi"])
        max_settimane = max(max_settimane, dati["durata_settimane"])
        max_rivalutaz = max(max_rivalutaz, dati["rivalutazione_mesi"])

    # Deduplicazione esercizi
    seen = set()
    esercizi_dedup = []
    for nome, desc in esercizi_totali:
        if nome not in seen:
            seen.add(nome)
            esercizi_dedup.append((nome, desc))

    return {
        "obiettivi": obiettivi_uniq,
        "esercizi":  esercizi_dedup,
        "durata_settimane": max_settimane,
        "rivalutazione_mesi": max_rivalutaz,
        "fonti": fonti_usate,
    }


def render_piano_vt(conn, paziente_id: int,
                    diagnosi_list: Optional[list] = None) -> None:
    """
    Pannello Streamlit Piano VT.
    diagnosi_list: lista di stringhe diagnostiche (es. da VVF o passata manualmente)
    """
    st.subheader("🎯 Piano di Vision Therapy — da diagnosi funzionale")

    # Input manuale o automatico
    if diagnosi_list is None:
        diagnosi_input = st.text_area(
            "Inserisci diagnosi funzionali (una per riga):",
            value="\n".join(CASO_CLINICO_SEED["vvf"]["diagnosi_funzionale"]),
            height=100,
            key="piano_vt_diagnosi_input"
        )
        diagnosi_list = [d.strip() for d in diagnosi_input.splitlines()
                         if d.strip()]
    else:
        st.markdown("**Diagnosi rilevate automaticamente:**")
        for d in diagnosi_list:
            st.markdown(f"- {d}")

    if not diagnosi_list:
        st.info("Nessuna diagnosi disponibile.")
        return

    piano = _piano_vt_da_diagnosi(diagnosi_list)

    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### 🎯 Obiettivi terapeutici")
        for i, o in enumerate(piano["obiettivi"], 1):
            st.markdown(f"{i}. {o}")
    with col2:
        st.metric("Durata stimata", f"{piano['durata_settimane']} settimane")
        st.metric("Rivalutazione", f"{piano['rivalutazione_mesi']} mesi")

    st.markdown("---")
    st.markdown("### 🏋️ Esercizi prescritti")
    for nome, desc in piano["esercizi"]:
        with st.container():
            c1, c2 = st.columns([1, 3])
            c1.markdown(f"**{nome}**")
            c2.markdown(desc)
    st.markdown("---")

    st.markdown("### 📅 Fasi del trattamento")
    for nome_fase, w_start, w_end, descrizione in _FASI_VT:
        if w_start <= piano["durata_settimane"]:
            with st.expander(f"{nome_fase} (sett. {w_start}–{w_end})"):
                st.markdown(descrizione)
                # filtra esercizi per fase
                esercizi_fase = piano["esercizi"][:3] if w_start == 1 \
                    else (piano["esercizi"][2:5] if w_start == 5
                          else piano["esercizi"][4:])
                for nome_es, desc_es in esercizi_fase:
                    st.markdown(f"- **{nome_es}**: {desc_es}")

    # Salva piano VT nel DB
    if st.button("💾 Salva Piano VT", type="primary", key="salva_piano_vt"):
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS piani_vt (
                    id BIGSERIAL PRIMARY KEY,
                    paziente_id BIGINT NOT NULL,
                    piano_json TEXT,
                    diagnosi_json TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO piani_vt (paziente_id, piano_json, diagnosi_json)
                VALUES (%s, %s, %s)
            """, (paziente_id,
                  json.dumps(piano, ensure_ascii=False),
                  json.dumps(diagnosi_list, ensure_ascii=False)))
            conn.commit()
            st.success("✅ Piano VT salvato nel DB.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE E — Widget Interattivi DEM con click e K-D con timer
# ══════════════════════════════════════════════════════════════════════

# ── Griglia DEM (numeri random come nella versione reale) ─────────────
import random as _random
_random.seed(42)

def _genera_griglia_dem(righe: int = 16, cols: int = 5) -> list:
    return [[str(_random.randint(1, 9)) for _ in range(cols)]
            for _ in range(righe)]

_DEM_GRIGLIA_A = _genera_griglia_dem(16, 5)
_DEM_GRIGLIA_C = [
    ["3", "8", "6", "1", "5", "4", "2", "9", "7", "6"],
    ["1", "5", "9", "2", "8", "3", "7", "4", "6", "5"],
    ["7", "2", "4", "8", "1", "6", "9", "3", "5", "8"],
    ["4", "6", "3", "9", "7", "2", "5", "8", "1", "4"],
    ["9", "1", "7", "4", "3", "8", "6", "2", "9", "3"],
    ["6", "3", "8", "5", "2", "9", "4", "7", "3", "7"],
    ["5", "7", "2", "6", "4", "1", "8", "3", "2", "1"],
    ["8", "4", "1", "3", "9", "7", "2", "5", "8", "9"],
    ["2", "9", "5", "7", "6", "4", "1", "6", "4", "2"],
    ["3", "6", "4", "1", "5", "2", "9", "1", "7", "6"],
    ["1", "8", "7", "2", "3", "6", "5", "4", "8", "3"],
    ["9", "2", "3", "8", "4", "7", "3", "6", "1", "5"],
    ["7", "5", "6", "4", "1", "3", "8", "2", "9", "4"],
    ["4", "1", "9", "6", "7", "5", "2", "7", "3", "8"],
    ["6", "3", "2", "5", "8", "4", "1", "9", "5", "2"],
    ["5", "7", "8", "3", "2", "1", "6", "5", "4", "7"],
]

# ── Card K-D ──────────────────────────────────────────────────────────
_KD_CARDS = [
    # Card 0 (Demo)
    [
        ["2", "5", "4", "3"],
        ["4", "8", "5", "6"],
        ["3", "7", "2", "9"],
        ["6", "9", "8", "1"],
        ["7", "3", "6", "4"],
    ],
    # Card 1
    [
        ["3", "8", "6", "2", "4"],
        ["1", "5", "9", "3", "7"],
        ["7", "2", "4", "8", "1"],
        ["4", "6", "3", "9", "5"],
        ["9", "1", "7", "4", "8"],
        ["6", "3", "8", "5", "2"],
    ],
    # Card 2
    [
        ["5", "1", "3", "7", "9", "2"],
        ["2", "9", "6", "4", "8", "3"],
        ["8", "4", "2", "1", "5", "7"],
        ["1", "7", "5", "9", "3", "6"],
        ["6", "3", "8", "2", "7", "4"],
        ["3", "8", "1", "6", "2", "9"],
    ],
    # Card 3
    [
        ["4", "2", "8", "5", "1", "9", "3"],
        ["7", "6", "3", "2", "9", "4", "8"],
        ["1", "9", "5", "7", "6", "2", "4"],
        ["8", "3", "4", "1", "5", "7", "6"],
        ["5", "7", "6", "9", "3", "8", "1"],
        ["2", "4", "7", "3", "8", "1", "5"],
    ],
]


def render_dem_widget() -> dict:
    """
    Widget DEM interattivo HTML.
    Restituisce dict con i risultati se completato.

    Integra in app_core.py:
        risultati = render_dem_widget()
        if risultati:
            # salva nel DB
    """
    st.subheader("🔢 DEM — Developmental Eye Movement Test (Interattivo)")

    tab_istr, tab_A, tab_C, tab_risultati = st.tabs(
        ["📖 Istruzioni", "🅰️ Parte A (solo vert.)", "🅰️🅱️ Parte C (orizz.)", "📊 Risultati"]
    )

    risultati_dem = {}

    with tab_istr:
        st.markdown("""
**Come somministrare il DEM interattivo:**
1. **Parte A** — Mostra la griglia verticale. Avvia il timer. Il paziente legge ogni colonna
   dall'alto al basso. Il clinico clicca **Errore** ad ogni omissione/sostituzione.
2. **Parte C** — Griglia orizzontale. Stessa procedura ma righe da sinistra a destra.
3. Alla fine calcola automaticamente: tipo DEM, ratio, errori.

**Tipo DEM:**
| Tipo | Tempo A | Tempo C | Ratio |
|------|---------|---------|-------|
| I   | Normale | Normale | Normale | Oculomotorio ok |
| II  | Elevato | Elevato | Normale | Deficit accomodativo/attentivo |
| III | Normale | Elevato | Elevato | Deficit oculomotorio puro |
| IV  | Elevato | Elevato | Elevato | Deficit oculomotorio + verbale |
        """)

    with tab_A:
        dem_a_html = _build_dem_html(
            "dem_a", _DEM_GRIGLIA_A, "Parte A — Verticale",
            layout="vertical"
        )
        st.components.v1.html(dem_a_html, height=620, scrolling=True)
        st.markdown("**Inserisci risultati misurati:**")
        c1, c2 = st.columns(2)
        with c1:
            tempo_a = st.number_input("Tempo A (sec)", min_value=0.0,
                                      max_value=300.0, value=0.0, step=0.5,
                                      key="dem_tempo_a")
        with c2:
            errori_a = st.number_input("Errori A", min_value=0, max_value=50,
                                       value=0, step=1, key="dem_errori_a")

    with tab_C:
        dem_c_html = _build_dem_html(
            "dem_c", _DEM_GRIGLIA_C, "Parte C — Orizzontale",
            layout="horizontal"
        )
        st.components.v1.html(dem_c_html, height=620, scrolling=True)
        st.markdown("**Inserisci risultati misurati:**")
        c1, c2 = st.columns(2)
        with c1:
            tempo_c = st.number_input("Tempo C (sec)", min_value=0.0,
                                      max_value=600.0, value=0.0, step=0.5,
                                      key="dem_tempo_c")
        with c2:
            errori_c = st.number_input("Errori C", min_value=0, max_value=80,
                                       value=0, step=1, key="dem_errori_c")

    with tab_risultati:
        ta = st.session_state.get("dem_tempo_a", 0.0)
        tc = st.session_state.get("dem_tempo_c", 0.0)
        ea = st.session_state.get("dem_errori_a", 0)
        ec = st.session_state.get("dem_errori_c", 0)

        if ta > 0 and tc > 0:
            ratio = round(tc / ta, 2) if ta > 0 else 0.0

            # Norme per 8-10 anni (approssimate)
            NORMA_A = 40.0
            NORMA_C = 80.0
            NORMA_RATIO = 2.5

            tipo_a_alto = ta > NORMA_A
            tipo_c_alto = tc > NORMA_C
            tipo_r_alto = ratio > NORMA_RATIO

            if not tipo_a_alto and not tipo_c_alto:
                tipo = "I"
                descrizione = "Oculomotricità nella norma"
                col_tipo = "🟢"
            elif tipo_a_alto and tipo_c_alto and not tipo_r_alto:
                tipo = "II"
                descrizione = "Deficit accomodativo/attentivo (ratio normale)"
                col_tipo = "🟡"
            elif not tipo_a_alto and tipo_c_alto and tipo_r_alto:
                tipo = "III"
                descrizione = "Deficit oculomotorio puro (A normale, C e ratio alti)"
                col_tipo = "🟠"
            else:
                tipo = "IV"
                descrizione = "Deficit oculomotorio + verbale"
                col_tipo = "🔴"

            st.markdown(f"## {col_tipo} Tipo {tipo} — {descrizione}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Tempo A", f"{ta:.1f}s",
                        delta=f"{ta-NORMA_A:+.1f}s vs norma",
                        delta_color="inverse")
            col2.metric("Tempo C", f"{tc:.1f}s",
                        delta=f"{tc-NORMA_C:+.1f}s vs norma",
                        delta_color="inverse")
            col3.metric("Ratio C/A", f"{ratio:.2f}",
                        delta=f"{ratio-NORMA_RATIO:+.2f} vs norma",
                        delta_color="inverse")
            col4.metric("Errori tot.", ea + ec)

            risultati_dem = {
                "DEM_tipo": tipo,
                "DEM_tempo_A": ta,
                "DEM_tempo_C": tc,
                "DEM_ratio": ratio,
                "DEM_errori": ea + ec,
                "DEM_errori_A": ea,
                "DEM_errori_C": ec,
            }
        else:
            st.info("Inserisci i tempi nelle schede A e C per vedere i risultati.")

    return risultati_dem


def _build_dem_html(widget_id: str, griglia: list, titolo: str,
                    layout: str = "horizontal") -> str:
    """Genera HTML interattivo per DEM con timer e click-to-mark."""
    righe_html = ""
    for r, riga in enumerate(griglia):
        celle = "".join(
            f'<span class="dem-cell" id="{widget_id}_r{r}_c{c}"'
            f' onclick="markCell(this)">{num}</span>'
            for c, num in enumerate(riga)
        )
        righe_html += f'<div class="dem-row">{celle}</div>\n'

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Courier New', monospace; background: #f6f8fa;
          margin: 0; padding: 12px; }}
  h3   {{ font-size: 14px; color: #0d1117; margin-bottom: 8px; }}
  .timer-bar {{ display:flex; align-items:center; gap:12px; margin-bottom:10px; }}
  #timer_{widget_id} {{ font-size: 28px; font-weight:bold; color:#0969da;
                        min-width:80px; }}
  button {{ padding:6px 14px; border:none; border-radius:6px;
            cursor:pointer; font-size:13px; font-weight:bold; }}
  #btn_start_{widget_id} {{ background:#2ea44f; color:white; }}
  #btn_stop_{widget_id}  {{ background:#cf222e; color:white; }}
  #btn_err_{widget_id}   {{ background:#9a6700; color:white; }}
  #err_count_{widget_id} {{ font-size:20px; font-weight:bold; color:#9a6700; }}
  .dem-grid {{ margin-top:8px; }}
  .dem-row  {{ display:flex; gap:{"20px" if layout=="horizontal" else "4px"};
               margin-bottom:{"4px" if layout=="horizontal" else "0"};
               {"flex-direction:column;" if layout=="vertical" else ""}
             }}
  /* quando layout è verticale, le colonne vanno side by side */
  {".dem-grid { display:flex; flex-direction:row; gap:20px; }" if layout=="vertical" else ""}
  {".dem-row { flex-direction:column; gap:2px; }" if layout=="vertical" else ""}
  .dem-cell {{ font-size: 22px; cursor:pointer; padding:2px 4px;
               border-radius:4px; user-select:none; transition: background 0.1s;
               min-width:24px; text-align:center; color:#0d1117; }}
  .dem-cell:hover  {{ background:#ddf4ff; }}
  .dem-cell.marked {{ background:#ffebe9; color:#cf222e;
                      text-decoration:line-through; font-weight:bold; }}
  .dem-cell.current {{ background:#dafbe1; border: 2px solid #2ea44f; }}
  .stats {{ margin-top:10px; font-size:13px; color:#444; }}
</style>
</head>
<body>
<h3>🔢 {titolo}</h3>
<div class="timer-bar">
  <div id="timer_{widget_id}">0.0s</div>
  <button id="btn_start_{widget_id}" onclick="startTimer()">▶ Avvia</button>
  <button id="btn_stop_{widget_id}"  onclick="stopTimer()">⏹ Stop</button>
  <button id="btn_err_{widget_id}"   onclick="addError()">❌ Errore</button>
  <span>Errori: <span id="err_count_{widget_id}">0</span></span>
</div>
<div class="dem-grid">
{righe_html}
</div>
<div class="stats" id="stats_{widget_id}"></div>

<script>
let startTime_{widget_id} = null;
let interval_{widget_id}  = null;
let elapsed_{widget_id}   = 0;
let errors_{widget_id}    = 0;
let running_{widget_id}   = false;

function startTimer() {{
  if (running_{widget_id}) return;
  running_{widget_id} = true;
  startTime_{widget_id} = Date.now() - elapsed_{widget_id} * 1000;
  interval_{widget_id} = setInterval(() => {{
    elapsed_{widget_id} = (Date.now() - startTime_{widget_id}) / 1000;
    document.getElementById('timer_{widget_id}').textContent =
      elapsed_{widget_id}.toFixed(1) + 's';
  }}, 100);
}}

function stopTimer() {{
  if (!running_{widget_id}) return;
  clearInterval(interval_{widget_id});
  running_{widget_id} = false;
  const stats = document.getElementById('stats_{widget_id}');
  stats.innerHTML = `<b>Tempo finale: ${{elapsed_{widget_id}.toFixed(2)}}s</b> |
    Errori: ${{errors_{widget_id}}} | Copia questi valori nel pannello sopra.`;
}}

function addError() {{
  errors_{widget_id}++;
  document.getElementById('err_count_{widget_id}').textContent =
    errors_{widget_id};
}}

function markCell(el) {{
  el.classList.toggle('marked');
  if (el.classList.contains('marked')) {{
    errors_{widget_id}++;
  }} else {{
    errors_{widget_id} = Math.max(0, errors_{widget_id} - 1);
  }}
  document.getElementById('err_count_{widget_id}').textContent =
    errors_{widget_id};
}}
</script>
</body>
</html>
"""


def render_kd_widget() -> dict:
    """
    Widget K-D (King-Devick) con timer per carta.
    Restituisce dict risultati.
    """
    st.subheader("👁️ K-D Test — King-Devick (Interattivo)")
    st.caption("Tre card di numeri da leggere ad alta voce il più velocemente possibile.")

    n_cards = st.selectbox("Numero di card", [3, 4], index=0,
                           key="kd_n_cards")
    cards_to_show = _KD_CARDS[:n_cards + 1]  # include card demo

    tab_labels = ["📋 Demo"] + [f"Card {i}" for i in range(1, n_cards + 1)] + ["📊 Risultati"]
    tabs = st.tabs(tab_labels)

    tempi  = []
    errori = []

    for idx, (tab, card_data) in enumerate(zip(tabs[:-1], cards_to_show)):
        with tab:
            label = "Demo" if idx == 0 else f"Card {idx}"
            kd_html = _build_kd_html(f"kd_{idx}", card_data, label)
            st.components.v1.html(kd_html, height=420, scrolling=False)

            c1, c2 = st.columns(2)
            with c1:
                t = st.number_input(f"Tempo {label} (sec)",
                                    min_value=0.0, max_value=300.0,
                                    value=0.0, step=0.1,
                                    key=f"kd_tempo_{idx}")
                tempi.append(float(t))
            with c2:
                e = st.number_input(f"Errori {label}",
                                    min_value=0, max_value=30,
                                    value=0, step=1, key=f"kd_err_{idx}")
                errori.append(int(e))

    risultati_kd = {}
    with tabs[-1]:
        validi_t = [t for t in tempi[1:] if t > 0]
        validi_e = errori[1:]
        if validi_t:
            totale_t = sum(validi_t)
            totale_e = sum(validi_e)

            st.markdown("### Riepilogo K-D Test")
            col1, col2, col3 = st.columns(3)
            col1.metric("Tempo totale", f"{totale_t:.1f}s")
            col2.metric("Errori totali", totale_e)
            col3.metric("Errori × Card",
                        " / ".join(str(e) for e in validi_e))

            # delta tra card (progressione)
            if len(validi_t) > 1:
                st.markdown("**Trend (deve migliorare card→card):**")
                for i in range(len(validi_t)):
                    delta = (validi_t[i] - validi_t[i-1]) if i > 0 else 0.0
                    st.markdown(
                        f"Card {i+1}: **{validi_t[i]:.1f}s** "
                        f"({'+' if delta>=0 else ''}{delta:.1f}s)")

            risultati_kd = {
                "KD_tempi": validi_t,
                "KD_errori": validi_e,
                "KD_tempo_totale": totale_t,
                "KD_errori_totale": totale_e,
            }
        else:
            st.info("Inserisci i tempi per le card per visualizzare i risultati.")

    return risultati_kd


def _build_kd_html(widget_id: str, card_data: list, label: str) -> str:
    righe_html = ""
    for riga in card_data:
        celle = " &nbsp; ".join(
            f'<span class="kd-num">{n}</span>' for n in riga
        )
        righe_html += f'<div class="kd-row">{celle}</div>\n'

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Courier New', monospace; background: #ffffff;
          margin: 0; padding: 14px; }}
  h3   {{ font-size: 14px; color: #0d1117; margin-bottom:8px; }}
  .timer-bar {{ display:flex; align-items:center; gap:10px; margin-bottom:12px; }}
  #timer_{widget_id} {{ font-size: 32px; font-weight:bold; color:#0969da; min-width:90px; }}
  button {{ padding:7px 16px; border:none; border-radius:6px;
            cursor:pointer; font-size:13px; font-weight:bold; }}
  #btn_start_{widget_id} {{ background:#2ea44f; color:white; }}
  #btn_stop_{widget_id}  {{ background:#cf222e; color:white; }}
  .kd-card  {{ border:2px solid #ccc; border-radius:10px; padding:16px;
               background:#fafafa; display:inline-block; }}
  .kd-row   {{ font-size:32px; font-weight:bold; color:#0d1117;
               letter-spacing:12px; margin-bottom:10px; text-align:center; }}
  .kd-num   {{ cursor:pointer; padding:2px 4px; border-radius:4px; }}
  .kd-num:hover   {{ background:#fff3cd; }}
  .kd-num.clicked {{ color:#cf222e; text-decoration:line-through; }}
  .final {{ margin-top:10px; font-weight:bold; font-size:14px; color:#2ea44f; }}
</style>
</head>
<body>
<h3>👁 K-D {label}</h3>
<div class="timer-bar">
  <div id="timer_{widget_id}">0.0s</div>
  <button id="btn_start_{widget_id}" onclick="startTimer()">▶ Avvia</button>
  <button id="btn_stop_{widget_id}"  onclick="stopTimer()">⏹ Stop</button>
</div>
<div class="kd-card">
{righe_html}
</div>
<div class="final" id="final_{widget_id}"></div>
<script>
let t0_{widget_id}  = null;
let ivl_{widget_id} = null;
let run_{widget_id} = false;
let el_{widget_id}  = 0;

function startTimer() {{
  if (run_{widget_id}) return;
  run_{widget_id} = true;
  t0_{widget_id}  = Date.now() - el_{widget_id} * 1000;
  ivl_{widget_id} = setInterval(() => {{
    el_{widget_id} = (Date.now() - t0_{widget_id}) / 1000;
    document.getElementById('timer_{widget_id}').textContent =
      el_{widget_id}.toFixed(1) + 's';
  }}, 100);
}}

function stopTimer() {{
  if (!run_{widget_id}) return;
  clearInterval(ivl_{widget_id});
  run_{widget_id} = false;
  document.getElementById('final_{widget_id}').textContent =
    '✅ Tempo: ' + el_{widget_id}.toFixed(2) + 's — copia nel pannello sopra.';
}}
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE F — Export Dati Statistici
# ══════════════════════════════════════════════════════════════════════

_EXPORT_QUERIES = {
    "pazienti_anagrafica": """
        SELECT id, nome, cognome, data_nascita, sesso,
               EXTRACT(YEAR FROM AGE(data_nascita))::int AS eta,
               created_at::date AS data_inserimento
        FROM pazienti
        ORDER BY created_at DESC
    """,
    "risultati_dem": """
        SELECT p.id AS paziente_id,
               p.nome || ' ' || p.cognome AS paziente,
               EXTRACT(YEAR FROM AGE(p.data_nascita))::int AS eta,
               (vv.dati_json::json->>'DEM_tipo') AS dem_tipo,
               (vv.dati_json::json->>'DEM_tempo_A')::float AS dem_tempo_a,
               (vv.dati_json::json->>'DEM_tempo_C')::float AS dem_tempo_c,
               (vv.dati_json::json->>'DEM_ratio')::float AS dem_ratio,
               (vv.dati_json::json->>'DEM_errori')::int AS dem_errori
        FROM pazienti p
        JOIN valutazioni_visive vv ON vv.paziente_id = p.id
        WHERE vv.dati_json::json->>'DEM_tipo' IS NOT NULL
        ORDER BY p.id
    """,
    "risultati_inpp": """
        SELECT p.id AS paziente_id,
               p.nome || ' ' || p.cognome AS paziente,
               EXTRACT(YEAR FROM AGE(p.data_nascita))::int AS eta,
               (inpp.dati_json::json->>'indice_disfunzione_pct')::float AS indice_disfunzione,
               (inpp.dati_json::json->>'oculomotoria_score')::float AS score_oculomotorio,
               inpp.dati_json::json->>'lateralita' AS lateralita_note
        FROM pazienti p
        JOIN inpp_neuromotorio inpp ON inpp.paziente_id = p.id
        ORDER BY p.id
    """,
    "risultati_nps": """
        SELECT p.id AS paziente_id,
               p.nome || ' ' || p.cognome AS paziente,
               n.tipo AS nps_tipo,
               (n.dati_json::json->>'qi_totale')::float AS qi_totale,
               n.data_valutazione
        FROM pazienti p
        JOIN nps_valutazioni n ON n.paziente_id = p.id
        ORDER BY p.id
    """,
    "risultati_tvps": """
        SELECT p.id AS paziente_id,
               p.nome || ' ' || p.cognome AS paziente,
               EXTRACT(YEAR FROM AGE(p.data_nascita))::int AS eta,
               (vv.dati_json::json->>'discriminazione_visiva_scaled')::int AS discrim_visiva,
               (vv.dati_json::json->>'memoria_visiva_scaled')::int AS mem_visiva,
               (vv.dati_json::json->>'relazioni_spaziali_scaled')::int AS rel_spaziali,
               (vv.dati_json::json->>'memoria_visiva_sequenziale_scaled')::int AS mem_seq,
               (vv.dati_json::json->>'figura_sfondo_scaled')::int AS figura_sfondo,
               (vv.dati_json::json->>'standard_score')::int AS standard_score,
               (vv.dati_json::json->>'percentile')::int AS percentile
        FROM pazienti p
        JOIN valutazioni_visive vv ON vv.paziente_id = p.id
        WHERE vv.dati_json::json->>'standard_score' IS NOT NULL
        ORDER BY p.id
    """,
    "relazioni_cliniche": """
        SELECT r.id, r.paziente_id,
               p.nome || ' ' || p.cognome AS paziente,
               r.tipo, r.titolo, r.data_relazione,
               r.stato, r.professionista, r.approvata_il
        FROM relazioni_cliniche r
        JOIN pazienti p ON p.id = r.paziente_id
        ORDER BY r.data_relazione DESC
    """,
}

_EXPORT_LABELS = {
    "pazienti_anagrafica":  "👥 Anagrafica pazienti",
    "risultati_dem":        "👁️ DEM — tutti i pazienti",
    "risultati_inpp":       "🧠 INPP — indici disfunzione",
    "risultati_nps":        "📊 NPS — QI e indici",
    "risultati_tvps":       "🎨 TVPS — profili subtest",
    "relazioni_cliniche":   "📄 Relazioni cliniche",
}


def _esegui_query(conn, sql: str):
    """Esegui query e ritorna (colonne, righe)."""
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return cols, rows


def _df_to_excel_bytes(cols: list, rows: list) -> bytes:
    """Converte risultati query in Excel bytes."""
    if not _HAS_PANDAS:
        return b""
    try:
        import openpyxl  # noqa
        df = pd.DataFrame(rows, columns=cols)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Dati")
            ws = writer.sheets["Dati"]
            # Auto-width colonne
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 40)
        return buf.getvalue()
    except Exception:
        return b""


def _df_to_csv_bytes(cols: list, rows: list) -> bytes:
    if not _HAS_PANDAS:
        lines = [";".join(cols)]
        for row in rows:
            lines.append(";".join(str(v) if v is not None else "" for v in row))
        return "\n".join(lines).encode("utf-8-sig")
    df = pd.DataFrame(rows, columns=cols)
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


def render_export_statistici(conn) -> None:
    """
    Pannello Streamlit per export dati statistici.
    Aggiungilo nella sezione Amministrazione del gestionale.
    """
    st.subheader("📊 Export Dati Statistici")
    st.caption(
        "Esporta i dati clinici aggregati per ricerca, analisi e reportistica."
    )

    formato = st.radio("Formato export", ["Excel (.xlsx)", "CSV (;)"],
                       horizontal=True, key="export_formato")

    st.markdown("---")

    for chiave, label in _EXPORT_LABELS.items():
        with st.expander(label):
            sql = _EXPORT_QUERIES[chiave]
            col_antepr, col_scarica = st.columns([3, 1])

            with col_antepr:
                if st.button(f"👁 Anteprima", key=f"prev_{chiave}"):
                    try:
                        cols, rows = _esegui_query(conn, sql)
                        if rows:
                            if _HAS_PANDAS:
                                df = pd.DataFrame(rows[:20], columns=cols)
                                st.dataframe(df, use_container_width=True)
                            else:
                                st.write(rows[:5])
                            st.caption(f"Totale righe: {len(rows)}")
                        else:
                            st.info("Nessun dato disponibile.")
                    except Exception as e:
                        st.error(f"Errore query: {e}")

            with col_scarica:
                if st.button(f"⬇️ Scarica", key=f"dl_{chiave}", type="primary"):
                    try:
                        cols, rows = _esegui_query(conn, sql)
                        if not rows:
                            st.warning("Nessun dato.")
                        else:
                            data_oggi = datetime.date.today().strftime("%Y%m%d")
                            if "Excel" in formato:
                                file_bytes = _df_to_excel_bytes(cols, rows)
                                filename   = f"{chiave}_{data_oggi}.xlsx"
                                mime_type  = ("application/vnd.openxmlformats-"
                                              "officedocument.spreadsheetml.sheet")
                            else:
                                file_bytes = _df_to_csv_bytes(cols, rows)
                                filename   = f"{chiave}_{data_oggi}.csv"
                                mime_type  = "text/csv"

                            st.download_button(
                                label=f"📥 {filename}",
                                data=file_bytes,
                                file_name=filename,
                                mime=mime_type,
                                key=f"dl_btn_{chiave}",
                            )
                    except Exception as e:
                        st.error(f"Errore export: {e}")

    st.markdown("---")
    st.markdown("### 📈 Statistiche rapide")
    if st.button("Calcola statistiche aggregate", key="calc_stats"):
        try:
            # Pazienti totali
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM pazienti")
            n_paz = cur.fetchone()[0]

            cur.execute("""
                SELECT AVG((dati_json::json->>'DEM_ratio')::float)
                FROM valutazioni_visive
                WHERE dati_json::json->>'DEM_ratio' IS NOT NULL
            """)
            avg_ratio_row = cur.fetchone()
            avg_ratio = avg_ratio_row[0] if avg_ratio_row and avg_ratio_row[0] else None

            cur.execute("""
                SELECT AVG((dati_json::json->>'indice_disfunzione_pct')::float)
                FROM inpp_neuromotorio
                WHERE dati_json::json->>'indice_disfunzione_pct' IS NOT NULL
            """)
            avg_inpp_row = cur.fetchone()
            avg_inpp = avg_inpp_row[0] if avg_inpp_row and avg_inpp_row[0] else None

            cur.execute("""
                SELECT AVG((dati_json::json->>'qi_totale')::float)
                FROM nps_valutazioni
                WHERE dati_json::json->>'qi_totale' IS NOT NULL
            """)
            avg_qi_row = cur.fetchone()
            avg_qi = avg_qi_row[0] if avg_qi_row and avg_qi_row[0] else None

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pazienti totali", n_paz)
            c2.metric("DEM ratio medio",
                      f"{avg_ratio:.2f}" if avg_ratio else "n.d.")
            c3.metric("INPP medio (%)",
                      f"{avg_inpp:.1f}" if avg_inpp else "n.d.")
            c4.metric("QI medio (NPS)",
                      f"{avg_qi:.1f}" if avg_qi else "n.d.")

        except Exception as e:
            st.error(f"Errore statistiche: {e}")


# ══════════════════════════════════════════════════════════════════════
#  ROUTER — funzione di aggregazione per app_main_router.py
# ══════════════════════════════════════════════════════════════════════

def render_nuovi_moduli(conn, sezione: str, paziente_id: Optional[int] = None) -> None:
    """
    Dispatcher per tutte le sezioni nuove.
    Aggiungilo in app_main_router.py:

        elif sezione == "NPS":
            render_nuovi_moduli(conn, "NPS", paziente_id)
        elif sezione == "ReportPDF":
            render_nuovi_moduli(conn, "ReportPDF", paziente_id)
        ...
    """
    if sezione == "NPS":
        if paziente_id:
            render_nps(conn, paziente_id)
        else:
            st.warning("Seleziona un paziente per accedere alla sezione NPS.")

    elif sezione == "PianoVT":
        if paziente_id:
            render_piano_vt(conn, paziente_id)
        else:
            st.warning("Seleziona un paziente.")

    elif sezione == "ReportPDF":
        if paziente_id:
            render_report_pdf_ui(conn, paziente_id)
        else:
            st.warning("Seleziona un paziente.")

    elif sezione == "DEM":
        render_dem_widget()

    elif sezione == "KD":
        render_kd_widget()

    elif sezione == "ExportStatistici":
        render_export_statistici(conn)

    elif sezione == "SeedDemo":
        render_seed_panel(conn)

    else:
        st.error(f"Sezione sconosciuta: {sezione}")


# ══════════════════════════════════════════════════════════════════════
#  __main__ — test locale senza DB
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    st.set_page_config(page_title="Test Nuovi Moduli", layout="wide")
    st.title("🧪 Test locale — Nuovi Moduli Gestionale The Organism")
    st.info("In modalità test il DB non è disponibile. "
            "Alcune funzioni salvano/caricano dati solo in demo.")

    sezione_test = st.sidebar.selectbox(
        "Sezione da testare",
        ["DEM Widget", "K-D Widget", "Caso Demo JSON",
         "Grafici PDF (preview)", "Piano VT Demo", "NPS (no DB)"]
    )

    if sezione_test == "DEM Widget":
        render_dem_widget()

    elif sezione_test == "K-D Widget":
        render_kd_widget()

    elif sezione_test == "Caso Demo JSON":
        st.json(CASO_CLINICO_SEED)

    elif sezione_test == "Grafici PDF (preview)":
        st.markdown("#### Anteprima grafici TVPS")
        if _HAS_MATPLOTLIB:
            seed = CASO_CLINICO_SEED
            png = _grafico_tvps(seed["tvps"])
            st.image(png, use_container_width=True)
            st.markdown("#### Anteprima grafico DEM")
            st.image(_grafico_dem(seed["vvf"]), use_container_width=True)
            st.markdown("#### Anteprima radar INPP")
            st.image(_grafico_inpp(seed["inpp"]), use_container_width=True)
            st.markdown("#### Anteprima profilo WISC-V")
            st.image(_grafico_wisc_wais(seed["nps"]["indici_wisc"]),
                     use_container_width=True)
        else:
            st.error("matplotlib non installato.")

    elif sezione_test == "Piano VT Demo":
        diagnosi = CASO_CLINICO_SEED["vvf"]["diagnosi_funzionale"]
        piano = _piano_vt_da_diagnosi(diagnosi)
        st.json(piano)

    elif sezione_test == "NPS (no DB)":
        st.warning("Questa sezione richiede un DB attivo.")
        st.json({
            "WISC-V subtest": list(_WISC5_SUBTEST.keys()),
            "WAIS-IV subtest": list(_WAIS4_SUBTEST.keys()),
        })
