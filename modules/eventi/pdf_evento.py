# -*- coding: utf-8 -*-
"""
modules/eventi/pdf_evento.py

Generatore PDF della conferma di iscrizione a un evento.

Stile coerente con il resto del gestionale:
- letterhead se disponibile (best-effort)
- brand color verde #1D6B44
- una pagina sola, compatto e leggibile
"""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

logger = logging.getLogger(__name__)

ROME_TZ = ZoneInfo("Europe/Rome")

# Branding
BRAND_GREEN = colors.HexColor("#1D6B44")
BRAND_GREEN_LIGHT = colors.HexColor("#E8F0EB")
DARK = colors.HexColor("#1A1A1A")
GRAY = colors.HexColor("#666666")
LIGHTGRAY = colors.HexColor("#CCCCCC")

LETTERHEAD_CANDIDATES = [
    "vision_manager/letterhead_neutral_A4.jpg",
    "vision_manager/assets/letterhead_neutral_A4.jpg",
    "assets/letterhead_neutral_A4.jpg",
    "assets/letterhead_the_organism_clean_A4.jpg",
]


def _find_letterhead() -> Optional[str]:
    for path in LETTERHEAD_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _draw_letterhead(c: canvas.Canvas, letterhead_path: Optional[str] = None) -> None:
    path = letterhead_path or _find_letterhead()
    if not path:
        return
    try:
        width, height = A4
        c.drawImage(path, 0, 0, width=width, height=height, mask="auto")
    except Exception as e:
        logger.warning(f"Impossibile disegnare letterhead: {e}")


def _on_page(canvas_obj, doc):
    _draw_letterhead(canvas_obj)


def _format_data_ora(dt: datetime) -> tuple[str, str]:
    """Restituisce (data_string, ora_string) in italiano."""
    GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    MESI = [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
    ]
    if dt.tzinfo is not None:
        dt = dt.astimezone(ROME_TZ)
    g = GIORNI[dt.weekday()]
    data_str = f"{g} {dt.day} {MESI[dt.month - 1]} {dt.year}"
    ora_str = dt.strftime("%H:%M")
    return data_str, ora_str


