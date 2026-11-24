# -*- coding: utf-8 -*-
"""
pdf_raven.py - Relazione PDF delle Matrici di Raven (ReportLab, verde #1D6B44).
carta_intestata: None, percorso/bytes di un PDF (sovrapposto come sfondo)
o di un'immagine PNG/JPG (posata in testa alla pagina).
"""
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .catalogo_raven import FORME
from .scoring_raven import eta_testo

TZ = ZoneInfo("Europe/Rome")
VERDE = colors.HexColor("#1D6B44")
VERDE_CHIARO = colors.HexColor("#E8F1EC")

_FONT, _FONT_B = "Helvetica", "Helvetica-Bold"
for reg, bold in [("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]:
    if os.path.exists(reg) and os.path.exists(bold):
        try:
            pdfmetrics.registerFont(TTFont("PNEV", reg))
            pdfmetrics.registerFont(TTFont("PNEV-B", bold))
            _FONT, _FONT_B = "PNEV", "PNEV-B"
        except Exception:
            pass

ST = ParagraphStyle("rb", fontName=_FONT, fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
ST_C = ParagraphStyle("rc", fontName=_FONT, fontSize=8.5, leading=11)
ST_CH = ParagraphStyle("rch", parent=ST_C, fontName=_FONT_B, textColor=colors.white)
ST_H1 = ParagraphStyle("rh1", fontName=_FONT_B, fontSize=15, leading=19, textColor=VERDE)
ST_H2 = ParagraphStyle("rh2", fontName=_FONT_B, fontSize=11.5, leading=14, textColor=VERDE,
                       spaceBefore=9, spaceAfter=4)
ST_F = ParagraphStyle("rf", fontName=_FONT, fontSize=9.5, leading=13)


def _p(testo, stile=ST):
    return Paragraph(escape(str(testo if testo is not None else "—")), stile)


def _tab(rows, widths):
    data = [[_p(c, ST_CH) for c in rows[0]]] + [[_p(c, ST_C) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERDE_CHIARO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9DBFAC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


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


def _scarto(v):
    return "0" if not v else "%+d" % v


def _data(d):
    try:
        return d.astimezone(TZ).strftime("%d/%m/%Y")
    except Exception:
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d or "—")


def genera_pdf(paziente, registrazione, carta_intestata=None, operatore=None):
    """
    paziente: dict con id, nome_completo, data_nascita
    registrazione: una riga di db_raven.lista (usa il testo di 'relazione' cosi' com'e' salvato)
    Ritorna bytes del PDF.
    """
    ris = registrazione.get("punteggi") or {}
    forma = registrazione["forma"]
    f = FORME[forma]

    carta_is_pdf, carta_img = False, None
    if carta_intestata is not None:
        head = carta_intestata[:4] if isinstance(carta_intestata, (bytes, bytearray)) \
            else open(carta_intestata, "rb").read(4)
        carta_is_pdf = head == b"%PDF"
        if not carta_is_pdf:
            carta_img = carta_intestata
    top = 42 * mm if carta_intestata is not None else 20 * mm
    carta_pagina = carta_is_pdf
    if carta_img is not None:
        try:
            from reportlab.lib.utils import ImageReader
            w0, h0 = ImageReader(io.BytesIO(carta_img) if isinstance(carta_img, (bytes, bytearray))
                                 else carta_img).getSize()
            carta_pagina = h0 > 1.2 * w0
        except Exception:
            carta_img = None
    fondo = 34 * mm if carta_pagina else 18 * mm

    def _pagina(c, doc):
        c.saveState()
        if carta_img is not None:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(io.BytesIO(carta_img) if isinstance(carta_img, (bytes, bytearray)) else carta_img)
            if carta_pagina:
                c.drawImage(img, 0, 0, width=A4[0], height=A4[1], mask="auto")
            else:
                c.drawImage(img, 18 * mm, A4[1] - 36 * mm, width=174 * mm, height=28 * mm,
                            preserveAspectRatio=True, anchor="nw", mask="auto")
        elif not carta_is_pdf:
            c.setStrokeColor(VERDE); c.setLineWidth(2)
            c.line(18 * mm, A4[1] - 12 * mm, 192 * mm, A4[1] - 12 * mm)
            c.setFont(_FONT_B, 8); c.setFillColor(VERDE)
            c.drawString(18 * mm, A4[1] - 10 * mm, "METODO PNEV · Psico-Neuro-Evolutivo")
        c.setFont(_FONT, 7); c.setFillColor(colors.grey)
        c.drawRightString(192 * mm, fondo - 6 * mm, "pag. %s" % doc.page)
        c.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=top, bottomMargin=fondo,
                            title="Matrici di Raven - %s" % f["breve"], author=operatore or "")
    L = 174 * mm
    s = [_p(f["nome"], ST_H1), Spacer(1, 3 * mm)]
    s.append(_tab([["Paziente", "Data di nascita", "Data della prova", "Età alla prova"],
                   [paziente.get("nome_completo") or "—", _data(paziente.get("data_nascita")),
                    _data(registrazione.get("data_reg")), eta_testo(ris.get("eta_mesi"))]],
                  [L * .34, L * .2, L * .2, L * .26]))

    s.append(_p("Punteggi", ST_H2))
    comp = ris.get("composizione")
    testa = ["Serie", "Risposte corrette", "Su"]
    if comp:
        testa += ["Atteso per questo totale", "Scarto"]
    rows = [testa]
    for nome in f["serie"]:
        r = [nome, (ris.get("serie") or {}).get(nome, "—"), f["item"]]
        if comp:
            r += [comp["attesi"].get(nome, "—"), _scarto(comp["scarti"].get(nome, 0))]
        rows.append(r)
    rows.append(["Totale", ris.get("totale", "—"), ris.get("massimo", "—")] + (["", ""] if comp else []))
    s.append(_tab(rows, [L * .2] * len(testa)))
    s.append(Spacer(1, 2 * mm))
    if ris.get("grado"):
        s.append(_p("Collocazione: %s — grado %s (%s)." % (ris["fascia"], ris["grado"], ris["lettura"]), ST_F))
    else:
        s.append(_p("Collocazione normativa: non calcolata%s." % (
            " (%s)" % ris["motivo_senza_norma"] if ris.get("motivo_senza_norma") else ""), ST_F))

    s.append(_p("Relazione", ST_H2))
    for par in str(registrazione.get("relazione") or "").split("\n"):
        if par.strip():
            s.append(_p(par.strip()))

    s.append(Spacer(1, 7 * mm))
    firma = Table([[_p("Data: %s" % datetime.now(TZ).strftime("%d/%m/%Y"), ST_F), _p("Il professionista", ST_F)],
                   ["", _p("______________________________", ST_F)]],
                  colWidths=[L * .55, L * .45], rowHeights=[None, 12 * mm])
    firma.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    s.append(KeepTogether([firma]))

    doc.build(s, onFirstPage=_pagina, onLaterPages=_pagina)
    pdf = buf.getvalue()
    if carta_is_pdf:
        pdf = _overlay_letterhead(pdf, carta_intestata)
    return pdf
