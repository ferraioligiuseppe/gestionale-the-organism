from __future__ import annotations
from io import BytesIO
from typing import Any, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm, mm
import math

def _clean(v: Any) -> str:
    return "" if v is None else str(v).strip()

def _draw_semiluna_tabo(c: canvas.Canvas, cx: float, cy: float, r: float, axis_deg: int | None, label: str):
    c.setLineWidth(0.8)
    c.arc(cx-r, cy-r, cx+r, cy+r, startAng=0, extent=180)
    c.line(cx-r, cy, cx+r, cy)

    c.setFont("Helvetica", 7)
    for ang in range(0, 181, 30):
        rad = math.radians(ang)
        x1 = cx + r*math.cos(rad)
        y1 = cy + r*math.sin(rad)
        x2 = cx + (r-4*mm)*math.cos(rad)
        y2 = cy + (r-4*mm)*math.sin(rad)
        c.line(x1, y1, x2, y2)
        tx = cx + (r+3*mm)*math.cos(rad)
        ty = cy + (r+3*mm)*math.sin(rad)
        c.drawCentredString(tx, ty-2, str(ang))

    if axis_deg is not None:
        try:
            a = int(axis_deg)
            a = max(0, min(180, a))
            rad = math.radians(a)
            x = cx + (r-2*mm)*math.cos(rad)
            y = cy + (r-2*mm)*math.sin(rad)
            c.setLineWidth(1.2)
            c.line(cx, cy, x, y)
            c.setLineWidth(0.8)
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 10*mm, label)

def genera_prescrizione_occhiali_bytes(formato: str, dati: Dict[str, Any], with_cirillo: bool = True) -> bytes:
    pagesize = A4 if formato.upper() == "A4" else A5
    W, H = pagesize
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)

    c.setFont("Helvetica-Bold", 12 if formato.upper()=="A4" else 11)
    c.drawString(2*cm, H-2.2*cm, "THE ORGANISM – STUDIO CLINICO")
    c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
    intest = "Dott. Giuseppe Ferraioli – Dott. Cirillo" if with_cirillo else "Dott. Giuseppe Ferraioli"
    c.drawString(2*cm, H-2.8*cm, intest)
    c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 12)
    c.drawString(2*cm, H-3.7*cm, "PRESCRIZIONE OCCHIALI")

    y = H-4.8*cm
    c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
    paz = _clean(dati.get("paziente_label"))
    data = _clean(dati.get("data"))
    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}")
        y -= 14
    if data:
        c.drawString(2*cm, y, f"Data: {data}")
        y -= 18

    tipo = _clean(dati.get("tipo_occhiale"))
    if tipo:
        c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
        c.drawString(2*cm, y, f"Tipo occhiale: {tipo}")
        y -= 16
        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)

    def row(label, od, os_):
        nonlocal y
        c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
        c.drawString(2*cm, y, label)
        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
        c.drawString(6.2*cm, y, f"OD  SF {od.get('sf','')}  CIL {od.get('cil','')}  AX {od.get('ax','')}")
        c.drawString(6.2*cm, y-13, f"OS  SF {os_.get('sf','')}  CIL {os_.get('cil','')}  AX {os_.get('ax','')}")
        y -= 30

    presc = dati.get("prescrizione", {})
    lont = presc.get("lontano", {})
    inter = presc.get("intermedio", {})
    vicino = presc.get("vicino", {})

    if lont:
        row("Lontano", lont.get("od", {}), lont.get("os", {}))
    if inter:
        row("Intermedio", inter.get("od", {}), inter.get("os", {}))
    if vicino:
        row("Vicino", vicino.get("od", {}), vicino.get("os", {}))
        add = _clean(vicino.get("add"))
        if add:
            c.drawString(6.2*cm, y+10, f"ADD: {add}")

    if lont and (lont.get("od", {}).get("ax") or lont.get("os", {}).get("ax")):
        ax_od = lont.get("od", {}).get("ax")
        ax_os = lont.get("os", {}).get("ax")
        r = 2.8*cm if formato.upper()=="A4" else 2.3*cm
        cx1 = 4.2*cm
        cx2 = 10.5*cm if formato.upper()=="A4" else 9.2*cm
        cy = 4.2*cm if formato.upper()=="A4" else 3.8*cm
        _draw_semiluna_tabo(c, cx1, cy, r, int(ax_od) if _clean(ax_od) else None, "TABO OD")
        _draw_semiluna_tabo(c, cx2, cy, r, int(ax_os) if _clean(ax_os) else None, "TABO OS")

    c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
    c.drawString(2*cm, 2*cm, "Firma e Timbro")
    c.save()
    return buf.getvalue()
