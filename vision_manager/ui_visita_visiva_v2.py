import json
import time
import datetime as dt
import os
import re
import tempfile
from datetime import date, datetime
import calendar
from io import BytesIO
from functools import lru_cache

import matplotlib.pyplot as plt
import streamlit as st
from streamlit.errors import StreamlitAPIException

# Se necessario, cambia questo import in:
# from .db import get_conn
from vision_manager.db import get_conn
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"

PROFESSIONALS_DEFAULT = [
    {
        "label": "Dr. Giuseppe Ferraioli",
        "lines": ["Dr. Giuseppe Ferraioli", "Neuropsicologo Optometrista"],
    },
    {
        "label": "Dott. Salvatore Adriano Cirillo",
        "lines": ["Dott. Salvatore Adriano Cirillo", "Medico Chirurgo", "Oculista"],
    },
]


def _sanitize_filename_part(value):
    txt = str(value or "").strip().lower()
    txt = re.sub(r"[^a-z0-9]+", "_", txt)
    return txt.strip("_") or "professionista"


def _normalize_professional_lines(lines):
    cleaned = []
    for line in lines or []:
        s = str(line or "").strip()
        if s:
            cleaned.append(s)
    return cleaned[:3]


def _ensure_professionals_state():
    professionals = st.session_state.get("vm_professionals")
    if not isinstance(professionals, list) or not professionals:
        professionals = [dict(item) for item in PROFESSIONALS_DEFAULT]
        st.session_state["vm_professionals"] = professionals

    normalized = []
    seen = set()
    for item in professionals:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        lines = _normalize_professional_lines(item.get("lines") or [])
        if not label and lines:
            label = lines[0]
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        normalized.append({"label": label, "lines": lines or [label]})

    if not normalized:
        normalized = [dict(item) for item in PROFESSIONALS_DEFAULT]

    st.session_state["vm_professionals"] = normalized

    active = st.session_state.get("vm_active_professional")
    labels = [item["label"] for item in normalized]
    if active not in labels:
        st.session_state["vm_active_professional"] = normalized[0]["label"]


def _get_active_professional():
    _ensure_professionals_state()
    active_label = st.session_state.get("vm_active_professional")
    for item in st.session_state.get("vm_professionals", []):
        if item.get("label") == active_label:
            return item
    return st.session_state.get("vm_professionals", [PROFESSIONALS_DEFAULT[0]])[0]


def _cover_cirillo_area(img):
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([(25, 30), (455, 205)], fill="white")
    return img


@lru_cache(maxsize=16)
def _professional_letterhead_path(professional_key, include_professional=True):
    path = os.path.join(tempfile.gettempdir(), f"vision_manager_letterhead_v4_{professional_key}_{int(include_professional)}.jpg")
    if os.path.exists(path):
        return path
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.open(LETTERHEAD).convert("RGB")
        img = _cover_cirillo_area(img)
        if include_professional:
            active = _get_active_professional()
            lines = _normalize_professional_lines(active.get("lines") or [])
            if lines:
                draw = ImageDraw.Draw(img)
                try:
                    font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
                    font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
                    font_sub2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
                except Exception:
                    font_main = ImageFont.load_default()
                    font_sub = ImageFont.load_default()
                    font_sub2 = ImageFont.load_default()
                x = 52
                y = 42
                for idx, line in enumerate(lines[:3]):
                    font = font_main if idx == 0 else (font_sub if idx == 1 else font_sub2)
                    draw.text((x, y), line, fill="black", font=font)
                    y += 60 if idx == 0 else 42
        img.save(path, format="JPEG", quality=95)
        return path
    except Exception:
        return LETTERHEAD


def _get_letterhead_path(include_professional=True):
    _ensure_professionals_state()
    active = _get_active_professional()
    key = _sanitize_filename_part(active.get("label"))
    return _professional_letterhead_path(key, include_professional)


# =========================================================
# HELPERS GENERICI
# =========================================================

def _parse_date_safe(value):
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return date.today()


def _render_dmy_input(label, key_prefix, default_date=None):
    dflt = _parse_date_safe(default_date) if default_date else date.today()

    day_key = f"{key_prefix}_day"
    month_key = f"{key_prefix}_month"
    year_key = f"{key_prefix}_year"

    st.session_state.setdefault(day_key, dflt.day)
    st.session_state.setdefault(month_key, dflt.month)
    st.session_state.setdefault(year_key, dflt.year)

    st.markdown(label)
    c1, c2, c3 = st.columns([1, 1, 1.2])
    month_names = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]

    year_selected = c3.selectbox(
        "Anno",
        list(range(date.today().year, 1899, -1)),
        index=max(0, min(date.today().year - st.session_state[year_key], date.today().year - 1900)),
        key=year_key,
    )
    month_selected = c2.selectbox(
        "Mese",
        list(range(1, 13)),
        format_func=lambda m: month_names[m - 1],
        index=max(0, min(11, st.session_state[month_key] - 1)),
        key=month_key,
    )
    max_day = calendar.monthrange(int(year_selected), int(month_selected))[1]
    current_day = int(st.session_state.get(day_key, dflt.day) or dflt.day)
    if current_day > max_day:
        current_day = max_day
        st.session_state[day_key] = max_day
    day_selected = c1.selectbox(
        "Giorno",
        list(range(1, max_day + 1)),
        index=max(0, min(max_day - 1, current_day - 1)),
        key=day_key,
    )

    return date(int(year_selected), int(month_selected), int(day_selected))


def _calculate_age(birth_date, reference_date=None):
    if not birth_date:
        return None
    try:
        b = _parse_date_safe(birth_date) if not isinstance(birth_date, date) else birth_date
        ref = reference_date or date.today()
        years = ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))
        return years if years >= 0 else None
    except Exception:
        return None


def _age_label(birth_date, prefix="Età"):
    years = _calculate_age(birth_date)
    if years is None:
        return ""
    return f"{prefix}: {years} anni"


def _safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return default if value is None else int(float(value))
    except Exception:
        return default


def _row_get(row, key, index=None, default=None):
    """
    Supporta sia righe tuple/list sia dict/RealDictRow.
    """
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if index is not None:
            return row[index]
    except Exception:
        pass
    return default


def _fmt_value(value, fallback="-"):
    if value is None:
        return fallback
    if isinstance(value, str):
        value = value.strip()
        return value if value else fallback
    return str(value)


def _fmt_rx_block(rx_dict):
    if not isinstance(rx_dict, dict):
        return "-"
    sf = _fmt_value(rx_dict.get("sf"))
    cyl = _fmt_value(rx_dict.get("cyl"))
    ax = _fmt_value(rx_dict.get("ax"))
    return f"SF {sf}   CIL {cyl}   AX {ax}"


def _calc_iop_adjusted(iop, cct, ref_cct=540.0):
    if iop is None or cct is None:
        return None
    delta = (ref_cct - cct) / 10.0 * 0.7
    return float(iop + delta)


def _clinical_attention(iop_od, iop_os, cct_od, cct_os):
    out = {
        "od": {"flag": False, "reason": "", "adj": None},
        "os": {"flag": False, "reason": "", "adj": None},
    }

    for eye in ("od", "os"):
        iop = iop_od if eye == "od" else iop_os
        cct = cct_od if eye == "od" else cct_os
        adj = _calc_iop_adjusted(iop, cct)

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
            reasons.append(f"IOP stimata da CCT ≈ {adj:.1f} mmHg")

        out[eye]["flag"] = flag
        out[eye]["reason"] = "; ".join(reasons)
        out[eye]["adj"] = adj

    return out


# =========================================================
# SESSION STATE
# =========================================================

