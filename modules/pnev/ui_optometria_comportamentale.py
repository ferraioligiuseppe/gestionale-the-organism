# -*- coding: utf-8 -*-
"""
ui_optometria_comportamentale.py — Modulo Optometria Comportamentale (OEP)
Struttura da FileMaker The Organism:
  1. Esame Refrattivo (lontano / vicino)
  2. Strabismo
  3. Telebinocular Skills (14 test)
  4. Analisi Integrativa OEP (#1–#21E)
  5. Retinoscopie Dinamiche
  6. Test Aggiuntivi
  7. Performance (King-Devick, DEM, Visual Tracking, ecc.)

Pattern identico agli altri moduli PNEV:
  render_optometria_comportamentale(pnev_json, prefix, readonly) -> (dict, summary)
"""

from __future__ import annotations
from datetime import date
from typing import Any
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _n(label: str, val: Any, key: str, min_v: float = -20.0, max_v: float = 20.0,
       step: float = 0.25, fmt: str = "%.2f") -> float:
    return st.number_input(label, min_value=float(min_v), max_value=float(max_v),
                           value=float(val or 0.0), step=float(step), format=fmt, key=key)

def _s(label: str, opts: list, val: str, key: str) -> str:
    idx = opts.index(val) if val in opts else 0
    return st.selectbox(label, opts, index=idx, key=key)

def _t(label: str, val: str, key: str, height: int = 60) -> str:
    return st.text_area(label, value=str(val or ""), height=height, key=key)

def _i(label: str, val: str, key: str) -> str:
    return st.text_input(label, value=str(val or ""), key=key)

def _cb(label: str, val: bool, key: str) -> bool:
    return st.checkbox(label, value=bool(val), key=key)

