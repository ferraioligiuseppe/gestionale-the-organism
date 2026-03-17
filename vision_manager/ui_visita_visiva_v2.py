import json
import datetime as dt
from datetime import date, datetime
import calendar
from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st

# Se necessario, cambia questo import in:
# from .db import get_conn
from vision_manager.db import get_conn
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"


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
        "vm_note": "",
        "vm_pending_load": None,
        "vm_loaded_visit_id": None,
        "vm_delete_confirm": None,
        "vm_mode": "new",
        "vm_current_patient_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_visit_form():
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
    st.session_state["vm_note"] = ""
    st.session_state["vm_loaded_visit_id"] = None
    st.session_state["vm_mode"] = "new"


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
        },
        "note": st.session_state.get("vm_note", ""),
    }


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
    st.session_state["vm_note"] = payload.get("note", "")
    st.session_state["vm_loaded_visit_id"] = visit_id
    st.session_state["vm_mode"] = "edit" if visit_id else "new"


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

def _build_referto_letterhead_pdf(payload, patient_label="Paziente", visit_id=None):
    data_pdf = {
        "data": str(payload.get("data", "")),
        "paziente": patient_label,
        "anamnesi": payload.get("anamnesi", ""),
        "acuita": payload.get("acuita", {}) or {},
        "esame_obiettivo": payload.get("esame_obiettivo", {}) or {},
        "note": payload.get("note", ""),
    }
    return build_referto_oculistico_a4(data_pdf, LETTERHEAD)


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


def _build_prescrizione_letterhead_pdf(payload, patient_label="Paziente"):
    corr_fin = payload.get("correzione_finale", {}) or {}
    od = corr_fin.get("od", {}) or {}
    os_ = corr_fin.get("os", {}) or {}
    add_value = _safe_float(corr_fin.get("add", 0.0), 0.0)

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
            "od": _rx_add(od, add_value / 2.0),
            "os": _rx_add(os_, add_value / 2.0),
        },
        "vicino": {
            "od": _rx_add(od, add_value),
            "os": _rx_add(os_, add_value),
        },
        "lenti": [],
    }
    return build_prescrizione_occhiali_a4(data_pdf, LETTERHEAD)


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


# =========================================================
# UI
# =========================================================

