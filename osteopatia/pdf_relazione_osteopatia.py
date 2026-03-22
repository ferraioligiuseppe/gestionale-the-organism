from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def _draw_title(c, x, y, txt):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, txt)
    return y - 14

def _draw_multiline(c, text: str, x: float, y: float, max_chars=95, line_h=14):
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
    c.setFont("Helvetica", 10)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= line_h
    return y

def build_pdf_relazione_osteopatia_a4(
    paziente_label: str,
    anamnesi: Optional[Dict[str, Any]],
    sedute: List[Dict[str, Any]],
    periodo_label: str = ""
) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    x = 2.0 * cm
    y = h - 2.0 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Relazione Osteopatia")
    y -= 18

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Paziente: {paziente_label}")
    y -= 14
    if periodo_label:
        c.drawString(x, y, f"Periodo: {periodo_label}")
        y -= 14

    y -= 6
    y = _draw_title(c, x, y, "1) Sintesi anamnestica")
    if anamnesi:
        y = _draw_multiline(c, f"Motivo: {anamnesi.get('motivo','')}", x, y)
        y = _draw_multiline(c, f"Dolore: {anamnesi.get('dolore_sede','')} — {anamnesi.get('dolore_intensita','')}/10", x, y)
        y = _draw_multiline(c, f"Valutazione: {anamnesi.get('valutazione','')}", x, y)
        y = _draw_multiline(c, f"Ipotesi: {anamnesi.get('ipotesi','')}", x, y)
    else:
        y = _draw_multiline(c, "Nessuna anamnesi collegata / selezionata.", x, y)

    y -= 10
    y = _draw_title(c, x, y, "2) Percorso sedute (riassunto)")
    if not sedute:
        y = _draw_multiline(c, "Nessuna seduta nel periodo selezionato.", x, y)
    else:
        for s in sedute:
            if y < 4.0 * cm:
                c.showPage()
                x = 2.0 * cm
                y = h - 2.0 * cm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, f"- {s.get('data_seduta','')} | {s.get('tipo_seduta','')} | Operatore: {s.get('operatore','')}")
            y -= 12
            c.setFont("Helvetica", 10)
            dp = s.get("dolore_pre","")
            dpo = s.get("dolore_post","")
            y = _draw_multiline(c, f"Dolore pre/post: {dp} → {dpo}", x+10, y)
            y = _draw_multiline(c, (s.get("descrizione","") or "")[:800], x+10, y)  # taglio per sicurezza
            y = _draw_multiline(c, (s.get("indicazioni","") or "")[:400], x+10, y)
            y -= 6

    y -= 10
    y = _draw_title(c, x, y, "3) Conclusioni e indicazioni")
    y = _draw_multiline(c, "Conclusioni: _________________________________", x, y)
    y = _draw_multiline(c, "Indicazioni: _________________________________", x, y)

    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(x, y, "Firma operatore: ________________________________")

    c.showPage()
    c.save()
    return buf.getvalue()
