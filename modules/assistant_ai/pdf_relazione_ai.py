from __future__ import annotations
from io import BytesIO
from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def _ml(c, text: str, x: float, y: float, max_chars=95, line_h=14):
    if not text:
        return y
    words = text.replace("\r","").split()
    line=""
    lines=[]
    for w in words:
        test=(line+" "+w).strip()
        if len(test)<=max_chars:
            line=test
        else:
            if line: lines.append(line)
            line=w
    if line: lines.append(line)
    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_h
    return y

def build_pdf_relazione_ai_a4(rel: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    x = 2*cm
    y = h - 2*cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, rel.get("titolo","Relazione"))
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Professionista: {rel.get('professionista','')}")
    y -= 14
    c.drawString(x, y, f"Paziente: {rel.get('paziente','')}")
    y -= 14
    c.drawString(x, y, f"Periodo: {rel.get('periodo','')}")
    y -= 18

    def section(title, body):
        nonlocal y
        if y < 4*cm:
            c.showPage()
            y = h - 2*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, title)
        y -= 14
        y = _ml(c, body or "Dato non disponibile.", x, y)
        y -= 8

    section("Sintesi", rel.get("sintesi"))
    section("Valutazione iniziale", rel.get("valutazione_iniziale"))
    section("Intervento e progressione", rel.get("intervento_e_progressione"))
    section("Risultati / osservazioni", rel.get("risultati"))
    section("Indicazioni", rel.get("indicazioni"))
    section("Piano / follow-up", rel.get("piano_followup"))
    section("Avvertenze", rel.get("avvertenze"))

    c.showPage()
    c.save()
    return buf.getvalue()
