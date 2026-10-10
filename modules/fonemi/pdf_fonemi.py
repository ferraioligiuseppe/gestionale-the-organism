# -*- coding: utf-8 -*-
"""
pdf_fonemi.py - Report PDF dell'impostazione fonemi (ReportLab, verde #1D6B44).
carta_intestata: None, percorso/bytes di un PDF (sovrapposto come sfondo)
o di un'immagine PNG/JPG (posata in testa alla pagina).
"""
import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, KeepTogether)
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Circle

from .catalogo_fonemi import FONEMI, LIVELLI, APPOGGI_LABEL, CRITERIO_PERC

TZ = ZoneInfo("Europe/Rome")
VERDE = colors.HexColor("#1D6B44")
VERDE_CHIARO = colors.HexColor("#E8F1EC")

_FONT, _FONT_B = "Helvetica", "Helvetica-Bold"
for reg, bold in [("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]:
    if os.path.exists(reg) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("PNEV", reg))
        pdfmetrics.registerFont(TTFont("PNEV-B", bold))
        _FONT, _FONT_B = "PNEV", "PNEV-B"   # serve per i simboli IPA (ʃ ɲ ʎ)

ST = ParagraphStyle("b", fontName=_FONT, fontSize=9.5, leading=13, alignment=TA_JUSTIFY)
ST_C = ParagraphStyle("c", fontName=_FONT, fontSize=8.3, leading=10.5)
ST_CH = ParagraphStyle("ch", parent=ST_C, fontName=_FONT_B, textColor=colors.white)
ST_H1 = ParagraphStyle("h1", fontName=_FONT_B, fontSize=15, leading=19, textColor=VERDE)
ST_H2 = ParagraphStyle("h2", fontName=_FONT_B, fontSize=11.5, leading=14, textColor=VERDE,
                       spaceBefore=9, spaceAfter=4)
ST_S = ParagraphStyle("s", parent=ST, fontSize=7.8, leading=10)


def _tab(rows, widths):
    data = [[Paragraph(str(c), ST_CH) for c in rows[0]]] + \
           [[Paragraph(str(c), ST_C) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERDE_CHIARO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9DBFAC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def _grafico(righe, larg=170 * mm, alt=45 * mm):
    """Accuratezza % per seduta, con livello annotato sul punto."""
    d = Drawing(larg, alt)
    x0, y0, w, h = 22, 14, larg - 32, alt - 24
    d.add(Line(x0, y0, x0 + w, y0, strokeColor=colors.grey))
    d.add(Line(x0, y0, x0, y0 + h, strokeColor=colors.grey))
    for v in (0, 50, 100):
        y = y0 + h * v / 100
        d.add(String(2, y - 3, f"{v}%", fontName=_FONT, fontSize=6.5))
    ys = y0 + h * CRITERIO_PERC / 100
    d.add(Line(x0, ys, x0 + w, ys, strokeColor=colors.HexColor("#C9A227"),
               strokeDashArray=[3, 2], strokeWidth=0.7))
    n = len(righe)
    if not n:
        return d
    pts = []
    for i, r in enumerate(righe):
        x = x0 + (w * (i + 0.5) / n)
        y = y0 + h * r["perc"] / 100
        pts += [x, y]
        d.add(Circle(x, y, 2.2, fillColor=VERDE, strokeColor=VERDE))
        d.add(String(x - 3, y + 4, f"L{r['livello']}", fontName=_FONT, fontSize=6))
        if n <= 14:
            d.add(String(x - 10, y0 - 9, r["data_seduta"].astimezone(TZ).strftime("%d/%m"),
                         fontName=_FONT, fontSize=6))
    if n > 1:
        d.add(PolyLine(pts, strokeColor=VERDE, strokeWidth=1.2))
    return d


def _overlay_letterhead(pdf_bytes, carta):
    from pypdf import PdfReader, PdfWriter
    raw = carta if isinstance(carta, (bytes, bytearray)) else open(carta, "rb").read()
    sfondo = PdfReader(io.BytesIO(raw)).pages[0]
    out = PdfWriter()
    for p in PdfReader(io.BytesIO(pdf_bytes)).pages:
        base = PdfWriter().add_blank_page(width=p.mediabox.width, height=p.mediabox.height)
        base.merge_page(sfondo)
        base.merge_page(p)
        out.add_page(base)
    buf = io.BytesIO()
    out.write(buf)
    return buf.getvalue()


def genera_pdf(paziente, obiettivi, storico, carta_intestata=None, operatore=None):
    """
    paziente: dict con id, nome_completo, data_nascita
    obiettivi: lista da db_fonemi.lista_obiettivi
    storico: lista da db_fonemi.storico_prove
    Ritorna bytes del PDF.
    """
    carta_is_pdf, carta_img = False, None
    if carta_intestata is not None:
        head = carta_intestata[:4] if isinstance(carta_intestata, (bytes, bytearray)) \
            else open(carta_intestata, "rb").read(4)
        carta_is_pdf = head == b"%PDF"
        if not carta_is_pdf:
            carta_img = carta_intestata

    top = 42 * mm if carta_intestata is not None else 20 * mm

    def _pagina(c, doc):
        c.saveState()
        if carta_img is not None:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(io.BytesIO(carta_img) if isinstance(carta_img, (bytes, bytearray)) else carta_img)
            c.drawImage(img, 18 * mm, A4[1] - 36 * mm, width=174 * mm, height=28 * mm,
                        preserveAspectRatio=True, anchor="nw", mask="auto")
        elif not carta_is_pdf:
            c.setStrokeColor(VERDE); c.setLineWidth(2)
            c.line(18 * mm, A4[1] - 12 * mm, 192 * mm, A4[1] - 12 * mm)
            c.setFont(_FONT_B, 8); c.setFillColor(VERDE)
            c.drawString(18 * mm, A4[1] - 10 * mm, "METODO PNEV · Psico-Neuro-Evolutivo")
        c.setFont(_FONT, 7); c.setFillColor(colors.grey)
        c.drawRightString(192 * mm, 10 * mm, f"pag. {doc.page}")
        c.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=top, bottomMargin=18 * mm,
                            title="Impostazione fonemi - report", author="Studio The Organism")
    s = [Paragraph("Impostazione fonemi — andamento del trattamento", ST_H1), Spacer(1, 4)]
    dn = paziente.get("data_nascita")
    dn = dn.strftime("%d/%m/%Y") if hasattr(dn, "strftime") else (dn or "-")
    s.append(Paragraph(
        f"<b>Paziente:</b> {paziente.get('nome_completo', '-')} &nbsp;&nbsp; "
        f"<b>Data di nascita:</b> {dn} &nbsp;&nbsp; "
        f"<b>Data report:</b> {datetime.now(TZ).strftime('%d/%m/%Y')}", ST))
    if operatore:
        s.append(Paragraph(f"<b>Operatore:</b> {operatore}", ST))

    # riepilogo obiettivi
    s.append(Paragraph("Obiettivi fonetici", ST_H2))
    rows = [["Fonema", "Punto / modo", "Livello attuale", "Stato", "Ultima accuratezza"]]
    for o in obiettivi:
        f = FONEMI[o["fonema"]]
        ult = [r for r in storico if r["obiettivo_id"] == o["id"]]
        acc = f"{ult[-1]['perc']}% (L{ult[-1]['livello']})" if ult else "-"
        rows.append([f["simbolo"], f["punto_modo"],
                     f"{o['livello']} · {LIVELLI[o['livello']][0]}", o["stato"], acc])
    s.append(_tab(rows, [18 * mm, 48 * mm, 46 * mm, 22 * mm, 40 * mm]))

    # dettaglio per fonema
    for o in obiettivi:
        ult = [r for r in storico if r["obiettivo_id"] == o["id"]]
        if not ult:
            continue
        f = FONEMI[o["fonema"]]
        blocco = [Paragraph(f"{f['simbolo']} — {f['punto_modo']}", ST_H2),
                  Paragraph(f"<b>Facilitazione:</b> {f['facilitazione']}. "
                            f"<b>Appoggio:</b> {f['appoggio']}.", ST_S),
                  Spacer(1, 3), _grafico(ult)]
        det = [["Data", "Livello", "Prove", "Corrette", "%", "Appoggi"]]
        for r in ult:
            det.append([r["data_seduta"].astimezone(TZ).strftime("%d/%m/%Y"),
                        f"{r['livello']} · {LIVELLI[r['livello']][0]}",
                        r["n_prove"], r["n_corrette"], f"{r['perc']}%",
                        ", ".join(APPOGGI_LABEL.get(a, a) for a in r["appoggi"]) or "nessuno"])
        blocco.append(_tab(det, [22 * mm, 40 * mm, 15 * mm, 17 * mm, 15 * mm, 65 * mm]))
        s.append(KeepTogether(blocco[:4]))
        s.append(blocco[4])

    s.append(Spacer(1, 8))
    s.append(Paragraph(
        f"Linea tratteggiata nel grafico: soglia di passaggio al {CRITERIO_PERC}%. "
        "Livelli: 1 stabilità di base · 2 posizione · 3 fonema isolato · 4 sillaba · "
        "5 parola · 6 frase e conversazione. Facilitazioni tattili-cinestesiche "
        "secondo la scheda PNEV (materiale originale, non riproduce il protocollo PROMPT®).", ST_S))

    doc.build(s, onFirstPage=_pagina, onLaterPages=_pagina)
    pdf = buf.getvalue()
    if carta_is_pdf:
        pdf = _overlay_letterhead(pdf, carta_intestata)
    return pdf