def ensure_visit_state():
    _ensure_professionals_state()
    defaults = {
        "vm_tipo_visita": "oculistica",
        "vm_data_visita": date.today(),
        "vm_anamnesi": "",
        "vm_acuita_naturale_od": "",
        "vm_acuita_naturale_os": "",
        "vm_acuita_corretta_od": "",
        "vm_acuita_corretta_os": "",
        "vm_congiuntiva": "",
        "vm_cornea": "",
        "vm_camera_anteriore": "",
        "vm_cristallino": "",
        "vm_vitreo": "",
        "vm_fondo_oculare": "",
        "vm_iop_od": "",
        "vm_iop_os": "",
        "vm_pachimetria_od": "",
        "vm_pachimetria_os": "",
        "vm_ca_od_sf": 0.0,
        "vm_ca_od_cyl": 0.0,
        "vm_ca_od_ax": 0,
        "vm_ca_os_sf": 0.0,
        "vm_ca_os_cyl": 0.0,
        "vm_ca_os_ax": 0,
        "vm_cf_od_sf": 0.0,
        "vm_cf_od_cyl": 0.0,
        "vm_cf_od_ax": 0,
        "vm_cf_os_sf": 0.0,
        "vm_cf_os_cyl": 0.0,
        "vm_cf_os_ax": 0,
        "vm_enable_add_vicino": True,
        "vm_enable_add_intermedio": False,
        "vm_add_vicino": 0.0,
        "vm_add_intermedio": 0.0,
        "vm_note": "",
        "vm_pending_load": None,
        "vm_loaded_visit_id": None,
        "vm_delete_confirm": None,
        "vm_mode": "new",
        "vm_current_patient_id": None,
        "vm_form_dirty": False,
        "vm_pending_action": None,
        "vm_selected_paziente_label": None,
        "vm_history_selected_visit_id": None,
        "vm_autosave_enabled": True,
        "vm_autosave_status": None,
        "vm_last_autosave_at": None,
        "vm_last_saved_hash": None,
        "vm_last_autosave_reason": None,
        "vm_flash_message": None,
        "vm_pending_form_reset": False,
        "vm_include_professional_referto": False,
        "vm_include_professional_prescrizione": False,
        "vm_professionals": [dict(item) for item in PROFESSIONALS_DEFAULT],
        "vm_active_professional": "Dr. Giuseppe Ferraioli",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _apply_form_reset_values():
    st.session_state["vm_tipo_visita"] = "oculistica"
    st.session_state["vm_data_visita"] = date.today()
    st.session_state["vm_anamnesi"] = ""
    st.session_state["vm_acuita_naturale_od"] = ""
    st.session_state["vm_acuita_naturale_os"] = ""
    st.session_state["vm_acuita_corretta_od"] = ""
    st.session_state["vm_acuita_corretta_os"] = ""
    st.session_state["vm_congiuntiva"] = ""
    st.session_state["vm_cornea"] = ""
    st.session_state["vm_camera_anteriore"] = ""
    st.session_state["vm_cristallino"] = ""
    st.session_state["vm_vitreo"] = ""
    st.session_state["vm_fondo_oculare"] = ""
    st.session_state["vm_iop_od"] = ""
    st.session_state["vm_iop_os"] = ""
    st.session_state["vm_pachimetria_od"] = ""
    st.session_state["vm_pachimetria_os"] = ""
    st.session_state["vm_ca_od_sf"] = 0.0
    st.session_state["vm_ca_od_cyl"] = 0.0
    st.session_state["vm_ca_od_ax"] = 0
    st.session_state["vm_ca_os_sf"] = 0.0
    st.session_state["vm_ca_os_cyl"] = 0.0
    st.session_state["vm_ca_os_ax"] = 0
    st.session_state["vm_cf_od_sf"] = 0.0
    st.session_state["vm_cf_od_cyl"] = 0.0
    st.session_state["vm_cf_od_ax"] = 0
    st.session_state["vm_cf_os_sf"] = 0.0
    st.session_state["vm_cf_os_cyl"] = 0.0
    st.session_state["vm_cf_os_ax"] = 0
    st.session_state["vm_enable_add_vicino"] = True
    st.session_state["vm_enable_add_intermedio"] = False
    st.session_state["vm_add_vicino"] = 0.0
    st.session_state["vm_add_intermedio"] = 0.0
    st.session_state["vm_note"] = ""
    st.session_state["vm_loaded_visit_id"] = None
    st.session_state["vm_mode"] = "new"
    _set_saved_state(build_visit_payload(), reason="nuova visita")


def clear_visit_form():
    try:
        _apply_form_reset_values()
        st.session_state["vm_pending_form_reset"] = False
    except StreamlitAPIException:
        st.session_state["vm_pending_form_reset"] = True
        st.session_state["vm_loaded_visit_id"] = None
        st.session_state["vm_mode"] = "new"
        st.session_state["vm_form_dirty"] = False


def mark_visit_dirty():
    st.session_state["vm_form_dirty"] = True


def _normalize_add_target(value):
    s = str(value or "vicino").strip().lower()
    if s in ("intermedio", "computer", "pc"):
        return "intermedio"
    return "vicino"


def _compute_additions(add_vicino=None, add_intermedio=None, enable_vicino=True, enable_intermedio=False):
    add_vicino = _safe_float(add_vicino, 0.0)
    add_intermedio = _safe_float(add_intermedio, 0.0)
    return {
        "vicino": round(add_vicino if enable_vicino else 0.0, 2),
        "intermedio": round(add_intermedio if enable_intermedio else 0.0, 2),
        "enable_vicino": bool(enable_vicino),
        "enable_intermedio": bool(enable_intermedio),
    }


# =========================================================
# PAYLOAD
# =========================================================

def build_visit_payload():
    return {
        "tipo_visita": st.session_state.get("vm_tipo_visita", "oculistica"),
        "data": str(st.session_state.get("vm_data_visita", date.today())),
        "anamnesi": st.session_state.get("vm_anamnesi", ""),
        "acuita": {
            "naturale": {
                "od": st.session_state.get("vm_acuita_naturale_od", ""),
                "os": st.session_state.get("vm_acuita_naturale_os", ""),
            },
            "corretta": {
                "od": st.session_state.get("vm_acuita_corretta_od", ""),
                "os": st.session_state.get("vm_acuita_corretta_os", ""),
            },
        },
        "esame_obiettivo": {
            "congiuntiva": st.session_state.get("vm_congiuntiva", ""),
            "cornea": st.session_state.get("vm_cornea", ""),
            "camera_anteriore": st.session_state.get("vm_camera_anteriore", ""),
            "cristallino": st.session_state.get("vm_cristallino", ""),
            "vitreo": st.session_state.get("vm_vitreo", ""),
            "fondo_oculare": st.session_state.get("vm_fondo_oculare", ""),
            "pressione_endoculare_od": st.session_state.get("vm_iop_od", ""),
            "pressione_endoculare_os": st.session_state.get("vm_iop_os", ""),
            "pachimetria_od": st.session_state.get("vm_pachimetria_od", ""),
            "pachimetria_os": st.session_state.get("vm_pachimetria_os", ""),
        },
        "correzione_abituale": {
            "od": {
                "sf": st.session_state.get("vm_ca_od_sf", 0.0),
                "cyl": st.session_state.get("vm_ca_od_cyl", 0.0),
                "ax": st.session_state.get("vm_ca_od_ax", 0),
            },
            "os": {
                "sf": st.session_state.get("vm_ca_os_sf", 0.0),
                "cyl": st.session_state.get("vm_ca_os_cyl", 0.0),
                "ax": st.session_state.get("vm_ca_os_ax", 0),
            },
        },
        "correzione_finale": {
            "od": {
                "sf": st.session_state.get("vm_cf_od_sf", 0.0),
                "cyl": st.session_state.get("vm_cf_od_cyl", 0.0),
                "ax": st.session_state.get("vm_cf_od_ax", 0),
            },
            "os": {
                "sf": st.session_state.get("vm_cf_os_sf", 0.0),
                "cyl": st.session_state.get("vm_cf_os_cyl", 0.0),
                "ax": st.session_state.get("vm_cf_os_ax", 0),
            },
            "add_vicino": _safe_float(st.session_state.get("vm_add_vicino", 0.0), 0.0),
            "add_intermedio": _safe_float(st.session_state.get("vm_add_intermedio", 0.0), 0.0),
            "enable_add_vicino": bool(st.session_state.get("vm_enable_add_vicino", True)),
            "enable_add_intermedio": bool(st.session_state.get("vm_enable_add_intermedio", False)),
        },
        "note": st.session_state.get("vm_note", ""),
    }


def _payload_signature(payload):
    try:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        return str(payload)


def _set_saved_state(payload, reason=None):
    st.session_state["vm_form_dirty"] = False
    st.session_state["vm_last_saved_hash"] = _payload_signature(payload)
    st.session_state["vm_last_autosave_at"] = time.time()
    st.session_state["vm_last_autosave_reason"] = reason


def _autosave_caption():
    ts = st.session_state.get("vm_last_autosave_at")
    if not ts:
        return None
    when = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
    reason = st.session_state.get("vm_last_autosave_reason")
    if reason:
        return f"Autosalvataggio: {when} · {reason}"
    return f"Autosalvataggio: {when}"


def maybe_autosave_current_visit(conn, paziente_id, reason="automatico"):
    if not st.session_state.get("vm_autosave_enabled"):
        return False, None, None
    if not paziente_id or not st.session_state.get("vm_form_dirty"):
        return False, None, None

    payload = build_visit_payload()
    payload_sig = _payload_signature(payload)
    if payload_sig == st.session_state.get("vm_last_saved_hash"):
        st.session_state["vm_form_dirty"] = False
        return False, st.session_state.get("vm_loaded_visit_id"), "nessuna modifica"

    visit_id, action = persist_current_visit(conn, paziente_id, payload=payload, reason=reason)
    st.session_state["vm_autosave_status"] = ("success", f"Autosalvataggio {action}. ID: {visit_id}.")
    return True, visit_id, action


def load_visit_payload(payload, visit_id=None):
    acuita = payload.get("acuita", {}) or {}
    naturale = acuita.get("naturale", {}) or {}
    corretta = acuita.get("corretta", {}) or {}

    esame = payload.get("esame_obiettivo", {}) or {}

    corr_ab = payload.get("correzione_abituale", {}) or {}
    corr_ab_od = corr_ab.get("od", {}) or {}
    corr_ab_os = corr_ab.get("os", {}) or {}

    corr_fin = payload.get("correzione_finale", {}) or {}
    corr_fin_od = corr_fin.get("od", {}) or {}
    corr_fin_os = corr_fin.get("os", {}) or {}

    st.session_state["vm_tipo_visita"] = payload.get("tipo_visita", "oculistica")
    st.session_state["vm_data_visita"] = _parse_date_safe(payload.get("data"))
    st.session_state["vm_anamnesi"] = payload.get("anamnesi", "")
    st.session_state["vm_acuita_naturale_od"] = naturale.get("od", "")
    st.session_state["vm_acuita_naturale_os"] = naturale.get("os", "")
    st.session_state["vm_acuita_corretta_od"] = corretta.get("od", "")
    st.session_state["vm_acuita_corretta_os"] = corretta.get("os", "")
    st.session_state["vm_congiuntiva"] = esame.get("congiuntiva", "")
    st.session_state["vm_cornea"] = esame.get("cornea", "")
    st.session_state["vm_camera_anteriore"] = esame.get("camera_anteriore", "")
    st.session_state["vm_cristallino"] = esame.get("cristallino", "")
    st.session_state["vm_vitreo"] = esame.get("vitreo", "")
    st.session_state["vm_fondo_oculare"] = esame.get("fondo_oculare", "")
    st.session_state["vm_iop_od"] = esame.get("pressione_endoculare_od", "")
    st.session_state["vm_iop_os"] = esame.get("pressione_endoculare_os", "")
    st.session_state["vm_pachimetria_od"] = esame.get("pachimetria_od", "")
    st.session_state["vm_pachimetria_os"] = esame.get("pachimetria_os", "")
    st.session_state["vm_ca_od_sf"] = _safe_float(corr_ab_od.get("sf", 0.0))
    st.session_state["vm_ca_od_cyl"] = _safe_float(corr_ab_od.get("cyl", 0.0))
    st.session_state["vm_ca_od_ax"] = _safe_int(corr_ab_od.get("ax", 0))
    st.session_state["vm_ca_os_sf"] = _safe_float(corr_ab_os.get("sf", 0.0))
    st.session_state["vm_ca_os_cyl"] = _safe_float(corr_ab_os.get("cyl", 0.0))
    st.session_state["vm_ca_os_ax"] = _safe_int(corr_ab_os.get("ax", 0))
    st.session_state["vm_cf_od_sf"] = _safe_float(corr_fin_od.get("sf", 0.0))
    st.session_state["vm_cf_od_cyl"] = _safe_float(corr_fin_od.get("cyl", 0.0))
    st.session_state["vm_cf_od_ax"] = _safe_int(corr_fin_od.get("ax", 0))
    st.session_state["vm_cf_os_sf"] = _safe_float(corr_fin_os.get("sf", 0.0))
    st.session_state["vm_cf_os_cyl"] = _safe_float(corr_fin_os.get("cyl", 0.0))
    st.session_state["vm_cf_os_ax"] = _safe_int(corr_fin_os.get("ax", 0))
    if any(k in corr_fin for k in ("add_vicino", "add_intermedio", "enable_add_vicino", "enable_add_intermedio")):
        st.session_state["vm_add_vicino"] = _safe_float(corr_fin.get("add_vicino", 0.0), 0.0)
        st.session_state["vm_add_intermedio"] = _safe_float(corr_fin.get("add_intermedio", 0.0), 0.0)
        st.session_state["vm_enable_add_vicino"] = bool(corr_fin.get("enable_add_vicino", st.session_state.get("vm_add_vicino", 0.0) != 0.0))
        st.session_state["vm_enable_add_intermedio"] = bool(corr_fin.get("enable_add_intermedio", st.session_state.get("vm_add_intermedio", 0.0) != 0.0))
    else:
        legacy_add = _safe_float(corr_fin.get("add", 0.0), 0.0)
        legacy_target = _normalize_add_target(corr_fin.get("add_target", "vicino"))
        if legacy_target == "intermedio":
            st.session_state["vm_add_intermedio"] = legacy_add
            st.session_state["vm_add_vicino"] = round(legacy_add * 2.0, 2)
        else:
            st.session_state["vm_add_vicino"] = legacy_add
            st.session_state["vm_add_intermedio"] = round(legacy_add / 2.0, 2) if legacy_add else 0.0
        st.session_state["vm_enable_add_vicino"] = st.session_state["vm_add_vicino"] != 0.0
        st.session_state["vm_enable_add_intermedio"] = st.session_state["vm_add_intermedio"] != 0.0
    st.session_state["vm_note"] = payload.get("note", "")
    st.session_state["vm_loaded_visit_id"] = visit_id
    st.session_state["vm_mode"] = "edit" if visit_id else "new"
    _set_saved_state(build_visit_payload(), reason="caricamento visita")


def apply_pending_visit_load():
    pending = st.session_state.pop("vm_pending_load", None)
    if not pending:
        return

    raw = pending.get("dati_json")
    visit_id = pending.get("visit_id")

    if not raw:
        return

    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
        load_visit_payload(payload, visit_id=visit_id)
    except Exception as e:
        st.error(f"Errore nel caricamento della visita: {e}")


# =========================================================
# PDF / EXPORT
# =========================================================

def _build_referto_letterhead_pdf(payload, patient_label="Paziente", visit_id=None, include_professional=False):
    data_pdf = {
        "data": str(payload.get("data", "")),
        "paziente": patient_label,
        "anamnesi": payload.get("anamnesi", ""),
        "acuita": payload.get("acuita", {}) or {},
        "esame_obiettivo": payload.get("esame_obiettivo", {}) or {},
        "note": payload.get("note", ""),
    }
    return build_referto_oculistico_a4(data_pdf, _get_letterhead_path(include_professional))


def _rx_add(rx, add_value):
    rx = rx or {}
    try:
        add_num = float(add_value or 0.0)
    except Exception:
        add_num = 0.0
    return {
        "sf": _safe_float(rx.get("sf", 0.0)) + add_num,
        "cyl": _safe_float(rx.get("cyl", 0.0)),
        "ax": _safe_int(rx.get("ax", 0)),
    }


def _build_prescrizione_letterhead_pdf(payload, patient_label="Paziente", include_professional=False):
    corr_fin = payload.get("correzione_finale", {}) or {}
    od = corr_fin.get("od", {}) or {}
    os_ = corr_fin.get("os", {}) or {}
    add_data = _compute_additions(
        corr_fin.get("add_vicino", corr_fin.get("add", 0.0)),
        corr_fin.get("add_intermedio", 0.0),
        corr_fin.get("enable_add_vicino", True),
        corr_fin.get("enable_add_intermedio", False),
    )

    rx_blank = {"sf": None, "cyl": None, "ax": None}

    data_pdf = {
        "data": str(payload.get("data", "")),
        "paziente": patient_label,
        "lontano": {
            "od": {
                "sf": _safe_float(od.get("sf", 0.0)),
                "cyl": _safe_float(od.get("cyl", 0.0)),
                "ax": _safe_int(od.get("ax", 0)),
            },
            "os": {
                "sf": _safe_float(os_.get("sf", 0.0)),
                "cyl": _safe_float(os_.get("cyl", 0.0)),
                "ax": _safe_int(os_.get("ax", 0)),
            },
        },
        "intermedio": {
            "od": _rx_add(od, add_data["intermedio"]) if add_data["enable_intermedio"] and add_data["intermedio"] else dict(rx_blank),
            "os": _rx_add(os_, add_data["intermedio"]) if add_data["enable_intermedio"] and add_data["intermedio"] else dict(rx_blank),
        },
        "vicino": {
            "od": _rx_add(od, add_data["vicino"]) if add_data["enable_vicino"] and add_data["vicino"] else dict(rx_blank),
            "os": _rx_add(os_, add_data["vicino"]) if add_data["enable_vicino"] and add_data["vicino"] else dict(rx_blank),
        },
        "lenti": [],
        "add": add_data["vicino"] if add_data["enable_vicino"] else 0.0,
        "add_od": add_data["vicino"] if add_data["enable_vicino"] else 0.0,
        "add_os": add_data["vicino"] if add_data["enable_vicino"] else 0.0,
    }
    return build_prescrizione_occhiali_a4(data_pdf, _get_letterhead_path(include_professional))


# =========================================================
# DB
# =========================================================

def _is_pg(conn):
    return conn.__class__.__module__.startswith("psycopg2")


def _ph(conn):
    return "%s" if _is_pg(conn) else "?"


def insert_paziente(conn, nome, cognome, data_nascita, note=""):
    nome = (nome or "").strip()
    cognome = (cognome or "").strip()
    note = (note or "").strip()
    data_nascita = (data_nascita or "").strip()

    if not cognome:
        raise ValueError("Cognome obbligatorio")
    if not nome:
        raise ValueError("Nome obbligatorio")
    if not data_nascita:
        raise ValueError("Data nascita obbligatoria")

    ph = _ph(conn)
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            has_note = False
            try:
                cur.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='pazienti' AND column_name='note'
                    LIMIT 1
                    """
                )
                has_note = cur.fetchone() is not None
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                has_note = False

            if has_note:
                cur.execute(
                    f"""
                    INSERT INTO pazienti
                    (cognome, nome, data_nascita, note, stato_paziente)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                    RETURNING id
                    """,
                    (cognome, nome, data_nascita, note, "ATTIVO"),
                )
            else:
                cur.execute(
                    f"""
                    INSERT INTO pazienti
                    (cognome, nome, data_nascita, stato_paziente)
                    VALUES ({ph}, {ph}, {ph}, {ph})
                    RETURNING id
                    """,
                    (cognome, nome, data_nascita, "ATTIVO"),
                )

            row = cur.fetchone()
            new_id = _row_get(row, "id", 0, None)
        else:
            cur.execute(
                f"""
                INSERT INTO Pazienti
                (Cognome, Nome, Data_Nascita, Note)
                VALUES ({ph}, {ph}, {ph}, {ph})
                """,
                (cognome, nome, data_nascita, note),
            )
            new_id = getattr(cur, "lastrowid", None)

        conn.commit()
        return new_id
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def update_paziente(conn, paziente_id, nome, cognome, data_nascita, note=""):
    nome = (nome or "").strip()
    cognome = (cognome or "").strip()
    note = (note or "").strip()
    data_nascita = (data_nascita or "").strip()

    if not paziente_id:
        raise ValueError("Paziente non valido")
    if not cognome:
        raise ValueError("Cognome obbligatorio")
    if not nome:
        raise ValueError("Nome obbligatorio")
    if not data_nascita:
        raise ValueError("Data nascita obbligatoria")

    ph = _ph(conn)
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            has_note = False
            try:
                cur.execute(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name='pazienti' AND column_name='note'
                    LIMIT 1
                    """
                )
                has_note = cur.fetchone() is not None
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                has_note = False

            if has_note:
                cur.execute(
                    f"""
                    UPDATE pazienti
                    SET cognome = {ph},
                        nome = {ph},
                        data_nascita = {ph},
                        note = {ph}
                    WHERE id = {ph}
                    """,
                    (cognome, nome, data_nascita, note, paziente_id),
                )
            else:
                cur.execute(
                    f"""
                    UPDATE pazienti
                    SET cognome = {ph},
                        nome = {ph},
                        data_nascita = {ph}
                    WHERE id = {ph}
                    """,
                    (cognome, nome, data_nascita, paziente_id),
                )
        else:
            cur.execute(
                f"""
                UPDATE Pazienti
                SET Cognome = {ph},
                    Nome = {ph},
                    Data_Nascita = {ph},
                    Note = {ph}
                WHERE ID = {ph}
                """,
                (cognome, nome, data_nascita, note, paziente_id),
            )

        conn.commit()
        return paziente_id
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def list_pazienti(conn):
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                """
                SELECT id, cognome, nome, data_nascita
                FROM pazienti
                ORDER BY cognome, nome
                """
            )
        else:
            cur.execute(
                """
                SELECT ID AS id, Cognome AS cognome, Nome AS nome, Data_Nascita AS data_nascita
                FROM Pazienti
                ORDER BY Cognome, Nome
                """
            )
        return cur.fetchall()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def list_visite(conn, paziente_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, data_visita, dati_json
            FROM visite_visive
            WHERE paziente_id = %s
              AND COALESCE(is_deleted, 0) = 0
            ORDER BY data_visita DESC, id DESC
            """,
            (paziente_id,),
        )
        return cur.fetchall()


def save_new_visit(conn, paziente_id):
    payload = build_visit_payload()
    data_visita = st.session_state.get("vm_data_visita", date.today())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO visite_visive (paziente_id, data_visita, dati_json)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (paziente_id, data_visita, json.dumps(payload)),
        )
        row = cur.fetchone()
        new_id = _row_get(row, "id", 0, None) if row is not None else None

    conn.commit()
    return new_id


def update_existing_visit(conn, visit_id, paziente_id):
    payload = build_visit_payload()
    data_visita = st.session_state.get("vm_data_visita", date.today())

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE visite_visive
            SET paziente_id = %s,
                data_visita = %s,
                dati_json = %s
            WHERE id = %s
            """,
            (paziente_id, data_visita, json.dumps(payload), visit_id),
        )

    conn.commit()
    return visit_id


