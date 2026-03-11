from __future__ import annotations
import datetime as dt
import json
from typing import Any, Dict, List
from collections.abc import Mapping
import streamlit as st
import matplotlib.pyplot as plt

import pandas as pd
from vision_manager.ui_kit import inject_ui, topbar, card_open, card_close, badge, callout, cta_button
# ---------- Apple-like (lightweight) CSS ----------
def _load_payload_into_form(pj: dict):
    """Carica un payload visita nel form (session_state). Deve essere chiamata PRIMA di creare i widget."""
    if not isinstance(pj, dict):
        return

    # Campi base
    st.session_state["anamnesi"] = pj.get("anamnesi") or ""
    st.session_state["note_visita"] = pj.get("note") or pj.get("note_visita") or ""

    # Acuità visiva
    ac = pj.get("acuita") or {}
    od = ac.get("od") or {}
    os_ = ac.get("os") or {}
    st.session_state["uo_lont_od"] = float(od.get("uo_lont", 0.0) or 0.0)
    st.session_state["uo_lont_os"] = float(os_.get("uo_lont", 0.0) or 0.0)
    st.session_state["cc_lont_od"] = float(od.get("cc_lont", 0.0) or 0.0)
    st.session_state["cc_lont_os"] = float(os_.get("cc_lont", 0.0) or 0.0)
    st.session_state["uo_vic_od"] = float(od.get("uo_vic", 0.0) or 0.0)
    st.session_state["uo_vic_os"] = float(os_.get("uo_vic", 0.0) or 0.0)
    st.session_state["cc_vic_od"] = float(od.get("cc_vic", 0.0) or 0.0)
    st.session_state["cc_vic_os"] = float(os_.get("cc_vic", 0.0) or 0.0)

    # Esame obiettivo
    eo = pj.get("esame_obiettivo") or {}
    st.session_state["cover_test"] = eo.get("cover_test", "") or ""
    st.session_state["motilita"] = eo.get("motilita", "") or ""
    st.session_state["pupille"] = eo.get("pupille", "") or ""
    st.session_state["convergenza"] = eo.get("convergenza", "") or ""
    st.session_state["visione_binoculare"] = eo.get("visione_binoculare", "") or ""
    st.session_state["iop_od"] = float(eo.get("iop_od", 0.0) or 0.0)
    st.session_state["iop_os"] = float(eo.get("iop_os", 0.0) or 0.0)
    st.session_state["pachimetria_od"] = float(eo.get("pachimetria_od", 0.0) or 0.0)
    st.session_state["pachimetria_os"] = float(eo.get("pachimetria_os", 0.0) or 0.0)
    st.session_state["fundus"] = eo.get("fundus", "") or ""

    # Correzione abituale
    ca = pj.get("correzione_abituale") or {}
    od_ab = ca.get("od") or {}
    os_ab = ca.get("os") or {}
    st.session_state["rx_ab_od_sf"] = float(od_ab.get("sf", 0.0) or 0.0)
    st.session_state["rx_ab_od_cyl"] = float(od_ab.get("cyl", 0.0) or 0.0)
    st.session_state["rx_ab_od_ax"] = int(od_ab.get("ax", 0) or 0)
    st.session_state["rx_ab_os_sf"] = float(os_ab.get("sf", 0.0) or 0.0)
    st.session_state["rx_ab_os_cyl"] = float(os_ab.get("cyl", 0.0) or 0.0)
    st.session_state["rx_ab_os_ax"] = int(os_ab.get("ax", 0) or 0)
    st.session_state["add_ab"] = float(ca.get("add", 0.0) or 0.0)

    # Correzione finale
    cf = pj.get("correzione_finale") or {}
    odf = cf.get("od") or {}
    osf = cf.get("os") or {}
    st.session_state["rx_fin_od_sf"] = float(odf.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_od_cyl"] = float(odf.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_od_ax"] = int(odf.get("ax", 0) or 0)
    st.session_state["rx_fin_os_sf"] = float(osf.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_os_cyl"] = float(osf.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_os_ax"] = int(osf.get("ax", 0) or 0)
    st.session_state["add_fin"] = float(cf.get("add", 0.0) or 0.0)

    # Prescrizione / lenti consigliate
    pr = pj.get("prescrizione") or {}
    st.session_state["tipo_lente"] = pr.get("tipo_lente", "") or ""
    st.session_state["trattamento"] = pr.get("trattamento", "") or ""
    st.session_state["uso_consigliato"] = pr.get("uso_consigliato", "") or ""