def ui_visita_visiva_v2(conn):
    ensure_visit_state()
    apply_pending_visit_load()

    st.title("Vision Manager")

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

    selected_paziente = st.selectbox("Seleziona paziente", pazienti_options, index=default_idx)
    paziente_id = pazienti_map[selected_paziente]

    previous_patient_id = st.session_state.get("vm_current_patient_id")
    if previous_patient_id is None:
        st.session_state["vm_current_patient_id"] = paziente_id
    elif str(previous_patient_id) != str(paziente_id):
        clear_visit_form()
        st.session_state["vm_current_patient_id"] = paziente_id

    st.session_state["vision_last_pid"] = paziente_id

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

    top1, top2, top3 = st.columns([1, 1, 2])

    with top1:
        if st.button("Nuova visita"):
            clear_visit_form()
            st.rerun()

    with top2:
        if st.session_state.get("vm_mode") == "edit":
            st.caption("Modalita: modifica")
        else:
            st.caption("Modalita: nuova")

    with top3:
        loaded_id = st.session_state.get("vm_loaded_visit_id")
        if loaded_id:
            st.info(f"Visita caricata ID {loaded_id}")

    if selected_age is not None:
        st.info(f"Età paziente: {selected_age} anni")

    st.subheader("Dati visita")

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Tipo visita", ["oculistica"], key="vm_tipo_visita")
    with c2:
        st.date_input("Data visita", key="vm_data_visita")

    st.text_area("Anamnesi", key="vm_anamnesi", height=120)

    st.subheader("Acuita visiva")
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        st.text_input("AVN OD", key="vm_acuita_naturale_od")
    with a2:
        st.text_input("AVN OS", key="vm_acuita_naturale_os")
    with a3:
        st.text_input("AVC OD", key="vm_acuita_corretta_od")
    with a4:
        st.text_input("AVC OS", key="vm_acuita_corretta_os")

    st.subheader("Esame obiettivo")
    e1, e2 = st.columns(2)
    with e1:
        st.text_input("Congiuntiva", key="vm_congiuntiva")
        st.text_input("Cornea", key="vm_cornea")
        st.text_input("Camera anteriore", key="vm_camera_anteriore")
        st.text_input("Cristallino", key="vm_cristallino")
        st.text_input("Vitreo", key="vm_vitreo")
    with e2:
        st.text_input("Fondo oculare", key="vm_fondo_oculare")
        st.text_input("IOP OD", key="vm_iop_od")
        st.text_input("IOP OS", key="vm_iop_os")
        st.text_input("Pachimetria OD", key="vm_pachimetria_od")
        st.text_input("Pachimetria OS", key="vm_pachimetria_os")

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
            st.write(f"IOP inserita: **{_fmt_value(st.session_state.get('vm_iop_od'), '-') } mmHg**")
            st.write(f"Pachimetria: **{_fmt_value(st.session_state.get('vm_pachimetria_od'), '-') } µm**")
            if att["od"].get("adj") is not None:
                st.write(f"IOP stimata da CCT: **{att['od']['adj']:.1f} mmHg**")
            if att["od"]["flag"]:
                st.warning(att["od"]["reason"] or "Possibile attenzione clinica.")
            else:
                st.success("Nessun flag con i dati inseriti.")

        with r2:
            st.write("**OS**")
            st.write(f"IOP inserita: **{_fmt_value(st.session_state.get('vm_iop_os'), '-') } mmHg**")
            st.write(f"Pachimetria: **{_fmt_value(st.session_state.get('vm_pachimetria_os'), '-') } µm**")
            if att["os"].get("adj") is not None:
                st.write(f"IOP stimata da CCT: **{att['os']['adj']:.1f} mmHg**")
            if att["os"]["flag"]:
                st.warning(att["os"]["reason"] or "Possibile attenzione clinica.")
            else:
                st.success("Nessun flag con i dati inseriti.")

    st.subheader("Correzione abituale")
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        st.number_input("OD SF", key="vm_ca_od_sf", step=0.25, format="%.2f")
        st.number_input("OS SF", key="vm_ca_os_sf", step=0.25, format="%.2f")
    with ca2:
        st.number_input("OD CIL", key="vm_ca_od_cyl", step=0.25, format="%.2f")
        st.number_input("OS CIL", key="vm_ca_os_cyl", step=0.25, format="%.2f")
    with ca3:
        st.number_input("OD AX", key="vm_ca_od_ax", step=1, min_value=0, max_value=180)
        st.number_input("OS AX", key="vm_ca_os_ax", step=1, min_value=0, max_value=180)

    st.subheader("Correzione finale")
    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        st.number_input("OD SF finale", key="vm_cf_od_sf", step=0.25, format="%.2f")
        st.number_input("OS SF finale", key="vm_cf_os_sf", step=0.25, format="%.2f")
    with cf2:
        st.number_input("OD CIL finale", key="vm_cf_od_cyl", step=0.25, format="%.2f")
        st.number_input("OS CIL finale", key="vm_cf_os_cyl", step=0.25, format="%.2f")
    with cf3:
        st.number_input("OD AX finale", key="vm_cf_od_ax", step=1, min_value=0, max_value=180)
        st.number_input("OS AX finale", key="vm_cf_os_ax", step=1, min_value=0, max_value=180)

    st.text_area("Note", key="vm_note", height=120)

    save1, save2, save3 = st.columns([1, 1, 1])

    with save1:
        if st.session_state.get("vm_mode") == "edit" and st.session_state.get("vm_loaded_visit_id"):
            if st.button("Aggiorna visita"):
                updated_id = update_existing_visit(conn, st.session_state["vm_loaded_visit_id"], paziente_id)
                st.success(f"Visita aggiornata correttamente. ID: {updated_id}")
        else:
            if st.button("Salva visita"):
                new_id = save_new_visit(conn, paziente_id)
                st.success(f"Visita salvata correttamente. ID: {new_id}")

    payload_corrente = build_visit_payload()

    with save2:
        current_pdf = _build_referto_letterhead_pdf(
            payload_corrente,
            patient_label=selected_paziente,
            visit_id=st.session_state.get("vm_loaded_visit_id"),
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
                preview = None
                st.write("Anteprima non disponibile")

            hist1, hist2, hist3, hist4 = st.columns([1, 1, 1, 1])
            with hist1:
                if st.button("Carica", key=f"vm_load_{visit_id}"):
                    st.session_state["vm_pending_load"] = {
                        "visit_id": visit_id,
                        "dati_json": dati_json,
                    }
                    st.rerun()
            with hist2:
                if preview is not None:
                    pdf_hist = _build_referto_letterhead_pdf(
                        preview,
                        patient_label=selected_paziente,
                        visit_id=visit_id,
                    )
                    st.download_button(
                        "Scarica PDF referto",
                        data=pdf_hist,
                        file_name=f"referto_visita_{visit_id}_{selected_paziente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"vm_pdf_{visit_id}",
                    )

            with hist3:
                if preview is not None:
                    pdf_pr_hist = _build_prescrizione_letterhead_pdf(
                        preview,
                        patient_label=selected_paziente,
                    )
                    st.download_button(
                        "Scarica PDF prescrizione",
                        data=pdf_pr_hist,
                        file_name=f"prescrizione_occhiali_{visit_id}_{selected_paziente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"vm_pr_{visit_id}",
                    )

            with hist4:
                if st.button("Cancella", key=f"vm_delete_{visit_id}"):
                    st.session_state["vm_delete_confirm"] = visit_id
                    st.rerun()

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
