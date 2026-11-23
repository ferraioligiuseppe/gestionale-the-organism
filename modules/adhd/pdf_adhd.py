# -*- coding: utf-8 -*-
"""
pdf_adhd.py - Report PDF del modulo ADHD (ReportLab, verde #1D6B44).
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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .catalogo_adhd import (SCALE, PROVE, METRICHE, AVVERTENZA, CRITERI_DISATTENZIONE,
                            CRITERI_IPERATTIVITA)
from .scoring_adhd import ESITO_ADHD_TESTO, BLOCCO_TESTO, riga_prova, sintesi

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

ST = ParagraphStyle("b", fontName=_FONT, fontSize=9.5, leading=13, alignment=TA_JUSTIFY)
ST_C = ParagraphStyle("c", fontName=_FONT, fontSize=8.3, leading=10.5)
ST_CH = ParagraphStyle("ch", parent=ST_C, fontName=_FONT_B, textColor=colors.white)
ST_H1 = ParagraphStyle("h1", fontName=_FONT_B, fontSize=15, leading=19, textColor=VERDE)
ST_H2 = ParagraphStyle("h2", fontName=_FONT_B, fontSize=11.5, leading=14, textColor=VERDE,
                       spaceBefore=9, spaceAfter=4)
ST_S = ParagraphStyle("s", parent=ST, fontSize=7.8, leading=10)


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


def _data(d):
    try:
        return d.astimezone(TZ).strftime("%d/%m/%Y")
    except Exception:
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d or "—")


def genera_pdf(paziente, registrazioni, carta_intestata=None, operatore=None, conclusioni=None):
    """
    paziente: dict con id, nome_completo, data_nascita
    registrazioni: lista da db_adhd.lista (dalla piu' recente)
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
    # foglio intestato a pagina intera (PDF o immagine verticale): ha anche il pie' di pagina
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
            if carta_pagina:     # immagine a pagina intera (foglio intestato): va come sfondo
                c.drawImage(img, 0, 0, width=A4[0], height=A4[1], mask="auto")
            else:                # striscia d'intestazione: in testa alla pagina
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
                            title="Valutazione attenzione e iperattività", author=operatore or "")
    L = 174 * mm
    s = [_p("Valutazione di attenzione, iperattività e autoregolazione", ST_H1), Spacer(1, 3 * mm)]
    s.append(_tab([["Paziente", "Data di nascita", "Data del report", "Operatore"],
                   [paziente.get("nome_completo") or "—", _data(paziente.get("data_nascita")),
                    datetime.now(TZ).strftime("%d/%m/%Y"), operatore or "—"]],
                  [L * .34, L * .2, L * .2, L * .26]))

    sin = sintesi(registrazioni)
    s.append(_p("Quadro d'insieme", ST_H2))
    s.append(_p(sin["testo"]))
    if sin["righe"]:
        s.append(Spacer(1, 2 * mm))
        s.append(_tab([["Area", "Fonte", "Esito"]] + [[a, f, e] for a, f, e, _ in sin["righe"]],
                      [L * .17, L * .3, L * .53]))

    per_cat = {}
    for r in registrazioni:
        per_cat.setdefault(r["categoria"], []).append(r)

    # ------------------------------------------------------------- scale
    if per_cat.get("scala"):
        s.append(_p("Scale di valutazione", ST_H2))
        for r in per_cat["scala"]:
            sc, p = SCALE.get(r["strumento"], {}), r["punteggi"]
            s.append(_p("%s — %s%s" % (sc.get("nome", r["strumento"]), _data(r["data_reg"]),
                                        " — compilata da: %s" % r["informatore"] if r.get("informatore") else ""),
                        ParagraphStyle("x", parent=ST, fontName=_FONT_B)))
            if r["strumento"].startswith("VAND"):
                rows = [["Area", "Risposte «spesso / molto spesso»", "Soglia", "Media item", "Screening"]]
                for nome, d in p.get("blocchi", {}).items():
                    rows.append([BLOCCO_TESTO.get(nome, nome), "%s su %s" % (d["positivi"], d["su"]),
                                 d["soglia"], d["media"] if d["media"] is not None else "—",
                                 "positivo" if d["positivo"] else
                                 ("sintomi sopra soglia" if d["sintomi_sopra_soglia"] else "negativo")])
                s.append(_tab(rows, [L * .26, L * .26, L * .1, L * .14, L * .24]))
                s.append(_p("%s. Aree di rendimento segnate come problema: %s. Item senza risposta: %s." % (
                    ESITO_ADHD_TESTO.get(p.get("esito_adhd"), "—"),
                    len(p.get("rendimento_problema") or []), p.get("mancanti", 0)), ST_S))
            else:
                rows = [["Sottoscala", "Punteggio", "Soglia", "Esito"],
                        ["Totale", p.get("totale"), p.get("soglia_totale"),
                         "sopra soglia" if p.get("totale_sopra_soglia") else "sotto soglia"]]
                for nome, d in (p.get("sottoscale") or {}).items():
                    rows.append([nome, "%s / %s" % (d["punteggio"], d["massimo"]), d["soglia"],
                                 "sopra soglia" if d["sopra_soglia"] else "sotto soglia"])
                s.append(_tab(rows, [L * .4, L * .2, L * .15, L * .25]))
            if r.get("note"):
                s.append(_p("Note: %s" % r["note"], ST_S))
            s.append(Spacer(1, 2.5 * mm))

    # --------------------------------------------------------- checklist
    if per_cat.get("checklist"):
        r = per_cat["checklist"][0]
        p, d = r["punteggi"], r["risposte"]
        s.append(_p("Scheda criteri compilata dal clinico — %s" % _data(r["data_reg"]), ST_H2))
        pres_d = [t for t, ok in zip(CRITERI_DISATTENZIONE, d.get("disattenzione", [])) if ok]
        pres_i = [t for t, ok in zip(CRITERI_IPERATTIVITA, d.get("iperattivita", [])) if ok]
        s.append(_tab([["Dominio", "Presenti", "Quali"],
                       ["Disattenzione", "%s su 9 (soglia %s)" % (p.get("n_disattenzione"), p.get("soglia")),
                        "; ".join(pres_d) or "—"],
                       ["Iperattività / impulsività", "%s su 9 (soglia %s)" % (p.get("n_iperattivita"), p.get("soglia")),
                        "; ".join(pres_i) or "—"]], [L * .22, L * .2, L * .58]))
        s.append(Spacer(1, 1.5 * mm))
        s.append(_tab([["Condizione", "Esito"]] +
                      [[k, "sì" if ok else "no"] for k, ok in (p.get("condizioni") or {}).items()],
                      [L * .8, L * .2]))
        extra = []
        if d.get("contesti"):
            extra.append("Contesti: %s." % ", ".join(d["contesti"]))
        if p.get("criteri_soddisfatti"):
            extra.append("Manifestazione %s%s." % (p.get("manifestazione"),
                                                    ", gravità %s" % d["gravita"].lower() if d.get("gravita") else ""))
        if r.get("note"):
            extra.append("Note: %s" % r["note"])
        if extra:
            s.append(_p(" ".join(extra), ST_S))

    # ------------------------------------------------------------- prove
    if per_cat.get("prova"):
        s.append(_p("Prove a schermo", ST_H2))
        rows = [["Data", "Prova", "Risultato"]]
        for r in reversed(per_cat["prova"]):
            rows.append([_data(r["data_reg"]), PROVE.get(r["strumento"], {}).get("nome", r["strumento"]),
                         riga_prova(r["strumento"], r["punteggi"])])
        s.append(_tab(rows, [L * .13, L * .25, L * .62]))
        s.append(_p("Prove costruite dallo studio su paradigmi sperimentali classici. Non hanno norme "
                    "di riferimento: i valori descrivono la prestazione e servono al confronto del "
                    "paziente con se stesso nel tempo, non a collocarlo rispetto ai coetanei.", ST_S))

    # ----------------------------------------------------------- esterni
    if per_cat.get("esterno"):
        s.append(_p("Test somministrati su materiale originale", ST_H2))
        rows = [["Data", "Test", "Scala / indice", "Punteggio", "z", "Percentile", "Fascia"]]
        for r in reversed(per_cat["esterno"]):
            p = r["punteggi"]
            rows.append([_data(r["data_reg"]), r["strumento"], p.get("scala") or "—",
                         "%s %s" % (p.get("valore"), "" if p.get("metrica") in ("GREZZO",) else
                                    "(%s)" % METRICHE.get(p.get("metrica"), ("",))[0].split(" (")[0].lower()),
                         p.get("z") if p.get("z") is not None else "—",
                         p.get("percentile_manuale") or (p.get("percentile") if p.get("percentile") is not None else "—"),
                         p.get("fascia") or "—"])
        s.append(_tab(rows, [L * .13, L * .19, L * .22, L * .15, L * .07, L * .11, L * .13]))
        s.append(_p("Punteggi calcolati dal clinico sul materiale originale. Dove il percentile non è "
                    "quello riportato dal manuale, è il valore teorico della curva normale.", ST_S))

    if conclusioni:
        s.append(_p("Considerazioni del clinico", ST_H2))
        for par in str(conclusioni).split("\n"):
            if par.strip():
                s.append(_p(par.strip()))

    s.append(Spacer(1, 4 * mm))
    crediti = sorted({SCALE[r["strumento"]]["credito"] for r in per_cat.get("scala", [])
                      if r["strumento"] in SCALE})
    s.append(_p(AVVERTENZA + (" Strumenti: " + " ".join(crediti) if crediti else ""), ST_S))

    doc.build(s, onFirstPage=_pagina, onLaterPages=_pagina)
    pdf = buf.getvalue()
    if carta_is_pdf:
        pdf = _overlay_letterhead(pdf, carta_intestata)
    return pdf
