# -*- coding: utf-8 -*-
"""
Generatore PDF del referto INPP — Studio The Organism.

Layout:
- Intestazione con logo studio (se presente)
- Dati paziente + data + terapista + motivo
- Riepilogo punteggi per sezione (sintesi)
- Per ciascuna sezione del protocollo: tabella prove + risultati
- Note finali
- Firma

Convenzioni del progetto: ReportLab, brand color verde #1D6B44.
"""

from io import BytesIO
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from .protocollo import PROTOCOLLO_INPP, SCORING_LABELS, calcola_punteggio_sezione


BRAND_GREEN = colors.HexColor("#1D6B44")
LIGHT_GREEN = colors.HexColor("#E8F1EC")
GRAY_TEXT = colors.HexColor("#666666")
BORDER_GRAY = colors.HexColor("#CCCCCC")


# -----------------------------------------------------------------------------
# Stili
# -----------------------------------------------------------------------------

def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, textColor=BRAND_GREEN,
            spaceAfter=4, alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontSize=10, textColor=GRAY_TEXT,
            alignment=TA_CENTER, spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontSize=13, textColor=BRAND_GREEN,
            spaceBefore=14, spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11, textColor=colors.black,
            spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontSize=10, textColor=colors.black,
            spaceAfter=4, alignment=TA_LEFT, leading=13,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontSize=8, textColor=GRAY_TEXT,
        ),
    }


# -----------------------------------------------------------------------------
# Helpers di formattazione
# -----------------------------------------------------------------------------

def _format_value(prova: dict, valori: dict) -> str:
    """Trasforma il valore di una prova in stringa leggibile per il PDF."""
    pid = prova["id"]
    v = valori.get(pid)
    scoring = prova.get("scoring", "0-4")

    if v is None or v == "" or v == "—":
        return "—"

    if scoring == "0-4":
        try:
            n = int(v)
            return f"{n}"
        except (TypeError, ValueError):
            return str(v)
    if scoring == "si_no":
        return str(v)
    if scoring == "lateralita":
        return str(v)
    if scoring == "scelta":
        return str(v)
    if scoring == "numerico":
        try:
            f = float(v)
            return f"{f:.1f}".rstrip("0").rstrip(".") if "." in f"{f:.1f}" else f"{int(f)}"
        except (TypeError, ValueError):
            return str(v)
    if scoring == "testo":
        return str(v)

    return str(v)


def _legenda_scoring_html() -> str:
    items = [f"<b>{k}</b> = {SCORING_LABELS[k].split('/')[0].strip()}" for k in (0, 1, 2, 3, 4)]
    return " &nbsp;·&nbsp; ".join(items)


# -----------------------------------------------------------------------------
# Costruzione corpo del documento
# -----------------------------------------------------------------------------