def genera_pdf_conferma(evento: dict, iscrizione: dict) -> bytes:
    """
    Genera il PDF di conferma iscrizione.

    Args:
        evento: dict con campi di ev_eventi
        iscrizione: dict con campi di ev_iscrizioni

    Returns:
        bytes del PDF
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=20 * mm,
        title=f"Conferma iscrizione - {evento.get('titolo', '')}",
        author="Studio The Organism",
    )

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle(
        "h1", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=18, textColor=BRAND_GREEN,
        spaceAfter=4, alignment=TA_LEFT,
    )
    style_h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=12, textColor=BRAND_GREEN,
        spaceBefore=12, spaceAfter=6, alignment=TA_LEFT,
    )
    style_body = ParagraphStyle(
        "body", parent=styles["BodyText"],
        fontName="Helvetica", fontSize=10, textColor=DARK,
        leading=14, alignment=TA_LEFT,
    )
    style_label = ParagraphStyle(
        "label", parent=styles["BodyText"],
        fontName="Helvetica-Bold", fontSize=10, textColor=GRAY,
    )
    style_caption = ParagraphStyle(
        "caption", parent=styles["BodyText"],
        fontName="Helvetica-Oblique", fontSize=8, textColor=GRAY,
        alignment=TA_CENTER, leading=11,
    )

    story = []

    # === HEADER ===
    story.append(Paragraph("Conferma di iscrizione", style_h1))
    iscrizione_id = iscrizione.get("id", "—")
    created_at = iscrizione.get("created_at")
    if isinstance(created_at, datetime):
        ts = created_at.astimezone(ROME_TZ).strftime("%d/%m/%Y %H:%M") if created_at.tzinfo else created_at.strftime("%d/%m/%Y %H:%M")
    else:
        ts = ""
    story.append(Paragraph(
        f"<font color='#666666'>Iscrizione n. <b>{iscrizione_id}</b> · registrata il {ts}</font>",
        style_body,
    ))
    story.append(Spacer(1, 10 * mm))

    # === BOX EVENTO ===
    data_str, ora_str = _format_data_ora(evento["data_ora"])
    rows = [
        [Paragraph("<b>Evento</b>", style_label), Paragraph(evento.get("titolo", ""), style_body)],
        [Paragraph("<b>Data</b>", style_label), Paragraph(data_str, style_body)],
        [Paragraph("<b>Ora</b>", style_label), Paragraph(f"ore {ora_str}", style_body)],
    ]
    if evento.get("durata_minuti"):
        rows.append([
            Paragraph("<b>Durata</b>", style_label),
            Paragraph(f"{evento['durata_minuti']} minuti", style_body),
        ])
    if evento.get("sede"):
        rows.append([
            Paragraph("<b>Sede</b>", style_label),
            Paragraph(evento["sede"], style_body),
        ])
    if evento.get("conduttore"):
        rows.append([
            Paragraph("<b>Conduttore</b>", style_label),
            Paragraph(evento["conduttore"], style_body),
        ])
    if evento.get("prezzo") is not None and float(evento["prezzo"]) > 0:
        rows.append([
            Paragraph("<b>Contributo</b>", style_label),
            Paragraph(f"€ {float(evento['prezzo']):.2f}", style_body),
        ])

    t = Table(rows, colWidths=[35 * mm, 130 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_GREEN_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GREEN),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    # === DESCRIZIONE ===
    if evento.get("descrizione"):
        story.append(Paragraph("Descrizione", style_h2))
        story.append(Paragraph(evento["descrizione"].replace("\n", "<br/>"), style_body))

    # === DATI ISCRITTO ===
    story.append(Paragraph("Dati iscritto", style_h2))
    nome_completo = f"{iscrizione.get('cognome', '')} {iscrizione.get('nome', '')}".strip()
    rows_i = [
        [Paragraph("<b>Nome</b>", style_label), Paragraph(nome_completo, style_body)],
        [Paragraph("<b>Email</b>", style_label), Paragraph(iscrizione.get("email", ""), style_body)],
    ]
    if iscrizione.get("telefono"):
        rows_i.append([Paragraph("<b>Telefono</b>", style_label), Paragraph(iscrizione["telefono"], style_body)])

    stato = iscrizione.get("stato", "confermata")
    stato_label = {
        "confermata": "<font color='#1D6B44'><b>Confermata</b></font>",
        "lista_attesa": "<font color='#B86A00'><b>Lista d'attesa</b></font>",
        "annullata": "<font color='#A00000'><b>Annullata</b></font>",
    }.get(stato, stato)
    rows_i.append([Paragraph("<b>Stato</b>", style_label), Paragraph(stato_label, style_body)])

    t2 = Table(rows_i, colWidths=[35 * mm, 130 * mm])
    t2.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHTGRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LIGHTGRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)

    # === NOTE PRATICHE ===
    story.append(Paragraph("Note pratiche", style_h2))
    note_text = (
        "• Conserva questa email/PDF come ricevuta dell'iscrizione.<br/>"
        "• In caso di impossibilità a partecipare, ti chiediamo cortesemente "
        "di avvisare lo Studio per liberare il posto a chi è in lista d'attesa.<br/>"
        "• Per qualsiasi necessità puoi rispondere a questa email."
    )
    if stato == "lista_attesa":
        note_text = (
            "<font color='#B86A00'><b>Sei in lista d'attesa.</b></font> "
            "Riceverai conferma di partecipazione non appena si libera un posto.<br/><br/>"
            + note_text
        )
    story.append(Paragraph(note_text, style_body))

    # === FOOTER ===
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph(
        "Studio The Organism — Via De Rosa 46, 84016 Pagani (SA)<br/>"
        "www.theorganism.com",
        style_caption,
    ))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
