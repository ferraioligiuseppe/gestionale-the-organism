# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/pdf_generator.py

Generatore PDF per i consensi costellazioni familiari.

Modalità supportate:
- 'cartaceo'      → PDF stampabile con campi vuoti per firma a penna
- 'click_studio'  → PDF già firmato con timbro digitale + hash + dati operatore
- 'link_paziente' → PDF firmato con timbro "firmato da remoto" + IP/UA

Branding: stile coerente con The Organism
- letterhead se disponibile (vision_manager/assets/letterhead_the_organism_clean_A4.jpg)
- colore brand verde #1D6B44
- font: Helvetica/Times come nel resto del gestionale
"""

from __future__ import annotations

import io
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

logger = logging.getLogger(__name__)

ROME_TZ = ZoneInfo("Europe/Rome")

# Branding
BRAND_GREEN = colors.HexColor("#1D6B44")
BRAND_GREEN_LIGHT = colors.HexColor("#E8F0EB")
DARK = colors.HexColor("#1A1A1A")
GRAY = colors.HexColor("#666666")
LIGHTGRAY = colors.HexColor("#CCCCCC")

# Path letterhead (best effort, fallback graceful se manca)
LETTERHEAD_CANDIDATES = [
    "vision_manager/assets/letterhead_the_organism_clean_A4.jpg",
    "assets/letterhead_the_organism_clean_A4.jpg",
    "modules/assets/letterhead_the_organism_clean_A4.jpg",
]


def _find_letterhead() -> Optional[str]:
    for path in LETTERHEAD_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def _draw_letterhead(c: canvas.Canvas, letterhead_path: Optional[str] = None) -> None:
    """Disegna letterhead come sfondo, se disponibile."""
    path = letterhead_path or _find_letterhead()
    if not path:
        return
    try:
        width, height = A4
        c.drawImage(path, 0, 0, width=width, height=height, mask='auto')
    except Exception as e:
        logger.warning(f"Letterhead non caricato: {e}")


# =============================================================================
# STILI PARAGRAFO
# =============================================================================

def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=14, leading=18,
            textColor=BRAND_GREEN, alignment=TA_CENTER, spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=11, leading=14,
            textColor=DARK, alignment=TA_LEFT, spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"],
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=GRAY, alignment=TA_LEFT,
        ),
        "voce": ParagraphStyle(
            "voce", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=DARK, alignment=TA_JUSTIFY,
        ),
        "version": ParagraphStyle(
            "version", parent=base["BodyText"],
            fontName="Helvetica-Oblique", fontSize=8, leading=10,
            textColor=GRAY, alignment=TA_CENTER, spaceAfter=10,
        ),
        "stamp_title": ParagraphStyle(
            "stamp_title", parent=base["BodyText"],
            fontName="Helvetica-Bold", fontSize=9, leading=11,
            textColor=BRAND_GREEN, alignment=TA_LEFT,
        ),
        "stamp_body": ParagraphStyle(
            "stamp_body", parent=base["BodyText"],
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=DARK, alignment=TA_LEFT,
        ),
    }
    return styles


# =============================================================================
# CONVERTITORE MARKDOWN → REPORTLAB
# =============================================================================
# Conversione minimale: gestiamo i sottoinsiemi MD usati nei nostri testi
# (heading, bold, italic, listed). Non è un parser MD completo.

def _md_to_paragraphs(md_text: str, styles: dict) -> list:
    """
    Trasforma il testo markdown del template in una lista di Flowable ReportLab.
    Gestisce: # ## ### , **bold**, *italic*, - lista, > quote, righe vuote.
    Ignora: tabelle MD complesse (le voci le rendiamo con Table dedicata).
    """
    flowables = []
    lines = md_text.split("\n")
    i = 0
    paragraph_buffer = []

    def flush():
        if paragraph_buffer:
            text = " ".join(paragraph_buffer).strip()
            if text:
                flowables.append(Paragraph(text, styles["body"]))
            paragraph_buffer.clear()

    while i < len(lines):
        line = lines[i].rstrip()

        # Salta separatori orizzontali ---
        if re.match(r"^-{3,}$", line):
            flush()
            flowables.append(Spacer(1, 6))
            i += 1
            continue

        # Heading
        m_h = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m_h:
            flush()
            level = len(m_h.group(1))
            text = _md_inline(m_h.group(2))
            if level == 1:
                flowables.append(Paragraph(text, styles["title"]))
            else:
                flowables.append(Paragraph(text, styles["subtitle"]))
            i += 1
            continue

        # Lista bullet
        if re.match(r"^[-*]\s+", line):
            flush()
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].rstrip()):
                txt = re.sub(r"^[-*]\s+", "", lines[i].rstrip())
                items.append(_md_inline(txt))
                i += 1
            for it in items:
                flowables.append(Paragraph(f"• {it}", styles["body"]))
            continue

        # Quote
        if line.startswith(">"):
            flush()
            text = _md_inline(line.lstrip("> ").strip())
            flowables.append(Paragraph(f"<i>{text}</i>", styles["small"]))
            i += 1
            continue

        # Tabella MD: skip (le tabelle sono renderizzate via _render_voci_table)
        if line.startswith("|"):
            flush()
            while i < len(lines) and lines[i].startswith("|"):
                i += 1
            continue

        # Riga vuota → flush
        if not line.strip():
            flush()
            i += 1
            continue

        # Riga normale
        paragraph_buffer.append(_md_inline(line))
        i += 1

    flush()
    return flowables


def _md_inline(text: str) -> str:
    """Converte **bold** e *italic* in tag ReportLab."""
    # bold prima di italic (per non confondere)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    # backtick code → mantengo come testo
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    return text


# =============================================================================
# RENDER VOCI (tabella SÌ/NO)
# =============================================================================

def _render_voci_table(voci_template: list[dict], voci_paziente: Optional[dict] = None) -> Table:
    """
    Renderizza la tabella delle voci con checkbox SÌ/NO.

    Args:
        voci_template: list of {codice, testo, obbligatorio, ordine}
        voci_paziente: dict {codice: True/False} se firmato; None se cartaceo vuoto
    """
    styles = _build_styles()
    data = [["#", "Voce", "SÌ", "NO"]]

    for v in sorted(voci_template, key=lambda x: x.get("ordine", 0)):
        codice = v["codice"]
        testo = v["testo"]
        if v.get("obbligatorio"):
            testo += " <i>(obbligatoria)</i>"

        si_mark = ""
        no_mark = ""
        if voci_paziente is not None:
            valore = voci_paziente.get(codice, False)
            si_mark = "✔" if valore else ""
            no_mark = "✔" if not valore else ""

        data.append([
            Paragraph(f"<b>{codice}</b>", styles["voce"]),
            Paragraph(testo, styles["voce"]),
            si_mark,
            no_mark,
        ])

    tbl = Table(
        data,
        colWidths=[18 * mm, 130 * mm, 12 * mm, 12 * mm],
        repeatRows=1,
    )
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, LIGHTGRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_GREEN_LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


# =============================================================================
# TIMBRO DIGITALE
# =============================================================================

def _render_timbro_digitale(
    paziente_nome: str,
    paziente_id: int,
    operatore: Optional[str],
    modalita_firma: str,
    data_accettazione: datetime,
    pdf_hash: Optional[str],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Table:
    """Timbro digitale a piè pagina del PDF firmato (modalità non cartacea)."""
    styles = _build_styles()

    if modalita_firma == "click_studio":
        titolo = "✔ FIRMATO DIGITALMENTE IN STUDIO"
    elif modalita_firma == "link_paziente":
        titolo = "✔ FIRMATO DIGITALMENTE A DISTANZA"
    else:
        titolo = "✔ FIRMATO"

    data_str = data_accettazione.strftime("%d/%m/%Y alle %H:%M:%S (Europe/Rome)")

    righe = [
        f"<b>{titolo}</b>",
        f"da: <b>{paziente_nome}</b> (id paziente: {paziente_id})",
        f"in data: {data_str}",
    ]
    if operatore:
        righe.append(f"alla presenza dell'operatore: <b>{operatore}</b>")
    if ip_address:
        ua_short = (user_agent or "")[:60]
        righe.append(f"dispositivo: IP {ip_address} | UA: {ua_short}")
    if pdf_hash:
        righe.append(
            f"<font name='Courier' size='7'>SHA-256: {pdf_hash}</font>"
        )

    contenuto = "<br/>".join(righe)

    tbl = Table(
        [[Paragraph(contenuto, styles["stamp_body"])]],
        colWidths=[174 * mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_GREEN_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, BRAND_GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


# =============================================================================
# SEZIONE FIRMA CARTACEA
# =============================================================================

def _render_firma_cartacea(paziente_nome: str = "") -> Table:
    """Sezione vuota per firma a penna (modalità cartaceo)."""
    styles = _build_styles()

    data = [
        [
            Paragraph("Luogo e data", styles["small"]),
            Paragraph("Firma del paziente", styles["small"]),
        ],
        [
            Paragraph("_" * 35, styles["body"]),
            Paragraph(f"_" * 35 + (f"<br/><font size='8'>{paziente_nome}</font>" if paziente_nome else ""), styles["body"]),
        ],
    ]
    tbl = Table(data, colWidths=[80 * mm, 95 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    return tbl


# =============================================================================
# API PUBBLICA
# =============================================================================

def genera_pdf_consenso(
    template: dict,
    *,
    modalita_firma: str = "cartaceo",
    paziente_nome: str = "",
    paziente_id: Optional[int] = None,
    voci_paziente: Optional[dict] = None,
    operatore: Optional[str] = None,
    data_accettazione: Optional[datetime] = None,
    pdf_hash: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    titolare_dati: Optional[dict] = None,
) -> bytes:
    """
    Genera il PDF del consenso.

    Args:
        template: dict con 'codice', 'versione', 'nome', 'sottocategoria',
            'testo_md', 'voci' (lista di {codice, testo, obbligatorio, ordine})
        modalita_firma: 'cartaceo' (vuoto, da firmare a penna) | 'click_studio' |
            'link_paziente' (entrambi: già firmato con timbro)
        paziente_nome: "Cognome Nome" del paziente
        paziente_id: id del paziente (per il timbro)
        voci_paziente: dict {codice: True/False} - obbligatorio se non cartaceo
        operatore: nome operatore (per timbro click_studio)
        data_accettazione: timestamp firma (default ora corrente Europe/Rome)
        pdf_hash: SHA-256 calcolato a posteriori (può essere None alla prima
            generazione, poi rigenerare con hash incluso se necessario)
        ip_address, user_agent: tracciamento (per timbro)
        titolare_dati: dict opzionale per personalizzare header con dati studio

    Returns:
        bytes del PDF generato
    """
    if modalita_firma not in ("cartaceo", "click_studio", "link_paziente"):
        raise ValueError(f"modalita_firma invalida: {modalita_firma}")
    if modalita_firma != "cartaceo" and voci_paziente is None:
        raise ValueError("voci_paziente è obbligatorio se modalita_firma != 'cartaceo'")

    if data_accettazione is None:
        data_accettazione = datetime.now(ROME_TZ)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=template.get("nome", "Consenso"),
    )

    styles = _build_styles()
    story = []

    # === HEADER ===
    story.append(Paragraph(template.get("nome", "Consenso"), styles["title"]))
    story.append(Paragraph(
        f"Codice: {template.get('codice', '')} — Versione: {template.get('versione', '')}",
        styles["version"]
    ))

    if paziente_nome or paziente_id:
        info_pz = f"<b>Paziente:</b> {paziente_nome or '(da compilare)'}"
        if paziente_id:
            info_pz += f" — id: {paziente_id}"
        story.append(Paragraph(info_pz, styles["small"]))
        story.append(Spacer(1, 6))

    # === CORPO TESTO MD ===
    testo_md = template.get("testo_md", "")
    flow_md = _md_to_paragraphs(testo_md, styles)
    story.extend(flow_md)

    story.append(Spacer(1, 10))

    # === TABELLA VOCI ===
    voci_template = template.get("voci") or []
    if voci_template:
        story.append(Paragraph("Consensi specifici", styles["subtitle"]))
        story.append(_render_voci_table(voci_template, voci_paziente))
        story.append(Spacer(1, 10))

    # === FIRMA / TIMBRO ===
    if modalita_firma == "cartaceo":
        story.append(Paragraph("Firma", styles["subtitle"]))
        story.append(_render_firma_cartacea(paziente_nome))
    else:
        story.append(_render_timbro_digitale(
            paziente_nome=paziente_nome or "(non specificato)",
            paziente_id=paziente_id or 0,
            operatore=operatore,
            modalita_firma=modalita_firma,
            data_accettazione=data_accettazione,
            pdf_hash=pdf_hash,
            ip_address=ip_address,
            user_agent=user_agent,
        ))

    # === FOOTER PAGINA ===
    def _on_page(c, doc_):
        _draw_letterhead(c, None)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        footer_y = 10 * mm
        c.drawString(18 * mm, footer_y,
            f"{template.get('codice', '')} v{template.get('versione', '')}  |  "
            f"Generato il {datetime.now(ROME_TZ).strftime('%d/%m/%Y %H:%M')}")
        c.drawRightString(192 * mm, footer_y, f"Pagina {c.getPageNumber()}")

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def genera_pdf_revoca(
    *,
    paziente_nome: str,
    paziente_id: int,
    template_codice: str,
    template_versione: str,
    data_revoca: datetime,
    modalita_revoca: str,
    motivazione: str,
    operatore: Optional[str] = None,
) -> bytes:
    """Genera un PDF di conferma revoca."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title="Revoca consenso",
    )

    styles = _build_styles()
    story = [
        Paragraph("REVOCA DEL CONSENSO", styles["title"]),
        Spacer(1, 12),
        Paragraph(
            f"Il/La sottoscritto/a <b>{paziente_nome}</b> (id paziente: {paziente_id}) "
            f"ha revocato il consenso registrato con codice "
            f"<b>{template_codice}</b> versione <b>{template_versione}</b>.",
            styles["body"]
        ),
        Spacer(1, 8),
        Paragraph(
            f"Data della revoca: <b>{data_revoca.strftime('%d/%m/%Y alle %H:%M (Europe/Rome)')}</b>",
            styles["body"]
        ),
        Paragraph(f"Modalità di revoca: <b>{modalita_revoca}</b>", styles["body"]),
        Spacer(1, 8),
        Paragraph("<b>Motivazione:</b>", styles["body"]),
        Paragraph(motivazione or "(non specificata)", styles["body"]),
        Spacer(1, 14),
        Paragraph(
            "Ai sensi dell'art. 7.3 del Regolamento UE 2016/679 (GDPR), la revoca "
            "non pregiudica la liceità del trattamento basato sul consenso "
            "prestato prima della revoca medesima.",
            styles["small"]
        ),
        Spacer(1, 14),
    ]

    if operatore:
        story.append(Paragraph(
            f"Revoca registrata da: <b>{operatore}</b>", styles["small"]
        ))

    def _on_page(c, doc_):
        _draw_letterhead(c, None)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