def _build_intestazione(stili, paziente_nome, data_valutazione, terapista, motivo):
    out = []
    out.append(Paragraph("Studio Associato The Organism", ParagraphStyle(
        "stintest", parent=stili["body"], fontSize=11, textColor=BRAND_GREEN,
        alignment=TA_CENTER, spaceAfter=2,
    )))
    out.append(Paragraph(
        "Dott. Giuseppe Ferraioli — Psicologo Optometrista Comportamentale",
        ParagraphStyle("stintest2", parent=stili["small"], alignment=TA_CENTER, spaceAfter=14),
    ))
    out.append(Paragraph("Valutazione Diagnostica dello Sviluppo Neurologico", stili["title"]))
    out.append(Paragraph("Metodo INPP — Formulario rev. 01/22", stili["subtitle"]))

    # Dati paziente
    rows = [
        ["Paziente:", paziente_nome or "—",
         "Data valutazione:", data_valutazione.strftime("%d/%m/%Y") if isinstance(data_valutazione, date) else str(data_valutazione)],
        ["Terapista:", terapista or "—", "", ""],
    ]
    t = Table(rows, colWidths=[28 * mm, 70 * mm, 32 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), GRAY_TEXT),
        ("TEXTCOLOR", (2, 0), (2, -1), GRAY_TEXT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    out.append(t)

    if motivo:
        out.append(Spacer(1, 6))
        out.append(Paragraph("<b>Motivo della valutazione:</b>", stili["body"]))
        out.append(Paragraph(motivo.replace("\n", "<br/>"), stili["body"]))

    return out


def _build_riepilogo(stili, riepilogo: dict):
    out = []
    out.append(Paragraph("Riepilogo punteggi per sezione", stili["h1"]))
    out.append(Paragraph(
        "Calcolato sulle prove con scoring 0–4. Punteggi più bassi indicano migliore integrazione neuro-evolutiva.",
        stili["small"],
    ))
    out.append(Spacer(1, 4))

    if not riepilogo:
        out.append(Paragraph("— Nessun punteggio calcolato —", stili["body"]))
        return out

    rows = [["Sezione", "Punteggio", "Massimo", "Percentuale"]]
    for info in riepilogo.values():
        rows.append([
            info["label"],
            str(info["ottenuto"]),
            str(info["massimo"]),
            f"{info['perc']}%",
        ])
    t = Table(rows, colWidths=[90 * mm, 25 * mm, 25 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    out.append(t)

    out.append(Spacer(1, 6))
    out.append(Paragraph(
        f"<b>Legenda scoring INPP (0–4):</b> {_legenda_scoring_html()}",
        stili["small"],
    ))

    return out


def _build_sezione(stili, sezione: dict, valori: dict):
    """Costruisce la parte del PDF dedicata a una sezione del protocollo."""
    out = []

    titolo = sezione["label"]
    if not sezione.get("no_total"):
        ott, mx = calcola_punteggio_sezione(sezione["id"], valori)
        if mx > 0:
            titolo += f" — punteggio {ott}/{mx}"

    out.append(Paragraph(titolo, stili["h1"]))

    for gruppo in sezione["gruppi"]:
        block = []
        block.append(Paragraph(gruppo["label"], stili["h2"]))

        rows = [["Prova", "Risultato"]]
        for prova in gruppo["prove"]:
            rows.append([prova["label"], _format_value(prova, valori)])

        t = Table(rows, colWidths=[120 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREEN),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_GREEN),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        block.append(t)
        block.append(Spacer(1, 4))

        # Teniamo gruppi piccoli insieme
        if len(rows) <= 12:
            out.append(KeepTogether(block))
        else:
            out.extend(block)

    return out


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def genera_pdf_referto(
    paziente_nome: str,
    data_valutazione,
    terapista: str,
    motivo: str,
    valori: dict,
    riepilogo: dict,
    note_finali: str,
) -> bytes:
    """
    Genera il PDF del referto INPP e lo ritorna come bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Referto INPP — {paziente_nome}",
    )
    stili = _styles()
    story = []

    # Intestazione
    story.extend(_build_intestazione(stili, paziente_nome, data_valutazione, terapista, motivo))
    story.append(Spacer(1, 8))

    # Riepilogo
    story.extend(_build_riepilogo(stili, riepilogo))
    story.append(Spacer(1, 8))

    # Dettaglio per sezione
    story.append(Paragraph("Dettaglio per sezione", stili["h1"]))
    for sezione in PROTOCOLLO_INPP:
        story.extend(_build_sezione(stili, sezione, valori))

    # Note finali
    if note_finali:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Note finali / interpretazione clinica", stili["h1"]))
        story.append(Paragraph(note_finali.replace("\n", "<br/>"), stili["body"]))

    # Firma
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        f"Pagani, {date.today().strftime('%d/%m/%Y')}",
        stili["body"],
    ))
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "<i>Dott. Giuseppe Ferraioli</i>",
        stili["body"],
    ))
    story.append(Paragraph("Psicologo Optometrista Comportamentale", stili["small"]))

    doc.build(story)
    return buf.getvalue()