def delete_visit(conn, visit_id):
    """
    Soft delete della visita: la visita non viene eliminata dal database,
    ma viene nascosta dallo storico impostando is_deleted e deleted_at.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE visite_visive
            SET is_deleted = 1,
                deleted_at = NOW()
            WHERE id = %s
            """,
            (visit_id,),
        )

    conn.commit()
    return visit_id




def _label_for_patient_id(pazienti_map, paziente_id):
    for label, pid in pazienti_map.items():
        try:
            if int(pid) == int(paziente_id):
                return label
        except Exception:
            if pid == paziente_id:
                return label
    return None


def persist_current_visit(conn, paziente_id, payload=None, reason=None):
    payload = payload or build_visit_payload()
    if st.session_state.get("vm_mode") == "edit" and st.session_state.get("vm_loaded_visit_id"):
        visit_id = update_existing_visit(conn, st.session_state["vm_loaded_visit_id"], paziente_id)
        action = "aggiornata"
    else:
        visit_id = save_new_visit(conn, paziente_id)
        st.session_state["vm_loaded_visit_id"] = visit_id
        st.session_state["vm_mode"] = "edit"
        action = "salvata"

    _set_saved_state(payload, reason=reason)
    return visit_id, action


def perform_pending_action(conn, action, current_paziente_id, pazienti_map):
    if not action:
        return

    action_type = action.get("type")

    if action_type == "switch_patient":
        target_pid = action.get("target_patient_id")
        target_label = action.get("target_patient_label") or _label_for_patient_id(pazienti_map, target_pid)
        clear_visit_form()
        st.session_state["vm_current_patient_id"] = target_pid
        st.session_state["vision_last_pid"] = target_pid
        if target_label:
            st.session_state["vm_selected_paziente_label"] = target_label

    elif action_type == "new_visit":
        clear_visit_form()

    elif action_type == "load_latest":
        ultime_visite = list_visite(conn, current_paziente_id)
        if ultime_visite:
            row_last = ultime_visite[0]
            st.session_state["vm_pending_load"] = {
                "visit_id": _row_get(row_last, "id", 0),
                "dati_json": _row_get(row_last, "dati_json", 2),
            }
            apply_pending_visit_load()
        else:
            clear_visit_form()
            st.session_state["vm_flash_message"] = ("info", "Nessuna visita salvata per questo paziente.")

    elif action_type == "load_specific_visit":
        st.session_state["vm_pending_load"] = {
            "visit_id": action.get("visit_id"),
            "dati_json": action.get("dati_json"),
        }
        apply_pending_visit_load()

    st.session_state["vm_pending_action"] = None

