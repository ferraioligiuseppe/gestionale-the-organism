from __future__ import annotations
from io import BytesIO
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def _draw_multiline(c: canvas.Canvas, text: str, x: float, y: float, max_chars=95, line_h=14):
    if not text:
        return y
    words = text.replace("\r", "").split()
    line = ""
    lines = []
    for w in words:
        test = (line + " " + w).strip()
        if len(test) <= max_chars:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_h
    return y

def build_pdf_osteopatia_referto_a4(paziente_label: str, seduta: Dict[str, Any]) -> bytes:
    """
    PDF A4 semplice e pulito.
    Se vuoi intestazione The Organism (logo/margini), possiamo:
    1) disegnare header con immagine, oppure
    2) fare overlay su template PDF A4 esistente.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    x = 2.0 * cm
    y = h - 2.0 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Referto Osteopatia")
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Paziente: {paziente_label}")
    y -= 14
    c.drawString(x, y, f"Data seduta: {seduta.get('data_seduta','')}   |   Tipo: {seduta.get('tipo_seduta','')}")
    y -= 14
    c.drawString(x, y, f"Operatore: {seduta.get('operatore','')}")
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Valutazione pre-trattamento")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Dolore pre: {seduta.get('dolore_pre','')} /10")
    y -= 14
    y = _draw_multiline(c, seduta.get("note_pre",""), x, y)

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Trattamento eseguito")
    y -= 14
    c.setFont("Helvetica", 10)

    tecniche = seduta.get("tecniche") or {}
    if isinstance(tecniche, str):
        import json
        try:
            tecniche = json.loads(tecniche)
        except Exception:
            tecniche = {}

    tech_true = [k for k, v in (tecniche or {}).items() if v]
    c.drawString(x, y, "Tecniche: " + (", ".join(tech_true) if tech_true else "-"))
    y -= 14
    y = _draw_multiline(c, seduta.get("descrizione",""), x, y)

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Esito / post-trattamento")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Dolore post: {seduta.get('dolore_post','')} /10")
    y -= 14
    y = _draw_multiline(c, seduta.get("risposta",""), x, y)
    y = _draw_multiline(c, seduta.get("reazioni",""), x, y)

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Indicazioni domiciliari")
    y -= 14
    c.setFont("Helvetica", 10)
    y = _draw_multiline(c, seduta.get("indicazioni",""), x, y)

    y -= 6
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Piano / prossimo step")
    y -= 14
    c.setFont("Helvetica", 10)
    y = _draw_multiline(c, seduta.get("prossimo_step",""), x, y)

    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(x, y, "Firma operatore: ________________________________")

    c.showPage()
    c.save()
    return buf.getvalue()
