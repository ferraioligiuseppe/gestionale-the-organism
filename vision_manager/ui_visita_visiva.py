from __future__ import annotations
import datetime as dt
import json
from typing import Any, Dict, List
from collections.abc import Mapping
import streamlit as st

# ---------- Apple-like (lightweight) CSS ----------


def _parse_pair_values(s: str):
    """Legge valori tipo '16/15' oppure '520/505'. Ritorna (od, os) float o (None, None)."""
    if not s:
        return (None, None)
    txt = str(s).strip().replace(",", "/").replace(";", "/").replace("\\", "/")
    parts = [p.strip() for p in txt.split("/") if p.strip()]
    if len(parts) == 1:
        try:
            v = float(parts[0])
            return (v, v)
        except Exception:
            return (None, None)
    try:
        od = float(parts[0])
    except Exception:
        od = None
    try:
        os_ = float(parts[1])
    except Exception:
        os_ = None
    return (od, os_)

def _iop_adjusted(iop, cct, ref_cct: float = 540.0):
    """Correzione semplificata (screening) IOP per spessore corneale. Non diagnostico."""
    if iop is None or cct is None:
        return None
    delta = (ref_cct - cct) / 10.0 * 0.7
    return float(iop + delta)

def _clinical_attention(iop_od, iop_os, cct_od, cct_os):
    """Flag di attenzione clinica (screening) combinando IOP e pachimetria."""
    out = {
        "od": {"flag": False, "reason": "", "adj": None},
        "os": {"flag": False, "reason": "", "adj": None},
    }
    for eye in ("od", "os"):
        iop = iop_od if eye == "od" else iop_os
        cct = cct_od if eye == "od" else cct_os
        adj = _iop_adjusted(iop, cct)

        reasons = []
        flag = False

        if iop is not None and iop >= 21:
            flag = True
            reasons.append("IOP ≥ 21 mmHg")

        if cct is not None and cct < 500 and iop is not None and iop >= 18:
            flag = True
            reasons.append("CCT < 500 µm con IOP ≥ 18 (possibile sottostima)")

        if adj is not None and adj >= 21:
            flag = True
            reasons.append(f"IOP stimata (da CCT) ≈ {adj:.1f} mmHg")

        out[eye]["flag"] = flag
        out[eye]["reason"] = "; ".join(reasons)
        out[eye]["adj"] = adj
    return out

def _load_payload_into_form(pj: dict):
    """Carica un payload visita nel form (session_state). Deve essere chiamata PRIMA di creare i widget."""
    if not isinstance(pj, dict):
        return

    # Data visita: per default oggi (così quando salvi crei una nuova visita)
    st.session_state["data_visita"] = dt.date.today()

    st.session_state["anamnesi"] = pj.get("anamnesi") or ""
    st.session_state["note_visita"] = pj.get("note") or pj.get("note_visita") or ""

    # Acuità
    ac = pj.get("acuita") or {}
    nat = ac.get("naturale") or {}
    abi = ac.get("abituale") or {}
    cor = ac.get("corretta") or {}

    for k_src, key in [("od","avn_od"),("os","avn_os"),("oo","avn_oo")]:
        if k_src in nat: st.session_state[key] = nat.get(k_src) or st.session_state.get(key)
    for k_src, key in [("od","ava_od"),("os","ava_os"),("oo","ava_oo")]:
        if k_src in abi: st.session_state[key] = abi.get(k_src) or st.session_state.get(key)
    for k_src, key in [("od","avc_od"),("os","avc_os"),("oo","avc_oo")]:
        if k_src in cor: st.session_state[key] = cor.get(k_src) or st.session_state.get(key)

    # Esame obiettivo
    eo = pj.get("esame_obiettivo") or {}
    for field in ("congiuntiva","cornea","camera_anteriore","cristallino","vitreo","fondo_oculare","pressione_endoculare","pachimetria","pressione_endoculare_od","pressione_endoculare_os","pachimetria_od","pachimetria_os"):
        if field in eo:
            st.session_state[field] = eo.get(field) or ""

    # Correzione finale
    cf = pj.get("correzione_finale") or {}
    od = cf.get("od") or {}
    os_ = cf.get("os") or {}
    st.session_state["rx_fin_od_sf"]  = float(od.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_od_cyl"] = float(od.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_od_ax"]  = int(od.get("ax", 0) or 0)

    st.session_state["rx_fin_os_sf"]  = float(os_.get("sf", 0.0) or 0.0)
    st.session_state["rx_fin_os_cyl"] = float(os_.get("cyl", 0.0) or 0.0)
    st.session_state["rx_fin_os_ax"]  = int(os_.get("ax", 0) or 0)

    st.session_state["add_fin"] = float(cf.get("add", 0.0) or 0.0)

    # Lenti consigliate
    pr = pj.get("prescrizione") or {}
    st.session_state["lenti_sel"] = pr.get("lenti") or []

APPLE_CSS = r"""
<style>
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1200px; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(0,0,0,.08); }
section[data-testid="stSidebar"] > div { padding-top: 1.0rem; }
h1, h2, h3 { letter-spacing: -0.01em; }
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] > div { border-radius: 14px !important; }
button { border-radius: 14px !important; }
details { border-radius: 18px; border: 1px solid rgba(0,0,0,.08); padding: 6px 10px; }
details > summary { font-weight: 600; }
.to-topbar {
  display:flex; justify-content: space-between; align-items:center;
  padding: 10px 12px; border-radius: 18px;
  border: 1px solid rgba(0,0,0,.08);
  background: rgba(255,255,255,.85);
  box-shadow: 0 6px 18px rgba(0,0,0,.05);
  margin-bottom: 12px;
}
.to-topbar .title { font-weight: 700; font-size: 1.05rem; letter-spacing: -0.01em; }
.to-topbar .sub { color: rgba(0,0,0,.55); font-size: 0.9rem; }
</style>
"""

from vision_manager.db import get_conn, init_db
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"

ACUITA_VALUES = [
    "N.V. (Occhio non vedente)",
    "P.L. (Percezione luce)",
    "M.M. (Movimento mano)",
    "C.F. (Conta dita)",
    "1/50","1/20","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10",
    "12/10","14/10","16/10"
]

LENTI_OPTIONS = [
    "Progressive",
    "Per vicino/intermedio",
    "Monofocali lontano",
    "Monofocali intermedio",
    "Monofocali vicino",
    "Fotocromatiche",
    "Polarizzate",
    "Controllo miopia",
    "Trattamento antiriflesso",
    "Filtro luce blu",
]

# redeploy