# =========================================================
# UI
# =========================================================

def ui_visita_visiva_v2(conn):
    ensure_visit_state()
    if st.session_state.get("vm_pending_form_reset"):
        _apply_form_reset_values()
        st.session_state["vm_pending_form_reset"] = False
    apply_pending_visit_load()

    st.title("© Vision Manager The Organism by Dr. Ferraioli Giuseppe")

    flash_message = st.session_state.pop("vm_flash_message", None)
    if flash_message:
        level, message = flash_message
        getattr(st, level, st.info)(message)

    autosave_status = st.session_state.pop("vm_autosave_status", None)
    if autosave_status:
        level, message = autosave_status
        getattr(st, level, st.info)(message)

    with st.expander("➕ Nuovo paziente", expanded=False):
        np1, np2, np3 = st.columns(3)
        nome_nuovo = np1.text_input("Nome nuovo paziente", key="vm_new_nome")
        cognome_nuovo = np2.text_input("Cognome nuovo paziente", key="vm_new_cognome")
        with np3:
            data_nascita_new = _render_dmy_input(
                "Data nascita nuovo paziente",
                "vm_new_data_nascita",
                st.session_state.get("vm_new_data_nascita_default", date(2010, 1, 1)),
            )
        eta_nuovo = _calculate_age(data_nascita_new)
        if eta_nuovo is not None:
            st.caption(f"Età automatica: {eta_nuovo} anni")
        note_nuovo = st.text_area("Note anagrafiche", key="vm_new_note", height=80)

        if st.button("Salva nuovo paziente", key="vm_save_new_patient"):
            try:
                pid = insert_paziente(
                    conn,
                    nome_nuovo,
                    cognome_nuovo,
                    data_nascita_new.isoformat() if data_nascita_new else "",
                    note_nuovo,
                )
                st.session_state["vision_last_pid"] = int(pid) if pid is not None else None
                st.success(f"Paziente salvato correttamente. ID: {pid}")
                st.rerun()
            except ValueError as ve:
                st.error(str(ve))
            except Exception as e:
                st.error(f"Errore salvataggio nuovo paziente: {e}")

    pazienti = list_pazienti(conn)
    if not pazienti:
        st.warning("Nessun paziente presente. Inserisci prima un nuovo paziente.")
        return

    pazienti_options = []
    pazienti_map = {}

    for row in pazienti:
        pid = _row_get(row, "id", 0)
        cognome = _row_get(row, "cognome", 1, "")
        nome = _row_get(row, "nome", 2, "")
        data_nascita = _row_get(row, "data_nascita", 3, "")
        label = f"{cognome} {nome}".strip()
        if data_nascita:
            label = f"{label} ({str(data_nascita)[:10]})"
        pazienti_options.append(label)
        pazienti_map[label] = pid

    default_idx = 0
    last_pid = st.session_state.get("vision_last_pid")
    if last_pid is not None:
        for i, row in enumerate(pazienti):
            pid = _row_get(row, "id", 0)
            try:
                if int(pid) == int(last_pid):
                    default_idx = i
                    break
            except Exception:
                pass

    forced_label = st.session_state.pop("vm_force_selected_paziente_label", None)
    if forced_label in pazienti_map:
        st.session_state["vm_selected_paziente_label"] = forced_label
    elif not st.session_state.get("vm_selected_paziente_label") or st.session_state.get("vm_selected_paziente_label") not in pazienti_map:
        st.session_state["vm_selected_paziente_label"] = pazienti_options[default_idx]

    selected_paziente = st.selectbox("Seleziona paziente", pazienti_options, key="vm_selected_paziente_label")
    requested_paziente_id = pazienti_map[selected_paziente]

    if st.session_state.get("vm_current_patient_id") is None:
        st.session_state["vm_current_patient_id"] = requested_paziente_id
        st.session_state["vision_last_pid"] = requested_paziente_id

    current_paziente_id = st.session_state.get("vm_current_patient_id")
    current_label = _label_for_patient_id(pazienti_map, current_paziente_id) or selected_paziente

    if requested_paziente_id != current_paziente_id:
        if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
            maybe_autosave_current_visit(conn, current_paziente_id, reason="prima cambio paziente")
            clear_visit_form()
            st.session_state["vm_current_patient_id"] = requested_paziente_id
            st.session_state["vision_last_pid"] = requested_paziente_id
            current_paziente_id = requested_paziente_id
            current_label = selected_paziente
            st.session_state["vm_flash_message"] = ("success", "Bozza autosalvata prima del cambio paziente.")
            st.rerun()
        elif st.session_state.get("vm_form_dirty"):
            st.session_state["vm_pending_action"] = {
                "type": "switch_patient",
                "target_patient_id": requested_paziente_id,
                "target_patient_label": selected_paziente,
            }
            st.session_state["vm_force_selected_paziente_label"] = current_label
            st.rerun()
        else:
            clear_visit_form()
            st.session_state["vm_current_patient_id"] = requested_paziente_id
            st.session_state["vision_last_pid"] = requested_paziente_id
            current_paziente_id = requested_paziente_id
            current_label = selected_paziente

    paziente_id = current_paziente_id
    selected_paziente = current_label

    pending_action = st.session_state.get("vm_pending_action")
    if pending_action:
        target_desc = {
            "switch_patient": f"cambiare paziente in **{pending_action.get('target_patient_label', '')}**",
            "new_visit": "iniziare una nuova visita",
            "load_latest": "caricare l'ultima visita salvata",
            "load_specific_visit": f"caricare la visita ID **{pending_action.get('visit_id')}**",
        }.get(pending_action.get("type"), "proseguire")

        st.warning(f"Ci sono modifiche non salvate. Vuoi autosalvare prima di {target_desc}?")
        pa1, pa2, pa3 = st.columns(3)
        with pa1:
            if st.button("💾 Autosalva e continua", key="vm_pending_autosave", type="primary"):
                visit_id, action_label = persist_current_visit(conn, paziente_id, reason="prima di azione con modifiche non salvate")
                perform_pending_action(conn, pending_action, paziente_id, pazienti_map)
                st.session_state["vm_flash_message"] = ("success", f"Visita {action_label} automaticamente (ID: {visit_id}).")
                st.rerun()
        with pa2:
            if st.button("➡️ Continua senza salvare", key="vm_pending_discard"):
                perform_pending_action(conn, pending_action, paziente_id, pazienti_map)
                st.rerun()
        with pa3:
            if st.button("❌ Annulla", key="vm_pending_cancel"):
                st.session_state["vm_pending_action"] = None
                st.rerun()

    selected_row = None
    for row in pazienti:
        pid = _row_get(row, "id", 0)
        try:
            if int(pid) == int(paziente_id):
                selected_row = row
                break
        except Exception:
            if pid == paziente_id:
                selected_row = row
                break

    edit_nome_default = _row_get(selected_row, "nome", 2, "") if selected_row is not None else ""
    edit_cognome_default = _row_get(selected_row, "cognome", 1, "") if selected_row is not None else ""
    edit_dn_default = _parse_date_safe(_row_get(selected_row, "data_nascita", 3, None)) if selected_row is not None else date.today()

    selected_age = _calculate_age(edit_dn_default)
    if selected_age is not None:
        st.caption(f"Paziente selezionato: **{edit_cognome_default} {edit_nome_default}** • Età: **{selected_age} anni**")
    else:
        st.caption(f"Paziente selezionato: **{edit_cognome_default} {edit_nome_default}**")

    with st.expander("✏️ Modifica anagrafica paziente", expanded=False):
        ep1, ep2, ep3 = st.columns(3)
        nome_edit = ep1.text_input("Nome", value=edit_nome_default, key=f"vm_edit_nome_{paziente_id}")
        cognome_edit = ep2.text_input("Cognome", value=edit_cognome_default, key=f"vm_edit_cognome_{paziente_id}")
        with ep3:
            data_nascita_edit = _render_dmy_input(
                "Data nascita",
                f"vm_edit_data_nascita_{paziente_id}",
                edit_dn_default,
            )
        eta_edit = _calculate_age(data_nascita_edit)
        if eta_edit is not None:
            st.caption(f"Età automatica: {eta_edit} anni")
        note_edit = st.text_area(
            "Note anagrafiche",
            value="",
            key=f"vm_edit_note_{paziente_id}",
            height=80,
            help="La nota viene aggiornata se il database ha la colonna note.",
        )

        if st.button("Salva modifiche anagrafiche", key=f"vm_save_edit_patient_{paziente_id}"):
            try:
                update_paziente(
                    conn,
                    paziente_id,
                    nome_edit,
                    cognome_edit,
                    data_nascita_edit.isoformat() if data_nascita_edit else "",
                    note_edit,
                )
                st.session_state["vision_last_pid"] = int(paziente_id)
                st.success("Anagrafica paziente aggiornata correttamente.")
                st.rerun()
            except ValueError as ve:
                st.error(str(ve))
            except Exception as e:
                st.error(f"Errore aggiornamento anagrafica: {e}")

    top1, top2, top3, top4 = st.columns([1, 1, 2, 1.2])

    with top1:
        if st.button("🆕 Nuova visita"):
            if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
                maybe_autosave_current_visit(conn, paziente_id, reason="prima di nuova visita")
                clear_visit_form()
                st.session_state["vm_flash_message"] = ("success", "Bozza autosalvata prima di iniziare una nuova visita.")
                st.rerun()
            if st.session_state.get("vm_form_dirty"):
                st.session_state["vm_pending_action"] = {"type": "new_visit"}
                st.rerun()
            clear_visit_form()
            st.rerun()

    with top2:
        if st.button("📂 Carica ultima visita"):
            if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
                maybe_autosave_current_visit(conn, paziente_id, reason="prima di caricare ultima visita")
                perform_pending_action(conn, {"type": "load_latest"}, paziente_id, pazienti_map)
                st.session_state["vm_flash_message"] = ("success", "Bozza autosalvata prima di caricare l'ultima visita.")
                st.rerun()
            if st.session_state.get("vm_form_dirty"):
                st.session_state["vm_pending_action"] = {"type": "load_latest"}
                st.rerun()
            perform_pending_action(conn, {"type": "load_latest"}, paziente_id, pazienti_map)
            st.rerun()

    with top3:
        loaded_id = st.session_state.get("vm_loaded_visit_id")
        if st.session_state.get("vm_mode") == "edit" and loaded_id and st.session_state.get("vm_form_dirty"):
            st.warning(f"Visita ID {loaded_id} modificata e non ancora salvata")
        elif st.session_state.get("vm_mode") == "edit" and loaded_id:
            st.success(f"Visita caricata ID {loaded_id}")
        else:
            st.info("Nuova visita in compilazione")

    with top4:
        st.checkbox("Autosave avanzato", key="vm_autosave_enabled", help="Quando è attivo, le modifiche vengono autosalvate prima di cambiare paziente o caricare un'altra visita. Il salvataggio manuale resta comunque disponibile.")

    if selected_age is not None:
        st.info(f"Età paziente: {selected_age} anni")

    st.subheader("Dati visita")

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Tipo visita", ["oculistica"], key="vm_tipo_visita", on_change=mark_visit_dirty)
    with c2:
        st.date_input("Data visita", key="vm_data_visita", on_change=mark_visit_dirty)

    st.text_area("Anamnesi", key="vm_anamnesi", height=120, on_change=mark_visit_dirty)

    st.subheader("Acuita visiva")
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.text_input("AVN OD", key="vm_acuita_naturale_od", on_change=mark_visit_dirty)
    with a2:
        st.text_input("AVN OS", key="vm_acuita_naturale_os", on_change=mark_visit_dirty)
    with a3:
        st.text_input("AVC OD", key="vm_acuita_corretta_od", on_change=mark_visit_dirty)
    with a4:
        st.text_input("AVC OS", key="vm_acuita_corretta_os", on_change=mark_visit_dirty)

    st.subheader("Esame obiettivo")
    e1, e2 = st.columns(2)
    with e1:
        st.text_input("Congiuntiva", key="vm_congiuntiva", on_change=mark_visit_dirty)
        st.text_input("Cornea", key="vm_cornea", on_change=mark_visit_dirty)
        st.text_input("Camera anteriore", key="vm_camera_anteriore", on_change=mark_visit_dirty)
        st.text_input("Cristallino", key="vm_cristallino", on_change=mark_visit_dirty)
        st.text_input("Vitreo", key="vm_vitreo", on_change=mark_visit_dirty)
    with e2:
        st.text_input("Fondo oculare", key="vm_fondo_oculare", on_change=mark_visit_dirty)
        st.text_input("IOP OD", key="vm_iop_od", on_change=mark_visit_dirty)
        st.text_input("IOP OS", key="vm_iop_os", on_change=mark_visit_dirty)
        st.text_input("Pachimetria OD", key="vm_pachimetria_od", on_change=mark_visit_dirty)
        st.text_input("Pachimetria OS", key="vm_pachimetria_os", on_change=mark_visit_dirty)

    iop_od_now = _safe_float(st.session_state.get("vm_iop_od"), None)
    iop_os_now = _safe_float(st.session_state.get("vm_iop_os"), None)
    cct_od_now = _safe_float(st.session_state.get("vm_pachimetria_od"), None)
    cct_os_now = _safe_float(st.session_state.get("vm_pachimetria_os"), None)
    att = _clinical_attention(iop_od_now, iop_os_now, cct_od_now, cct_os_now)

    with st.expander("🔎 Rapporto IOP / Pachimetria", expanded=False):
        st.caption("Indicatore di attenzione clinica orientativo. Non sostituisce la valutazione specialistica.")
        r1, r2 = st.columns(2)

        with r1:
            st.write("**OD**")
            st.write(f"IOP inserita: **{_fmt_value(st.session_state.get('vm_iop_od'), '-')} mmHg**")
            st.write(f"Pachimetria: **{_fmt_value(st.session_state.get('vm_pachimetria_od'), '-')} µm**")
            if att["od"].get("adj") is not None:
                st.write(f"IOP stimata da CCT: **{att['od']['adj']:.1f} mmHg**")
            if att["od"]["flag"]:
                st.warning(att["od"]["reason"] or "Possibile attenzione clinica.")
            else:
                st.success("Nessun flag con i dati inseriti.")

        with r2:
            st.write("**OS**")
            st.write(f"IOP inserita: **{_fmt_value(st.session_state.get('vm_iop_os'), '-')} mmHg**")
            st.write(f"Pachimetria: **{_fmt_value(st.session_state.get('vm_pachimetria_os'), '-')} µm**")
            if att["os"].get("adj") is not None:
                st.write(f"IOP stimata da CCT: **{att['os']['adj']:.1f} mmHg**")
            if att["os"]["flag"]:
                st.warning(att["os"]["reason"] or "Possibile attenzione clinica.")
            else:
                st.success("Nessun flag con i dati inseriti.")

    st.subheader("Correzione abituale")
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        st.number_input("OD SF", key="vm_ca_od_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS SF", key="vm_ca_os_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with ca2:
        st.number_input("OD CIL", key="vm_ca_od_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS CIL", key="vm_ca_os_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with ca3:
        st.number_input("OD AX", key="vm_ca_od_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)
        st.number_input("OS AX", key="vm_ca_os_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)

    st.subheader("Correzione finale")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        st.number_input("OD SF finale", key="vm_cf_od_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS SF finale", key="vm_cf_os_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf2:
        st.number_input("OD CIL finale", key="vm_cf_od_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS CIL finale", key="vm_cf_os_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf3:
        st.number_input("OD AX finale", key="vm_cf_od_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)
        st.number_input("OS AX finale", key="vm_cf_os_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)

    st.subheader("Addizioni per prescrizione")
    st.caption("Seleziona una o entrambe le addizioni da riportare in prescrizione, partendo dalla refrazione finale.")
    add1, add2 = st.columns(2)
    with add1:
        st.checkbox("Aggiungi prescrizione per vicino", key="vm_enable_add_vicino", on_change=mark_visit_dirty)
        st.number_input(
            "ADD vicino",
            key="vm_add_vicino",
            step=0.25,
            format="%.2f",
            min_value=0.0,
            disabled=not st.session_state.get("vm_enable_add_vicino", True),
            on_change=mark_visit_dirty,
        )
    with add2:
        st.checkbox("Aggiungi prescrizione per intermedio", key="vm_enable_add_intermedio", on_change=mark_visit_dirty)
        st.number_input(
            "ADD intermedio",
            key="vm_add_intermedio",
            step=0.25,
            format="%.2f",
            min_value=0.0,
            disabled=not st.session_state.get("vm_enable_add_intermedio", False),
            on_change=mark_visit_dirty,
        )

    add_preview = _compute_additions(
        st.session_state.get("vm_add_vicino", 0.0),
        st.session_state.get("vm_add_intermedio", 0.0),
        st.session_state.get("vm_enable_add_vicino", True),
        st.session_state.get("vm_enable_add_intermedio", False),
    )
    st.caption(
        f"Prescrizione: vicino {'attivo' if add_preview['enable_vicino'] else 'non attivo'} "
        f"({add_preview['vicino']:+.2f}) · intermedio {'attivo' if add_preview['enable_intermedio'] else 'non attivo'} "
        f"({add_preview['intermedio']:+.2f})"
    )

    st.text_area("Note", key="vm_note", height=120, on_change=mark_visit_dirty)

    auto1, auto2 = st.columns([2,1])
    with auto1:
        autosave_caption = _autosave_caption()
        if autosave_caption:
            st.caption(autosave_caption)
        elif st.session_state.get("vm_autosave_enabled"):
            st.caption("Autosave avanzato attivo.")
    with auto2:
        if st.session_state.get("vm_autosave_enabled") and st.session_state.get("vm_form_dirty"):
            if st.button("⚡ Autosalva ora", key="vm_autosave_now"):
                visit_id, action = persist_current_visit(conn, paziente_id, reason="autosalvataggio manuale")
                st.success(f"Autosalvataggio {action}. ID: {visit_id}")
                st.rerun()

    st.subheader("Professionisti Studio The Organism")
    _ensure_professionals_state()
    professionisti = st.session_state.get("vm_professionals", [])
    professionisti_labels = [item.get("label") for item in professionisti]
    if professionisti_labels:
        current_prof = st.session_state.get("vm_active_professional")
        default_prof_idx = professionisti_labels.index(current_prof) if current_prof in professionisti_labels else 0
        st.selectbox(
            "Professionista attivo",
            professionisti_labels,
            index=default_prof_idx,
            key="vm_active_professional",
        )
        active_prof = _get_active_professional()
        active_lines = active_prof.get("lines") or [active_prof.get("label", "")]
        st.caption(" · ".join([line for line in active_lines if line]))

    with st.expander("➕ Gestione professionisti Studio The Organism", expanded=False):
        gp1, gp2 = st.columns(2)
        with gp1:
            new_prof_label = st.text_input("Nome professionista", key="vm_new_prof_label")
            new_prof_line2 = st.text_input("Qualifica riga 2", key="vm_new_prof_line2")
        with gp2:
            new_prof_line3 = st.text_input("Qualifica riga 3", key="vm_new_prof_line3")
            st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Aggiungi professionista", key="vm_add_professional"):
            lines = _normalize_professional_lines([new_prof_label, new_prof_line2, new_prof_line3])
            if not new_prof_label.strip():
                st.warning("Inserisci almeno il nome del professionista.")
            else:
                existing = st.session_state.get("vm_professionals", [])
                if any((item.get("label") == new_prof_label.strip()) for item in existing):
                    st.info("Professionista già presente nell'elenco.")
                else:
                    existing.append({"label": new_prof_label.strip(), "lines": lines or [new_prof_label.strip()]})
                    st.session_state["vm_professionals"] = existing
                    st.session_state["vm_active_professional"] = new_prof_label.strip()
                    st.success("Professionista aggiunto correttamente.")
                    st.rerun()

        removable = [lbl for lbl in professionisti_labels if lbl not in {"Dr. Giuseppe Ferraioli", "Dott. Salvatore Adriano Cirillo"}]
        if removable:
            prof_to_remove = st.selectbox("Rimuovi professionista aggiunto", [""] + removable, key="vm_remove_prof_select")
            if prof_to_remove and st.button("Rimuovi professionista", key="vm_remove_professional_btn"):
                st.session_state["vm_professionals"] = [item for item in st.session_state.get("vm_professionals", []) if item.get("label") != prof_to_remove]
                if st.session_state.get("vm_active_professional") == prof_to_remove:
                    st.session_state["vm_active_professional"] = "Dr. Giuseppe Ferraioli"
                st.success("Professionista rimosso.")
                st.rerun()

    st.subheader("Opzioni stampa")
    pr1, pr2 = st.columns(2)
    with pr1:
        st.checkbox(
            "Mostra professionista attivo nel referto",
            key="vm_include_professional_referto",
        )
    with pr2:
        st.checkbox(
            "Mostra professionista attivo nella prescrizione",
            key="vm_include_professional_prescrizione",
        )

    save1, save2, save3 = st.columns([1, 1, 1])

    with save1:
        if st.session_state.get("vm_mode") == "edit" and st.session_state.get("vm_loaded_visit_id"):
            if st.button("Aggiorna visita"):
                updated_id, _ = persist_current_visit(conn, paziente_id, reason="salvataggio manuale")
                st.session_state["vm_mode"] = "edit"
                st.success(f"Visita aggiornata correttamente. ID: {updated_id}")
        else:
            if st.button("Salva visita"):
                new_id, _ = persist_current_visit(conn, paziente_id, reason="salvataggio manuale")
                st.session_state["vm_mode"] = "edit"
                st.success(f"Visita salvata correttamente. ID: {new_id}")

    payload_corrente = build_visit_payload()

    with save2:
        current_pdf = _build_referto_letterhead_pdf(
            payload_corrente,
            patient_label=selected_paziente,
            visit_id=st.session_state.get("vm_loaded_visit_id"),
            include_professional=st.session_state.get("vm_include_professional_referto", False),
        )
        st.download_button(
            "PDF referto",
            data=current_pdf,
            file_name=f"referto_visita_{selected_paziente.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="vm_download_current_pdf",
        )

    with save3:
        current_prescrizione = _build_prescrizione_letterhead_pdf(
            payload_corrente,
            patient_label=selected_paziente,
            include_professional=st.session_state.get("vm_include_professional_prescrizione", False),
        )
        st.download_button(
            "PDF prescrizione",
            data=current_prescrizione,
            file_name=f"prescrizione_occhiali_{selected_paziente.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="vm_download_current_prescrizione",
        )

    st.subheader("Storico visite")
    visite = list_visite(conn, paziente_id)

    if not visite:
        st.info("Nessuna visita salvata per questo paziente.")
        return

    def _to_float_local(x):
        try:
            if x is None:
                return None
            if isinstance(x, (int, float)):
                return float(x)
            s = str(x).strip().replace(",", ".")
            if s == "":
                return None
            return float(s)
        except Exception:
            return None

    def _parse_pair_values_local(s):
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

    trend = []
    for row0 in visite:
        dati_json0 = _row_get(row0, "dati_json", 2)

        try:
            pj0 = json.loads(dati_json0) if isinstance(dati_json0, str) else dati_json0
        except Exception:
            continue

        if not isinstance(pj0, dict):
            continue

        eo0 = pj0.get("esame_obiettivo") or {}

        iop_od0 = _to_float_local(eo0.get("pressione_endoculare_od"))
        iop_os0 = _to_float_local(eo0.get("pressione_endoculare_os"))

        if iop_od0 is None and iop_os0 is None:
            od_old, os_old = _parse_pair_values_local(eo0.get("pressione_endoculare") or "")
            iop_od0 = _to_float_local(od_old)
            iop_os0 = _to_float_local(os_old)

        if iop_od0 is None and iop_os0 is None:
            continue

        d_raw = _row_get(row0, "data_visita", 1) or pj0.get("data") or pj0.get("data_visita") or ""
        try:
            d0 = dt.date.fromisoformat(str(d_raw)[:10])
        except Exception:
            continue

        trend.append((d0, iop_od0, iop_os0))

    if trend:
        trend.sort(key=lambda x: x[0])
        dates = [t[0] for t in trend]
        od_vals = [t[1] for t in trend]
        os_vals = [t[2] for t in trend]

        st.markdown("#### 📈 Andamento IOP (OD/OS) nel tempo")
        fig, ax = plt.subplots()
        ax.plot(dates, od_vals, marker="o", label="IOP OD")
        ax.plot(dates, os_vals, marker="o", label="IOP OS")
        ax.axhline(21, linestyle="--", linewidth=1, label="Soglia 21 mmHg")
        ax.set_ylabel("mmHg")
        ax.set_xlabel("Data visita")
        ax.legend()
        ax.grid(True, alpha=0.25)
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("Nessun dato IOP presente nello storico (compila IOP OD/OS e salva almeno una visita).")

    visit_choices = []
    visit_lookup = {}
    for row in visite:
        visit_id = _row_get(row, "id", 0)
        data_visita = _row_get(row, "data_visita", 1)
        label = f"Visita #{visit_id} - {str(data_visita)[:10]}"
        visit_choices.append(label)
        visit_lookup[label] = row

    current_hist_id = st.session_state.get("vm_history_selected_visit_id")
    if current_hist_id is None or all(_row_get(r, "id", 0) != current_hist_id for r in visite):
        st.session_state["vm_history_selected_visit_id"] = _row_get(visite[0], "id", 0)

    current_hist_label = None
    for label, row in visit_lookup.items():
        if _row_get(row, "id", 0) == st.session_state.get("vm_history_selected_visit_id"):
            current_hist_label = label
            break
    if current_hist_label is None:
        current_hist_label = visit_choices[0]

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("⬅️ Precedente", key="vm_hist_prev"):
            idx = visit_choices.index(current_hist_label)
            if idx < len(visit_choices) - 1:
                new_label = visit_choices[idx + 1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_label], "id", 0)
                st.rerun()
    with nav2:
        chosen_hist_label = st.selectbox("Naviga nello storico", visit_choices, index=visit_choices.index(current_hist_label), key="vm_history_selected_label")
        st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[chosen_hist_label], "id", 0)
    with nav3:
        if st.button("Successiva ➡️", key="vm_hist_next"):
            idx = visit_choices.index(chosen_hist_label)
            if idx > 0:
                new_label = visit_choices[idx - 1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_label], "id", 0)
                st.rerun()

    selected_hist_row = visit_lookup[chosen_hist_label]
    selected_visit_id = _row_get(selected_hist_row, "id", 0)
    selected_data_visita = _row_get(selected_hist_row, "data_visita", 1)
    selected_dati_json = _row_get(selected_hist_row, "dati_json", 2)

    try:
        selected_preview = json.loads(selected_dati_json) if isinstance(selected_dati_json, str) else selected_dati_json
    except Exception:
        selected_preview = None

    st.markdown(f"### Visita selezionata: #{selected_visit_id} — {selected_data_visita}")
    if selected_preview is not None:
        p1, p2 = st.columns(2)
        with p1:
            st.write("**Tipo visita:**", selected_preview.get("tipo_visita", ""))
            st.write("**Data:**", selected_preview.get("data", ""))
        with p2:
            st.write("**Anamnesi:**", selected_preview.get("anamnesi", "") or "-")
            st.write("**Note:**", selected_preview.get("note", "") or "-")
    else:
        st.info("Anteprima non disponibile per questa visita.")

    hist1, hist2, hist3, hist4 = st.columns([1, 1, 1, 1])
    with hist1:
        if st.button("Carica visita selezionata", key=f"vm_load_selected_{selected_visit_id}"):
            if st.session_state.get("vm_form_dirty"):
                st.session_state["vm_pending_action"] = {
                    "type": "load_specific_visit",
                    "visit_id": selected_visit_id,
                    "dati_json": selected_dati_json,
                }
                st.rerun()
            perform_pending_action(conn, {"type": "load_specific_visit", "visit_id": selected_visit_id, "dati_json": selected_dati_json}, paziente_id, pazienti_map)
            st.rerun()
    with hist2:
        if selected_preview is not None:
            pdf_hist = _build_referto_letterhead_pdf(
                selected_preview,
                patient_label=selected_paziente,
                visit_id=selected_visit_id,
                include_professional=st.session_state.get("vm_include_professional_referto", False),
            )
            st.download_button(
                "Scarica PDF referto",
                data=pdf_hist,
                file_name=f"referto_visita_{selected_visit_id}_{selected_paziente.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"vm_pdf_selected_{selected_visit_id}",
            )
    with hist3:
        if selected_preview is not None:
            pdf_pr_hist = _build_prescrizione_letterhead_pdf(
                selected_preview,
                patient_label=selected_paziente,
                include_professional=st.session_state.get("vm_include_professional_prescrizione", False),
            )
            st.download_button(
                "Scarica PDF prescrizione",
                data=pdf_pr_hist,
                file_name=f"prescrizione_occhiali_{selected_visit_id}_{selected_paziente.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"vm_pr_selected_{selected_visit_id}",
            )
    with hist4:
        if st.button("Cancella visita selezionata", key=f"vm_delete_selected_{selected_visit_id}"):
            st.session_state["vm_delete_confirm"] = selected_visit_id
            st.rerun()

    with st.expander("📚 Elenco completo visite", expanded=False):
        for row in visite:
            visit_id = _row_get(row, "id", 0)
            data_visita = _row_get(row, "data_visita", 1)
            dati_json = _row_get(row, "dati_json", 2)
            with st.expander(f"Visita #{visit_id} - {data_visita}"):
                try:
                    preview = json.loads(dati_json) if isinstance(dati_json, str) else dati_json
                    st.write("Tipo visita:", preview.get("tipo_visita", ""))
                    st.write("Anamnesi:", preview.get("anamnesi", ""))
                except Exception:
                    st.write("Anteprima non disponibile")

    delete_id = st.session_state.get("vm_delete_confirm")
    if delete_id:
        st.warning(f"Stai per cancellare la visita ID {delete_id}. Confermi?")
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Conferma cancellazione", key="vm_delete_yes", type="primary"):
                delete_visit(conn, delete_id)
                if st.session_state.get("vm_loaded_visit_id") == delete_id:
                    clear_visit_form()
                st.session_state["vm_delete_confirm"] = None
                st.success("Visita cancellata correttamente.")
                st.rerun()

        with c2:
            if st.button("Annulla", key="vm_delete_no"):
                st.session_state["vm_delete_confirm"] = None
                st.rerun()


def ui_visita_visiva():
    conn = get_conn()
    return ui_visita_visiva_v2(conn)
