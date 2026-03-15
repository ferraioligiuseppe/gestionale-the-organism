import json
from datetime import date, datetime
from io import BytesIO

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Se necessario, cambia questo import in:
# from .db import get_conn
from vision_manager.db import get_conn


# =========================================================
# HELPERS GENERICI
# =========================================================

def _parse_date_safe(value):
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return date.today()


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
        "vm_mode": "new",
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
# PDF REFERTO
# =========================================================

def _p(text, style):
    safe = _fmt_value(text, "-")
    safe = safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br/>")
    return Paragraph(safe, style)


def _build_two_col_table(rows, col_widths, style):
    tbl = Table(rows, colWidths=col_widths, hAlign="LEFT")
    tbl.setStyle(style)
    return tbl


def generate_referto_pdf(payload, patient_label="Paziente", visit_id=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Referto visita visiva",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="VMTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1f4f46"),
        alignment=TA_LEFT,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="VMSub",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#47645d"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="VMSection",
        parent=styles["Heading2"],
        fontSize=11.5,
        leading=14,
        textColor=colors.white,
        backColor=colors.HexColor("#2f6f63"),
        borderPadding=(5, 8, 5),
        spaceBefore=8,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="VMLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#33534b"),
    ))
    styles.add(ParagraphStyle(
        name="VMBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.black,
    ))

    label_style = styles["VMLabel"]
    body_style = styles["VMBody"]

    esame = payload.get("esame_obiettivo", {}) or {}
    acuita = payload.get("acuita", {}) or {}
    naturale = acuita.get("naturale", {}) or {}
    corretta = acuita.get("corretta", {}) or {}
    corr_ab = payload.get("correzione_abituale", {}) or {}
    corr_fin = payload.get("correzione_finale", {}) or {}

    story = []
    story.append(Paragraph("Referto visita visiva", styles["VMTitle"]))

    meta_text = f"Paziente: <b>{patient_label}</b> - Data visita: <b>{_fmt_value(payload.get('data'))}</b>"
    if visit_id:
        meta_text += f" - ID visita: <b>{visit_id}</b>"
    story.append(Paragraph(meta_text, styles["VMSub"]))
    story.append(Spacer(1, 6))

    meta_table = Table(
        [
            [_p("Tipo visita", label_style), _p(payload.get("tipo_visita", "oculistica"), body_style)],
            [_p("Anamnesi", label_style), _p(payload.get("anamnesi", ""), body_style)],
        ],
        colWidths=[38 * mm, 136 * mm],
        hAlign="LEFT",
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f8f7")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#c9d7d2")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8e2de")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Acuita visiva", styles["VMSection"]))
    acuita_rows = [
        [_p("Parametro", label_style), _p("OD", label_style), _p("OS", label_style)],
        [_p("Naturale", body_style), _p(naturale.get("od", ""), body_style), _p(naturale.get("os", ""), body_style)],
        [_p("Corretta", body_style), _p(corretta.get("od", ""), body_style), _p(corretta.get("os", ""), body_style)],
    ]
    acuita_tbl = Table(acuita_rows, colWidths=[55 * mm, 58 * mm, 58 * mm], hAlign="LEFT")
    acuita_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5efec")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#b9ccc6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e2de")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(acuita_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Esame obiettivo", styles["VMSection"]))
    esame_rows = [
        [_p("Parametro", label_style), _p("Risultato", label_style)],
        [_p("Congiuntiva", body_style), _p(esame.get("congiuntiva", ""), body_style)],
        [_p("Cornea", body_style), _p(esame.get("cornea", ""), body_style)],
        [_p("Camera anteriore", body_style), _p(esame.get("camera_anteriore", ""), body_style)],
        [_p("Cristallino", body_style), _p(esame.get("cristallino", ""), body_style)],
        [_p("Vitreo", body_style), _p(esame.get("vitreo", ""), body_style)],
        [_p("Fondo oculare", body_style), _p(esame.get("fondo_oculare", ""), body_style)],
        [_p("Pressione endoculare OD", body_style), _p(esame.get("pressione_endoculare_od", ""), body_style)],
        [_p("Pressione endoculare OS", body_style), _p(esame.get("pressione_endoculare_os", ""), body_style)],
        [_p("Pachimetria OD", body_style), _p(esame.get("pachimetria_od", ""), body_style)],
        [_p("Pachimetria OS", body_style), _p(esame.get("pachimetria_os", ""), body_style)],
    ]
    esame_tbl = _build_two_col_table(
        esame_rows,
        [58 * mm, 115 * mm],
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5efec")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#b9ccc6")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e2de")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(esame_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Correzione ottica", styles["VMSection"]))
    rx_rows = [
        [_p("Tipo", label_style), _p("OD", label_style), _p("OS", label_style)],
        [_p("Abituale", body_style), _p(_fmt_rx_block(corr_ab.get("od", {})), body_style), _p(_fmt_rx_block(corr_ab.get("os", {})), body_style)],
        [_p("Finale", body_style), _p(_fmt_rx_block(corr_fin.get("od", {})), body_style), _p(_fmt_rx_block(corr_fin.get("os", {})), body_style)],
    ]
    rx_tbl = Table(rx_rows, colWidths=[32 * mm, 69 * mm, 69 * mm], hAlign="LEFT")
    rx_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5efec")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#b9ccc6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e2de")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(rx_tbl)

    note = _fmt_value(payload.get("note", ""), "")
    if note:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Note cliniche", styles["VMSection"]))
        note_table = Table([[_p(note, body_style)]], colWidths=[173 * mm], hAlign="LEFT")
        note_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7faf9")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#c9d7d2")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(note_table)

    story.append(Spacer(1, 18))
    footer_table = Table(
        [[_p("Firma e timbro", label_style), _p("_______________________________", body_style)]],
        colWidths=[42 * mm, 85 * mm],
        hAlign="LEFT",
    )
    footer_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(footer_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =========================================================
# DB
# =========================================================

def list_pazienti(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, cognome, nome
            FROM pazienti
            ORDER BY cognome, nome
            """
        )
        return cur.fetchall()


def list_visite(conn, paziente_id):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, data_visita, dati_json
            FROM visite_visive
            WHERE paziente_id = %s
              AND COALESCE(is_deleted, 0) <> 1
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


# =========================================================
# UI
# =========================================================

def ui_visita_visiva_v2(conn):
    ensure_visit_state()
    apply_pending_visit_load()

    st.title("Vision Manager")

    pazienti = list_pazienti(conn)
    if not pazienti:
        st.warning("Nessun paziente presente.")
        return

    pazienti_options = []
    pazienti_map = {}

    for row in pazienti:
        pid = _row_get(row, "id", 0)
        cognome = _row_get(row, "cognome", 1, "")
        nome = _row_get(row, "nome", 2, "")
        label = f"{cognome} {nome}".strip()
        pazienti_options.append(label)
        pazienti_map[label] = pid

    selected_paziente = st.selectbox("Seleziona paziente", pazienti_options)
    paziente_id = pazienti_map[selected_paziente]

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

    save1, save2, save3 = st.columns([1, 1, 2])

    with save1:
        if st.session_state.get("vm_mode") == "edit" and st.session_state.get("vm_loaded_visit_id"):
            if st.button("Aggiorna visita"):
                updated_id = update_existing_visit(conn, st.session_state["vm_loaded_visit_id"], paziente_id)
                st.success(f"Visita aggiornata correttamente. ID: {updated_id}")
        else:
            if st.button("Salva visita"):
                new_id = save_new_visit(conn, paziente_id)
                st.success(f"Visita salvata correttamente. ID: {new_id}")

    with save2:
        current_pdf = generate_referto_pdf(
            build_visit_payload(),
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

    st.subheader("Storico visite")
    visite = list_visite(conn, paziente_id)

    if not visite:
        st.info("Nessuna visita salvata per questo paziente.")
        return

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

            hist1, hist2 = st.columns([1, 1])
            with hist1:
                if st.button("Carica", key=f"vm_load_{visit_id}"):
                    st.session_state["vm_pending_load"] = {
                        "visit_id": visit_id,
                        "dati_json": dati_json,
                    }
                    st.rerun()
            with hist2:
                if preview is not None:
                    pdf_hist = generate_referto_pdf(preview, patient_label=selected_paziente, visit_id=visit_id)
                    st.download_button(
                        "Scarica PDF",
                        data=pdf_hist,
                        file_name=f"referto_visita_{visit_id}_{selected_paziente.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"vm_pdf_{visit_id}",
                    )


def ui_visita_visiva():
    conn = get_conn()
    return ui_visita_visiva_v2(conn)