def _g(d: dict, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
    return d if d != {} else default

def _col_od_os(st_cols, label_od, label_os, val_od, val_os, key_od, key_os,
               min_v=-20.0, max_v=20.0, step=0.25):
    with st_cols[0]:
        v_od = st.number_input(label_od, min_value=float(min_v), max_value=float(max_v),
                               value=float(val_od or 0.0), step=float(step), format="%.2f", key=key_od)
    with st_cols[1]:
        v_os = st.number_input(label_os, min_value=float(min_v), max_value=float(max_v),
                               value=float(val_os or 0.0), step=float(step), format="%.2f", key=key_os)
    return v_od, v_os

LATI = ["—", "OD", "OS", "OO", "Alt"]
DEVIAZIONE_OPTS = ["—", "Ortoforia", "Esoforia", "Esotropia", "Exoforia", "Exotropia",
                   "Iperforia OD", "Iperforia OS", "Cicloforia"]
CORRISP_OPTS = ["—", "CRN", "CRA", "Aniseiconia"]
CONCOMITANZA_OPTS = ["—", "Concomitante", "Inconcomitante", "Paralisi"]
FISSAZIONE_OPTS = ["—", "Centrale", "Eccentrica nasale", "Eccentrica temporale",
                   "Eccentrica superiore", "Eccentrica inferiore"]
COVER_OPTS = ["—", "Negativo", "Esoforia", "Exoforia", "Iperforia OD", "Iperforia OS",
              "Esotropia", "Exotropia"]
STEREO_OPTS = ["—", "< 40\"", "40\"", "60\"", "80\"", "100\"", "140\"", "200\"",
               "Nessuna stereoacuità", "Non testabile"]
DOMINANZA_OPTS = ["—", "OD", "OS"]
RISPOSTA_OPTS = ["—", "Positiva", "Negativa", "Dubbia", "Non testabile"]
QUALITA_OPTS   = ["—", "Buona", "Discreta", "Scarsa", "Non testabile"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. ESAME REFRATTIVO
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_refrattivo(d: dict, px: str) -> dict:
    st.markdown("#### 🔭 Esame Refrattivo")

    # Acuità visiva naturale
    st.markdown("**Acuità visiva naturale (sc)**")
    c = st.columns(3)
    av_nat_od = _i("AV nat. OD", _g(d,"av_naturale","od"), f"{px}_av_nat_od"); 
    av_nat_os = _i("AV nat. OS", _g(d,"av_naturale","os"), f"{px}_av_nat_os")
    av_nat_oo = _i("AV nat. OO", _g(d,"av_naturale","oo"), f"{px}_av_nat_oo")
    with c[0]: av_nat_od = st.text_input("AV nat. OD", _g(d,"av_naturale","od"), key=f"{px}_av_nat_od2")
    with c[1]: av_nat_os = st.text_input("AV nat. OS", _g(d,"av_naturale","os"), key=f"{px}_av_nat_os2")
    with c[2]: av_nat_oo = st.text_input("AV nat. OO", _g(d,"av_naturale","oo"), key=f"{px}_av_nat_oo2")

    # Refrazione soggettiva lontano
    st.markdown("**Refrazione soggettiva — Lontano**")
    col = st.columns(4)
    with col[0]: sf_od = st.number_input("SF OD", -30.0, 30.0, float(_g(d,"lontano","sf_od") or 0), 0.25, format="%.2f", key=f"{px}_sf_od")
    with col[1]: cil_od = st.number_input("Cil OD", -10.0, 10.0, float(_g(d,"lontano","cil_od") or 0), 0.25, format="%.2f", key=f"{px}_cil_od")
    with col[2]: asse_od = st.number_input("Asse OD °", 0.0, 180.0, float(_g(d,"lontano","asse_od") or 0), 1.0, format="%.0f", key=f"{px}_asse_od")
    with col[3]: av_cc_od = st.text_input("AV cc OD", _g(d,"lontano","av_cc_od"), key=f"{px}_av_cc_od")

    col2 = st.columns(4)
    with col2[0]: sf_os = st.number_input("SF OS", -30.0, 30.0, float(_g(d,"lontano","sf_os") or 0), 0.25, format="%.2f", key=f"{px}_sf_os")
    with col2[1]: cil_os = st.number_input("Cil OS", -10.0, 10.0, float(_g(d,"lontano","cil_os") or 0), 0.25, format="%.2f", key=f"{px}_cil_os")
    with col2[2]: asse_os = st.number_input("Asse OS °", 0.0, 180.0, float(_g(d,"lontano","asse_os") or 0), 1.0, format="%.0f", key=f"{px}_asse_os")
    with col2[3]: av_cc_os = st.text_input("AV cc OS", _g(d,"lontano","av_cc_os"), key=f"{px}_av_cc_os")

    # Aggiunta vicino (Add)
    st.markdown("**Aggiunta vicino (Add)**")
    c3 = st.columns(3)
    with c3[0]: add_od = st.number_input("Add OD", 0.0, 4.0, float(_g(d,"add","od") or 0), 0.25, format="%.2f", key=f"{px}_add_od")
    with c3[1]: add_os = st.number_input("Add OS", 0.0, 4.0, float(_g(d,"add","os") or 0), 0.25, format="%.2f", key=f"{px}_add_os")
    with c3[2]: av_vicino = st.text_input("AV vicino cc", _g(d,"add","av_vicino"), key=f"{px}_av_vicino")

    # Occhiali in uso
    st.markdown("**Occhiali/LAC in uso**")
    rx_in_uso = _t("Rx in uso (descrizione)", _g(d,"rx_in_uso"), f"{px}_rx_in_uso", height=68)

    note_ref = _t("Note refrattive", _g(d,"note_refrattivo"), f"{px}_note_ref", height=68)

    return {
        "av_naturale": {"od": av_nat_od, "os": av_nat_os, "oo": av_nat_oo},
        "lontano": {"sf_od": sf_od, "cil_od": cil_od, "asse_od": asse_od, "av_cc_od": av_cc_od,
                    "sf_os": sf_os, "cil_os": cil_os, "asse_os": asse_os, "av_cc_os": av_cc_os},
        "add": {"od": add_od, "os": add_os, "av_vicino": av_vicino},
        "rx_in_uso": rx_in_uso,
        "note_refrattivo": note_ref,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. STRABISMO
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_strabismo(d: dict, px: str) -> dict:
    st.markdown("#### 👁️ Strabismo")

    c = st.columns(2)
    with c[0]:
        stato_ref = _s("Stato refrattivo", ["—","Emmetrope","Miopia","Ipermetropia","Astigmatismo","Misto"], _g(d,"stato_refrattivo"), f"{px}_stato_ref")
    with c[1]:
        fissazione_od = _s("Fissazione monoculare OD", FISSAZIONE_OPTS, _g(d,"fissazione_od"), f"{px}_fiss_od")
    c2 = st.columns(2)
    with c2[0]:
        fissazione_os = _s("Fissazione monoculare OS", FISSAZIONE_OPTS, _g(d,"fissazione_os"), f"{px}_fiss_os")
    with c2[1]:
        deviazione = _s("Deviazione oculare (Cover test)", DEVIAZIONE_OPTS, _g(d,"deviazione"), f"{px}_deviazione")

    c3 = st.columns(3)
    with c3[0]:
        dev_dp_lon = st.number_input("Deviazione DP (lontano)", -60.0, 60.0, float(_g(d,"dev_dp_lontano") or 0), 1.0, format="%.0f", key=f"{px}_dev_dp_lon")
    with c3[1]:
        dev_dp_vic = st.number_input("Deviazione DP (vicino)", -60.0, 60.0, float(_g(d,"dev_dp_vicino") or 0), 1.0, format="%.0f", key=f"{px}_dev_dp_vic")
    with c3[2]:
        corrisp = _s("Corrispondenza retinica", CORRISP_OPTS, _g(d,"corrispondenza_retinica"), f"{px}_corrisp")

    c4 = st.columns(2)
    with c4[0]:
        concomitanza = _s("Concomitanza", CONCOMITANZA_OPTS, _g(d,"concomitanza"), f"{px}_concomitanza")
    with c4[1]:
        stereo = _s("Stereoacuità", STEREO_OPTS, _g(d,"stereoacuita"), f"{px}_stereo")

    dominanza_oculare = _s("Dominanza oculare", DOMINANZA_OPTS, _g(d,"dominanza_oculare"), f"{px}_dom_ocul")
    note_strab = _t("Note strabismo", _g(d,"note_strabismo"), f"{px}_note_strab", height=68)

    return {
        "stato_refrattivo": stato_ref,
        "fissazione_od": fissazione_od,
        "fissazione_os": fissazione_os,
        "deviazione": deviazione,
        "dev_dp_lontano": dev_dp_lon,
        "dev_dp_vicino": dev_dp_vic,
        "corrispondenza_retinica": corrisp,
        "concomitanza": concomitanza,
        "stereoacuita": stereo,
        "dominanza_oculare": dominanza_oculare,
        "note_strabismo": note_strab,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. TELEBINOCULAR SKILLS (14 test)
# ─────────────────────────────────────────────────────────────────────────────

TELEBINOCULAR_TESTS = [
    ("T1",  "Acuità visiva lontano OD (Telebinocular)"),
    ("T2",  "Acuità visiva lontano OS (Telebinocular)"),
    ("T3",  "Acuità visiva lontano binoculare"),
    ("T4",  "Fusione lontano (Worth 4 Dot)"),
    ("T5",  "Fusione vicino (Worth 4 Dot)"),
    ("T6",  "Foria lontano verticale"),
    ("T7",  "Foria lontano laterale"),
    ("T8",  "Foria vicino verticale"),
    ("T9",  "Foria vicino laterale"),
    ("T10", "Convergenza — punto prossimo (PPC)"),
    ("T11", "Divergenza — punto prossimo"),
    ("T12", "Accomodazione — ampiezza OD"),
    ("T13", "Accomodazione — ampiezza OS"),
    ("T14", "Flessibilità accomodativa binoculare (cpm)"),
]

def _sezione_telebinocular(d: dict, px: str) -> dict:
    st.markdown("#### 🔬 Telebinocular Skills (14 test)")
    risultati = d.get("telebinocular", {}) or {}
    nuovi = {}

    for code, label in TELEBINOCULAR_TESTS:
        c = st.columns([3, 2, 2])
        with c[0]:
            st.markdown(f"**{code}** — {label}")
        with c[1]:
            valore = st.text_input("Valore", value=str(risultati.get(f"{code}_val", "")),
                                   key=f"{px}_{code}_val", label_visibility="collapsed",
                                   placeholder="Valore")
        with c[2]:
            qualita = _s("", QUALITA_OPTS, risultati.get(f"{code}_q", "—"),
                         f"{px}_{code}_q")
        nuovi[f"{code}_val"] = valore
        nuovi[f"{code}_q"] = qualita

    note_tb = _t("Note Telebinocular", d.get("note_telebinocular", ""), f"{px}_note_tb", height=68)

    return {"telebinocular": nuovi, "note_telebinocular": note_tb}


# ─────────────────────────────────────────────────────────────────────────────
# 4. ANALISI INTEGRATIVA OEP (#1–#21E)
# ─────────────────────────────────────────────────────────────────────────────

OEP_FINDINGS = [
    ("#1",   "Acuità visiva sc (lontano)"),
    ("#2",   "Cover test lontano"),
    ("#3",   "Cover test vicino"),
    ("#4",   "Punto prossimo di convergenza (PPC)"),
    ("#5",   "Motilità oculare (saccadi e inseguimenti)"),
    ("#6",   "Retinoscopia statica OD"),
    ("#6s",  "Retinoscopia statica OS"),
    ("#7",   "Retinoscopia dinamica (MEM) OD"),
    ("#7s",  "Retinoscopia dinamica (MEM) OS"),
    ("#8",   "Cross cilindro binoculare vicino — Sf"),
    ("#8c",  "Cross cilindro binoculare vicino — Cil/Asse"),
    ("#9",   "Foria lontano (Von Graefe)"),
    ("#10",  "Foria vicino (Von Graefe)"),
    ("#11",  "Fusione lontano BI (base interna)"),
    ("#12",  "Fusione lontano BE (base esterna)"),
    ("#13",  "Fusione vicino BI (base interna)"),
    ("#14",  "Fusione vicino BE (base esterna)"),
    ("#15",  "Flessibilità fusionale lontano"),
    ("#16",  "Flessibilità fusionale vicino"),
    ("#17",  "Accomodazione relativa positiva (ARP)"),
    ("#18",  "Accomodazione relativa negativa (ARN)"),
    ("#19",  "Flessibilità accomodativa monoculare OD"),
    ("#19s", "Flessibilità accomodativa monoculare OS"),
    ("#20",  "Flessibilità accomodativa binoculare"),
    ("#21",  "Stereopsi (Randot/TNO/Lang)"),
    ("#21E", "Stereopsi — acuità fine (arcsec)"),
]

def _sezione_oep(d: dict, px: str) -> dict:
    st.markdown("#### 📊 Analisi Integrativa OEP (#1–#21E)")
    oep = d.get("oep", {}) or {}
    nuovi = {}

    for code, label in OEP_FINDINGS:
        c = st.columns([1, 3, 3, 2])
        with c[0]:
            st.markdown(f"`{code}`")
        with c[1]:
            st.caption(label)
        with c[2]:
            val = st.text_input("Risultato", value=str(oep.get(f"{code}_val", "")),
                                key=f"{px}_oep{code}_val", label_visibility="collapsed",
                                placeholder="Risultato")
        with c[3]:
            nota = st.text_input("Nota", value=str(oep.get(f"{code}_nota", "")),
                                 key=f"{px}_oep{code}_nota", label_visibility="collapsed",
                                 placeholder="Nota")
        nuovi[f"{code}_val"] = val
        nuovi[f"{code}_nota"] = nota

    note_oep = _t("Note analisi OEP", d.get("note_oep", ""), f"{px}_note_oep", height=68)

    return {"oep": nuovi, "note_oep": note_oep}


# ─────────────────────────────────────────────────────────────────────────────
# 5. RETINOSCOPIE DINAMICHE
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_retinoscopie(d: dict, px: str) -> dict:
    st.markdown("#### 🔦 Retinoscopie Dinamiche")
    ret = d.get("retinoscopie", {}) or {}

    st.markdown("**MEM (Monocular Estimation Method)**")
    c = st.columns(2)
    with c[0]:
        mem_od = st.number_input("MEM OD (D)", -3.0, 3.0, float(ret.get("mem_od") or 0), 0.25, format="%.2f", key=f"{px}_mem_od")
    with c[1]:
        mem_os = st.number_input("MEM OS (D)", -3.0, 3.0, float(ret.get("mem_os") or 0), 0.25, format="%.2f", key=f"{px}_mem_os")

    st.markdown("**BCC (Bell Copy)**")
    c2 = st.columns(2)
    with c2[0]:
        bcc_od = st.number_input("BCC OD (D)", -3.0, 3.0, float(ret.get("bcc_od") or 0), 0.25, format="%.2f", key=f"{px}_bcc_od")
    with c2[1]:
        bcc_os = st.number_input("BCC OS (D)", -3.0, 3.0, float(ret.get("bcc_os") or 0), 0.25, format="%.2f", key=f"{px}_bcc_os")

    st.markdown("**Nott Retinoscopy**")
    c3 = st.columns(2)
    with c3[0]:
        nott_od = st.number_input("Nott OD (D)", -3.0, 3.0, float(ret.get("nott_od") or 0), 0.25, format="%.2f", key=f"{px}_nott_od")
    with c3[1]:
        nott_os = st.number_input("Nott OS (D)", -3.0, 3.0, float(ret.get("nott_os") or 0), 0.25, format="%.2f", key=f"{px}_nott_os")

    lag_acc = st.number_input("Lag accomodativo medio (D)", 0.0, 3.0, float(ret.get("lag_accomodativo") or 0), 0.25, format="%.2f", key=f"{px}_lag_acc")
    note_ret = _t("Note retinoscopie", ret.get("note", ""), f"{px}_note_ret", height=68)

    return {
        "retinoscopie": {
            "mem_od": mem_od, "mem_os": mem_os,
            "bcc_od": bcc_od, "bcc_os": bcc_os,
            "nott_od": nott_od, "nott_os": nott_os,
            "lag_accomodativo": lag_acc,
            "note": note_ret,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. TEST AGGIUNTIVI
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_test_aggiuntivi(d: dict, px: str) -> dict:
    st.markdown("#### 🧪 Test Aggiuntivi")
    ta = d.get("test_aggiuntivi", {}) or {}

    c = st.columns(2)
    with c[0]:
        worth_lon = _s("Worth 4 Dot lontano", ["—","Fusione","Soppressione OD","Soppressione OS","Diplopia","4 punti"], ta.get("worth_lontano","—"), f"{px}_worth_lon")
        worth_vic = _s("Worth 4 Dot vicino", ["—","Fusione","Soppressione OD","Soppressione OS","Diplopia","4 punti"], ta.get("worth_vicino","—"), f"{px}_worth_vic")
        bagolini = _s("Bagolini (filtri striati)", ["—","CRN","Soppressione","CRA","Diplopia"], ta.get("bagolini","—"), f"{px}_bagolini")
        maddox = st.text_input("Maddox Rod", ta.get("maddox",""), key=f"{px}_maddox")
    with c[1]:
        amsler = _s("Griglia di Amsler", ["—","Normale","Metamorfopsia OD","Metamorfopsia OS","Scotoma OD","Scotoma OS"], ta.get("amsler","—"), f"{px}_amsler")
        ishihara = _s("Ishihara (visione colori)", ["—","Normale","Daltonismo R/G","Daltonismo B/Y","Non testabile"], ta.get("ishihara","—"), f"{px}_ishihara")
        sensibilita_contrasto = st.text_input("Sensibilità al contrasto (CSV-1000)", ta.get("sensibilita_contrasto",""), key=f"{px}_sens_contr")
        campo_visivo = st.text_input("Campo visivo (confrontazione/perimetria)", ta.get("campo_visivo",""), key=f"{px}_campo_vis")

    purkinje = _s("Test di Purkinje (fissazione eccentrica)", ["—","Normale","Positivo OD","Positivo OS"], ta.get("purkinje","—"), f"{px}_purkinje")
    note_ta = _t("Note test aggiuntivi", ta.get("note",""), f"{px}_note_ta", height=68)

    return {
        "test_aggiuntivi": {
            "worth_lontano": worth_lon, "worth_vicino": worth_vic,
            "bagolini": bagolini, "maddox": maddox,
            "amsler": amsler, "ishihara": ishihara,
            "sensibilita_contrasto": sensibilita_contrasto,
            "campo_visivo": campo_visivo,
            "purkinje": purkinje,
            "note": note_ta,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_performance(d: dict, px: str) -> dict:
    st.markdown("#### ⚡ Performance Visiva")
    perf = d.get("performance", {}) or {}

    # King-Devick
    st.markdown("**King-Devick Test (saccadi)**")
    c = st.columns(4)
    with c[0]: kd_demo = st.number_input("Demo (sec)", 0.0, 300.0, float(perf.get("kd_demo") or 0), 0.1, format="%.1f", key=f"{px}_kd_demo")
    with c[1]: kd_1 = st.number_input("Card 1 (sec)", 0.0, 300.0, float(perf.get("kd_1") or 0), 0.1, format="%.1f", key=f"{px}_kd_1")
    with c[2]: kd_2 = st.number_input("Card 2 (sec)", 0.0, 300.0, float(perf.get("kd_2") or 0), 0.1, format="%.1f", key=f"{px}_kd_2")
    with c[3]: kd_3 = st.number_input("Card 3 (sec)", 0.0, 300.0, float(perf.get("kd_3") or 0), 0.1, format="%.1f", key=f"{px}_kd_3")
    kd_errori = st.number_input("King-Devick — Errori totali", 0, 50, int(perf.get("kd_errori") or 0), key=f"{px}_kd_errori")
    kd_totale = kd_1 + kd_2 + kd_3
    if kd_totale > 0:
        st.caption(f"Tempo totale (card 1+2+3): **{kd_totale:.1f} sec**")

    # DEM (Developmental Eye Movement)
    st.markdown("**DEM (Developmental Eye Movement)**")
    c2 = st.columns(3)
    with c2[0]: dem_vert = st.number_input("DEM Verticale (sec)", 0.0, 300.0, float(perf.get("dem_verticale") or 0), 0.1, format="%.1f", key=f"{px}_dem_vert")
    with c2[1]: dem_oriz = st.number_input("DEM Orizzontale (sec)", 0.0, 300.0, float(perf.get("dem_orizzontale") or 0), 0.1, format="%.1f", key=f"{px}_dem_oriz")
    with c2[2]: dem_errori = st.number_input("DEM Errori", 0, 50, int(perf.get("dem_errori") or 0), key=f"{px}_dem_errori")
    dem_ratio = st.number_input("DEM Ratio (H/V)", 0.0, 5.0, float(perf.get("dem_ratio") or 0), 0.01, format="%.2f", key=f"{px}_dem_ratio")
    dem_interpreta = _s("DEM Interpretazione", ["—","Normale","Tipo I (saccadi)","Tipo II (accomodazione)","Tipo III (misto)","Tipo IV"], perf.get("dem_interpretazione","—"), f"{px}_dem_interp")

    # Visual Tracking
    st.markdown("**Visual Tracking (NSUCO / Groffman)**")
    c3 = st.columns(2)
    with c3[0]:
        track_saccadi = _s("Saccadi — qualità", QUALITA_OPTS, perf.get("tracking_saccadi","—"), f"{px}_track_sacc")
        track_inseg = _s("Inseguimenti — qualità", QUALITA_OPTS, perf.get("tracking_inseguimenti","—"), f"{px}_track_inseg")
    with c3[1]:
        track_sacc_score = st.text_input("Saccadi — score NSUCO", perf.get("tracking_saccadi_score",""), key=f"{px}_track_sacc_score")
        track_inseg_score = st.text_input("Inseguimenti — score NSUCO", perf.get("tracking_inseg_score",""), key=f"{px}_track_inseg_score")

    # Visagraph / ReadAlyzer (se disponibile)
    st.markdown("**Visagraph / Eye-tracking lettura** (se disponibile)")
    c4 = st.columns(3)
    with c4[0]: visag_fix = st.number_input("Fissazioni/100 parole", 0.0, 500.0, float(perf.get("visag_fissazioni") or 0), 1.0, format="%.0f", key=f"{px}_visag_fix")
    with c4[1]: visag_reg = st.number_input("Regressioni/100 parole", 0.0, 200.0, float(perf.get("visag_regressioni") or 0), 1.0, format="%.0f", key=f"{px}_visag_reg")
    with c4[2]: visag_wpm = st.number_input("Velocità lettura (wpm)", 0.0, 800.0, float(perf.get("visag_wpm") or 0), 1.0, format="%.0f", key=f"{px}_visag_wpm")
    visag_grade = st.text_input("Grade equivalent (Visagraph)", perf.get("visag_grade",""), key=f"{px}_visag_grade")

    note_perf = _t("Note performance", perf.get("note",""), f"{px}_note_perf", height=68)

    return {
        "performance": {
            "kd_demo": kd_demo, "kd_1": kd_1, "kd_2": kd_2, "kd_3": kd_3,
            "kd_totale": kd_totale, "kd_errori": kd_errori,
            "dem_verticale": dem_vert, "dem_orizzontale": dem_oriz,
            "dem_errori": dem_errori, "dem_ratio": dem_ratio,
            "dem_interpretazione": dem_interpreta,
            "tracking_saccadi": track_saccadi,
            "tracking_saccadi_score": track_sacc_score,
            "tracking_inseguimenti": track_inseg,
            "tracking_inseg_score": track_inseg_score,
            "visag_fissazioni": visag_fix, "visag_regressioni": visag_reg,
            "visag_wpm": visag_wpm, "visag_grade": visag_grade,
            "note": note_perf,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_optometria_comportamentale(
    optom_json: dict | None,
    prefix: str,
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Renderizza il modulo completo di optometria comportamentale.
    optom_json: dict salvato in visita_json["optometria_comportamentale"] o {}
    Ritorna (dict aggiornato, summary_text)
    """
    if optom_json is None:
        optom_json = {}

    if readonly:
        st.markdown("**Optometria comportamentale — riepilogo:**")
        ref = optom_json.get("refrattivo", {})
        st.write(f"SF OD: {ref.get('lontano',{}).get('sf_od',0)} | SF OS: {ref.get('lontano',{}).get('sf_os',0)}")
        perf = optom_json.get("performance", {})
        if perf.get("kd_totale"):
            st.write(f"King-Devick totale: {perf['kd_totale']:.1f} sec")
        return optom_json, "Optometria comportamentale (readonly)"

    st.markdown("## 👁️‍🗨️ Optometria Comportamentale")

    tab_ref, tab_strab, tab_tb, tab_oep, tab_ret, tab_add, tab_perf = st.tabs([
        "🔭 Refrattivo",
        "↔️ Strabismo",
        "🔬 Telebinocular",
        "📊 OEP #1–#21E",
        "🔦 Retinoscopie",
        "🧪 Test Aggiuntivi",
        "⚡ Performance",
    ])

    nuovi = dict(optom_json)

    with tab_ref:
        nuovi["refrattivo"] = _sezione_refrattivo(optom_json.get("refrattivo", {}), f"{prefix}_ref")

    with tab_strab:
        nuovi["strabismo"] = _sezione_strabismo(optom_json.get("strabismo", {}), f"{prefix}_strab")

    with tab_tb:
        tb_data = _sezione_telebinocular(optom_json, f"{prefix}_tb")
        nuovi.update(tb_data)

    with tab_oep:
        oep_data = _sezione_oep(optom_json, f"{prefix}_oep")
        nuovi.update(oep_data)

    with tab_ret:
        ret_data = _sezione_retinoscopie(optom_json, f"{prefix}_ret")
        nuovi.update(ret_data)

    with tab_add:
        ta_data = _sezione_test_aggiuntivi(optom_json, f"{prefix}_ta")
        nuovi.update(ta_data)

    with tab_perf:
        perf_data = _sezione_performance(optom_json, f"{prefix}_perf")
        nuovi.update(perf_data)

    nuovi["_meta"] = {"data": date.today().isoformat(), "versione": "optom_v1"}

    # Summary
    ref = nuovi.get("refrattivo", {}).get("lontano", {})
    strab = nuovi.get("strabismo", {})
    perf = nuovi.get("performance", {})

    parts = []
    sf_od = ref.get("sf_od", 0)
    sf_os = ref.get("sf_os", 0)
    if sf_od or sf_os:
        parts.append(f"Rx OD {sf_od:+.2f} OS {sf_os:+.2f}")
    dev = strab.get("deviazione", "—")
    if dev and dev != "—":
        parts.append(f"Deviazione: {dev}")
    stereo = strab.get("stereoacuita", "—")
    if stereo and stereo != "—":
        parts.append(f"Stereo: {stereo}")
    kd = perf.get("kd_totale", 0)
    if kd:
        parts.append(f"K-D: {kd:.1f}s")
    dem_interp = perf.get("dem_interpretazione", "—")
    if dem_interp and dem_interp != "—":
        parts.append(f"DEM: {dem_interp}")

    summary = "Optom. comportamentale — " + (" | ".join(parts) if parts else "compilato")
    return nuovi, summary
