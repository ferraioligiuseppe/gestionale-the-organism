"""
pei_core.pdf_io — tutto ciò che riguarda i FILE PDF:
  1. genera_pdf()       -> esporta un Documento in PDF (ReportLab)
  2. leggi_allegato()   -> valida un PDF caricato, calcola hash, estrae testo
  3. unisci_pdf()       -> PDF generato + allegati originali in un unico file

intestazione: callback opzionale (canvas, doc) per la carta intestata
del gestionale; nel TFA Manager si lascia None.
"""
from __future__ import annotations

import hashlib
import io
from datetime import date, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from .model import Documento

VERDE = colors.HexColor("#1D6B44")
VERDE_CHIARO = colors.HexColor("#E8F2EC")
MAX_ALLEGATO_MB = 15


def _stili():
    s = getSampleStyleSheet()
    return {
        "titolo": ParagraphStyle("t", parent=s["Title"], textColor=VERDE, fontSize=17, spaceAfter=4),
        "sotto": ParagraphStyle("st", parent=s["Normal"], fontSize=9.5, textColor=colors.grey,
                                alignment=1, spaceAfter=10),
        "sez": ParagraphStyle("sez", parent=s["Heading2"], textColor=colors.white, fontSize=11.5,
                              backColor=VERDE, borderPadding=(4, 5, 4, 5), spaceBefore=12, spaceAfter=8),
        "etichetta": ParagraphStyle("e", parent=s["Normal"], fontName="Helvetica-Bold",
                                    fontSize=9.5, textColor=VERDE),
        "testo": ParagraphStyle("x", parent=s["Normal"], fontSize=10, leading=13.5, alignment=TA_JUSTIFY),
        "cella": ParagraphStyle("c", parent=s["Normal"], fontSize=9.5, leading=12),
        "vuoto": ParagraphStyle("v", parent=s["Normal"], fontSize=9.5, textColor=colors.grey,
                                fontName="Helvetica-Oblique"),
    }


def _formatta(valore, tipo) -> str | None:
    if valore in (None, "", []):
        return None
    if tipo == "number":
        return str(valore)
    if tipo == "checkbox":
        return "Sì" if valore else "No"
    if tipo == "multiselect":
        return "<br/>".join("• " + escape(str(v)) for v in valore)
    if isinstance(valore, (date, datetime)):
        return valore.strftime("%d/%m/%Y")
    if tipo == "date" and isinstance(valore, str) and len(valore) == 10 and valore[4] == "-":
        a, m, g = valore.split("-")
        return f"{g}/{m}/{a}"
    return escape(str(valore)).replace("\n", "<br/>")


def _tabella(campo, righe, st, larghezza=17 * cm):
    cols = campo["opzioni"]
    w = larghezza / len(cols)
    dati = [[Paragraph(escape(campo["label"]), st["etichetta"])] + [""] * (len(cols) - 1),
            [Paragraph(f"<b>{escape(c['label'])}</b>", st["cella"]) for c in cols]]
    for r in righe or [{}]:
        dati.append([Paragraph(escape(str(r.get(c["key"], "") or "")).replace("\n", "<br/>"),
                               st["cella"]) for c in cols])
    t = Table(dati, colWidths=[w] * len(cols), repeatRows=2)
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_CHIARO),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F8F5")),
        ("BOX", (0, 0), (-1, -1), 0.5, VERDE), ("INNERGRID", (0, 1), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _piede(canvas, doc, titolo, anonimo):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    testo = f"{titolo} — pagina {doc.page}"
    if anonimo:
        testo += " — documento anonimizzato"
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, testo)
    canvas.restoreState()


def genera_pdf(doc: Documento, intestazione=None, includi_vuoti: bool = False,
               sottotitolo: str | None = None, margini=None) -> bytes:
    """margini: (alto, destro, basso, sinistro) in punti, per carte intestate
    che occupano anche il piede o i lati della pagina."""
    st = _stili()
    buf = io.BytesIO()
    if margini is None:
        margini = (4.2 * cm if intestazione else 2 * cm, 2 * cm, 2 * cm, 2 * cm)
    alto, destro, basso, sinistro = margini
    pdf = SimpleDocTemplate(buf, pagesize=A4, leftMargin=sinistro, rightMargin=destro,
                            topMargin=alto, bottomMargin=basso, title=doc.titolo)
    larghezza = A4[0] - sinistro - destro

    titolo = doc.titolo + (" — provvisorio" if doc.provvisorio else "")
    story = [Paragraph(escape(titolo), st["titolo"])]
    info = [p for p in (doc.contenuto.get("soggetto"), doc.anno_scolastico
                        or doc.contenuto.get("anno_scolastico")) if p]
    if sottotitolo:
        info.append(sottotitolo)
    if info:
        story.append(Paragraph(escape(" · ".join(map(str, info))), st["sotto"]))

    for sez in doc.sezioni():
        blocchi = []
        for campo in sez["campi"]:
            if campo["tipo"] == "tabella":
                righe = [r for r in (doc.contenuto.get(campo["key"]) or [])
                         if any(str(v).strip() for v in r.values())]
                if not righe and not includi_vuoti:
                    continue
                blocchi += [_tabella(campo, righe, st, larghezza), Spacer(1, 6)]
                continue
            val = _formatta(doc.contenuto.get(campo["key"]), campo["tipo"])
            if val is None and not includi_vuoti:
                continue
            corpo = Paragraph(val, st["testo"]) if val else Paragraph("non compilato", st["vuoto"])
            t = Table([[Paragraph(escape(campo["label"]), st["etichetta"])], [corpo]],
                      colWidths=[larghezza])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), VERDE_CHIARO),
                ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            blocchi += [t, Spacer(1, 6)]
        if blocchi:
            story.append(KeepTogether([Paragraph(escape(sez["titolo"]), st["sez"])] + blocchi[:2]))
            story += blocchi[2:]

    def on_page(c, d):
        if intestazione:
            intestazione(c, d)
        _piede(c, d, doc.titolo, doc.anonimo)

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


# --------------------------------------------------------------------------
# Allegati PDF caricati (DF, PDF, PEI della scuola, ecc.)
# --------------------------------------------------------------------------
def leggi_allegato(dati: bytes, nome_file: str) -> dict:
    """Valida e descrive un PDF caricato. Solleva ValueError se non valido."""
    from pypdf import PdfReader

    if not dati.startswith(b"%PDF"):
        raise ValueError("Il file non è un PDF valido.")
    if len(dati) > MAX_ALLEGATO_MB * 1024 * 1024:
        raise ValueError(f"File oltre {MAX_ALLEGATO_MB} MB.")
    reader = PdfReader(io.BytesIO(dati))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("PDF protetto da password: rimuovi la protezione e ricarica.")
    testo = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    return {
        "nome_file": nome_file,
        "sha256": hashlib.sha256(dati).hexdigest(),
        "dimensione": len(dati),
        "pagine": len(reader.pages),
        "testo_estratto": testo,
        "scansione": len(testo) < 30 * len(reader.pages),  # poco testo = probabile scansione
    }


def unisci_pdf(principale: bytes, allegati: list[bytes]) -> bytes:
    from pypdf import PdfReader, PdfWriter

    w = PdfWriter()
    for blob in [principale, *allegati]:
        for pagina in PdfReader(io.BytesIO(blob)).pages:
            w.add_page(pagina)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