# ---------- Apple-like (lightweight) CSS ----------
def _apple_css():
    st.markdown(
        """
<style>
:root{
  --bg:#f5f7fb;
  --card:#ffffff;
  --line:#e7ebf3;
  --text:#111827;
  --muted:#6b7280;
  --brand:#2563eb;
  --ok:#10b981;
  --warn:#f59e0b;
  --bad:#ef4444;
  --shadow:0 10px 30px rgba(17,24,39,.06);
  --radius:18px;
}
html, body, [data-testid="stAppViewContainer"] { background:var(--bg); }
.block-container{ padding-top:1rem; padding-bottom:2rem; max-width:1400px; }
.vm-topbar{
  background:linear-gradient(180deg,#ffffff, #fbfcff);
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:22px;
  padding:18px 20px;
  margin:0 0 14px 0;
}
.vm-title{ font-size:1.45rem; font-weight:800; color:var(--text); letter-spacing:.2px; }
.vm-sub{ color:var(--muted); margin-top:4px; }
.vm-pill{
  display:inline-flex; align-items:center; gap:8px;
  padding:8px 12px; border:1px solid var(--line); border-radius:999px;
  background:#fff; color:var(--text); font-size:.9rem; margin-right:8px;
}
.vm-card{
  background:var(--card);
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:var(--radius);
  padding:18px;
  margin:10px 0 14px 0;
}
.vm-section{ font-size:1.05rem; font-weight:800; color:var(--text); margin-bottom:10px; }
.vm-help{ color:var(--muted); font-size:.92rem; margin-top:-4px; margin-bottom:12px; }
.vm-note{
  background:#f9fbff; border:1px dashed #dbe7ff; color:#334155;
  border-radius:14px; padding:10px 12px; font-size:.92rem;
}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stSelectbox"] > div,
div[data-testid="stDateInput"] input{
  border-radius:14px !important;
}
.stButton>button{
  border-radius:14px !important;
  border:1px solid var(--line) !important;
  background:#fff !important;
}
.stButton>button[kind="primary"]{
  background:var(--brand) !important;
  color:#fff !important;
  border-color:transparent !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _safe_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def _safe_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def _fmt_snellen(v: float) -> str:
    try:
        v = float(v)
    except Exception:
        return "0/10"
    v = max(0.0, min(1.6, v))
    return f"{int(round(v*10))}/10"


def _save_payload() -> dict:
    return {
        "anamnesi": st.session_state.get("anamnesi", ""),
        "acuita": {
            "od": {
                "uo_lont": _safe_float(st.session_state.get("uo_lont_od", 0.0)),
                "cc_lont": _safe_float(st.session_state.get("cc_lont_od", 0.0)),
                "uo_vic": _safe_float(st.session_state.get("uo_vic_od", 0.0)),
                "cc_vic": _safe_float(st.session_state.get("cc_vic_od", 0.0)),
            },
            "os": {
                "uo_lont": _safe_float(st.session_state.get("uo_lont_os", 0.0)),
                "cc_lont": _safe_float(st.session_state.get("cc_lont_os", 0.0)),
                "uo_vic": _safe_float(st.session_state.get("uo_vic_os", 0.0)),
                "cc_vic": _safe_float(st.session_state.get("cc_vic_os", 0.0)),
            },
        },
        "esame_obiettivo": {
            "cover_test": st.session_state.get("cover_test", ""),
            "motilita": st.session_state.get("motilita", ""),
            "pupille": st.session_state.get("pupille", ""),
            "convergenza": st.session_state.get("convergenza", ""),
            "visione_binoculare": st.session_state.get("visione_binoculare", ""),
            "iop_od": _safe_float(st.session_state.get("iop_od", 0.0)),
            "iop_os": _safe_float(st.session_state.get("iop_os", 0.0)),
            "pachimetria_od": _safe_float(st.session_state.get("pachimetria_od", 0.0)),
            "pachimetria_os": _safe_float(st.session_state.get("pachimetria_os", 0.0)),
            "fundus": st.session_state.get("fundus", ""),
        },
        "correzione_abituale": {
            "od": {
                "sf": _safe_float(st.session_state.get("rx_ab_od_sf", 0.0)),
                "cyl": _safe_float(st.session_state.get("rx_ab_od_cyl", 0.0)),
                "ax": _safe_int(st.session_state.get("rx_ab_od_ax", 0)),
            },
            "os": {
                "sf": _safe_float(st.session_state.get("rx_ab_os_sf", 0.0)),
                "cyl": _safe_float(st.session_state.get("rx_ab_os_cyl", 0.0)),
                "ax": _safe_int(st.session_state.get("rx_ab_os_ax", 0)),
            },
            "add": _safe_float(st.session_state.get("add_ab", 0.0)),
        },
        "correzione_finale": {
            "od": {
                "sf": _safe_float(st.session_state.get("rx_fin_od_sf", 0.0)),
                "cyl": _safe_float(st.session_state.get("rx_fin_od_cyl", 0.0)),
                "ax": _safe_int(st.session_state.get("rx_fin_od_ax", 0)),
            },
            "os": {
                "sf": _safe_float(st.session_state.get("rx_fin_os_sf", 0.0)),
                "cyl": _safe_float(st.session_state.get("rx_fin_os_cyl", 0.0)),
                "ax": _safe_int(st.session_state.get("rx_fin_os_ax", 0)),
            },
            "add": _safe_float(st.session_state.get("add_fin", 0.0)),
        },
        "prescrizione": {
            "tipo_lente": st.session_state.get("tipo_lente", ""),
            "trattamento": st.session_state.get("trattamento", ""),
            "uso_consigliato": st.session_state.get("uso_consigliato", ""),
        },
        "note": st.session_state.get("note_visita", ""),
    }


def ui_visita_visiva():
    st.set_page_config(page_title="Vision Manager • Visita", layout="wide")
    inject_ui()
    _apple_css()

    if st.session_state.get("vm_pending_payload") is not None:
        pj_pending = st.session_state.pop("vm_pending_payload")
        st.session_state["vm_last_loaded_visita_id"] = st.session_state.pop("vm_pending_visita_id", None)
        _load_payload_into_form(pj_pending)
        st.rerun()

    topbar("Vision Manager", "Visita visiva")

    st.session_state.setdefault("data_visita", dt.date.today())
    st.session_state.setdefault("anamnesi", "")
    st.session_state.setdefault("note_visita", "")

    for k in [
        "uo_lont_od", "uo_lont_os", "cc_lont_od", "cc_lont_os",
        "uo_vic_od", "uo_vic_os", "cc_vic_od", "cc_vic_os",
        "iop_od", "iop_os", "pachimetria_od", "pachimetria_os",
        "rx_ab_od_sf", "rx_ab_od_cyl", "rx_ab_od_ax",
        "rx_ab_os_sf", "rx_ab_os_cyl", "rx_ab_os_ax", "add_ab",
        "rx_fin_od_sf", "rx_fin_od_cyl", "rx_fin_od_ax",
        "rx_fin_os_sf", "rx_fin_os_cyl", "rx_fin_os_ax", "add_fin",
    ]:
        st.session_state.setdefault(k, 0.0 if "ax" not in k else 0)

    for k in [
        "cover_test", "motilita", "pupille", "convergenza", "visione_binoculare", "fundus",
        "tipo_lente", "trattamento", "uso_consigliato"
    ]:
        st.session_state.setdefault(k, "")

    card_open("")
    st.markdown('<div class="vm-section">Dati principali</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        st.date_input("Data visita", key="data_visita")
    with c2:
        anamnesi = st.text_area("Anamnesi", height=110, key="anamnesi")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Acuità visiva</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    fields = [
        ("uo_lont_od", "UO lont OD"), ("uo_lont_os", "UO lont OS"),
        ("cc_lont_od", "CC lont OD"), ("cc_lont_os", "CC lont OS"),
        ("uo_vic_od", "UO vic OD"), ("uo_vic_os", "UO vic OS"),
        ("cc_vic_od", "CC vic OD"), ("cc_vic_os", "CC vic OS"),
    ]
    for i, (k, lab) in enumerate(fields):
        with cols[i % 4]:
            st.number_input(lab, key=k, step=0.1, format="%.1f")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Esame obiettivo</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Cover test", key="cover_test")
        st.text_input("Motilità", key="motilita")
        st.text_input("Pupille", key="pupille")
    with c2:
        st.text_input("Convergenza", key="convergenza")
        st.text_input("Visione binoculare", key="visione_binoculare")
        st.text_input("Fundus", key="fundus")
    with c3:
        st.number_input("IOP OD", key="iop_od", step=0.5, format="%.1f")
        st.number_input("IOP OS", key="iop_os", step=0.5, format="%.1f")
        st.number_input("Pachimetria OD", key="pachimetria_od", step=1.0, format="%.1f")
        st.number_input("Pachimetria OS", key="pachimetria_os", step=1.0, format="%.1f")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Correzione abituale</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("SF OD", key="rx_ab_od_sf", step=0.25, format="%.2f")
        st.number_input("CYL OD", key="rx_ab_od_cyl", step=0.25, format="%.2f")
        st.number_input("AX OD", key="rx_ab_od_ax", step=1, format="%d")
    with c2:
        st.number_input("SF OS", key="rx_ab_os_sf", step=0.25, format="%.2f")
        st.number_input("CYL OS", key="rx_ab_os_cyl", step=0.25, format="%.2f")
        st.number_input("AX OS", key="rx_ab_os_ax", step=1, format="%d")
    with c3:
        st.number_input("ADD", key="add_ab", step=0.25, format="%.2f")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Correzione finale</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("SF OD fin", key="rx_fin_od_sf", step=0.25, format="%.2f")
        st.number_input("CYL OD fin", key="rx_fin_od_cyl", step=0.25, format="%.2f")
        st.number_input("AX OD fin", key="rx_fin_od_ax", step=1, format="%d")
    with c2:
        st.number_input("SF OS fin", key="rx_fin_os_sf", step=0.25, format="%.2f")
        st.number_input("CYL OS fin", key="rx_fin_os_cyl", step=0.25, format="%.2f")
        st.number_input("AX OS fin", key="rx_fin_os_ax", step=1, format="%d")
    with c3:
        st.number_input("ADD fin", key="add_fin", step=0.25, format="%.2f")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Prescrizione</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Tipo lente", key="tipo_lente")
    with c2:
        st.text_input("Trattamento", key="trattamento")
    with c3:
        st.text_input("Uso consigliato", key="uso_consigliato")
    card_close()

    card_open("Sezione")
    st.markdown('<div class="vm-section">Note visita</div>', unsafe_allow_html=True)
    st.text_area("Note", height=120, key="note_visita")
    card_close()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salva payload demo"):
            st.session_state["ultimo_payload_demo"] = _save_payload()
            st.success("Payload salvato in sessione")
    with c2:
        if st.button("Mostra payload demo"):
            st.json(st.session_state.get("ultimo_payload_demo", {}))
