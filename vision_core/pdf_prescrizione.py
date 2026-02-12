from __future__ import annotations
from io import BytesIO
from typing import Any, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm
import os
import math
from pypdf import PdfReader, PdfWriter

TEMPLATE_TOP_OFFSET_CM = 8.0  # scendi di 7 cm quando c'è carta intestata

def _clean(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()

def _overlay_on_template(content_pdf_bytes: bytes, template_path: str) -> bytes:
    try:
        if not os.path.exists(template_path):
            return content_pdf_bytes
        r_t = PdfReader(template_path)
        r_c = PdfReader(BytesIO(content_pdf_bytes))
        w = PdfWriter()
        base = r_t.pages[0]
        base.merge_page(r_c.pages[0])
        w.add_page(base)
        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception:
        return content_pdf_bytes

def _draw_semiluna_tabo(c: canvas.Canvas, cx: float, cy: float, r: float, axis: int | None, label: str, mirror: bool = False):
    """Semicerchio TABO 0–180° con tacche e freccia asse.
    mirror=True per OSN (specchio), tipico ottico.
    """
    c.setLineWidth(1.0)
    # semicerchio superiore
    c.arc(cx-r, cy-r, cx+r, cy+r, startAng=0, extent=180)
    # linea base
    c.line(cx-r, cy, cx+r, cy)

    # tacche + numeri (ogni 10°, numeri ogni 30°)
    for deg in range(0, 181, 10):
        ang_deg = (180 - deg) if mirror else deg
        ang = math.radians(ang_deg)
        x1 = cx + r*math.cos(ang)
        y1 = cy + r*math.sin(ang)
        inner = r - (10 if deg % 30 == 0 else 6)
        x2 = cx + inner*math.cos(ang)
        y2 = cy + inner*math.sin(ang)
        c.line(x1, y1, x2, y2)
        if deg % 30 == 0:
            c.setFont("Helvetica", 7)
            tx = cx + (r+10)*math.cos(ang)
            ty = cy + (r+10)*math.sin(ang)
            c.drawCentredString(tx, ty-2, str(deg))

    # label
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 14, f"TABO – {label}")

    # freccia asse
    if axis is None:
        return
    try:
        axis_i = int(axis)
    except Exception:
        return

    draw_axis = (180 - axis_i) if mirror else axis_i
    ang = math.radians(draw_axis)
    x_end = cx + (r-8)*math.cos(ang)
    y_end = cy + (r-8)*math.sin(ang)
    c.setLineWidth(1.6)
    c.line(cx, cy, x_end, y_end)

    ah = 7
    left = ang + math.radians(150)
    right = ang - math.radians(150)
    c.line(x_end, y_end, x_end + ah*math.cos(left), y_end + ah*math.sin(left))
    c.line(x_end, y_end, x_end + ah*math.cos(right), y_end + ah*math.sin(right))



def genera_prescrizione_occhiali_bytes(formato: str, dati: Dict[str, Any], with_cirillo: bool = True) -> bytes:
    pagesize = A4 if formato.upper() == "A4" else A5
    W, H = pagesize
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)

    assets = os.path.join(os.path.dirname(__file__), "assets")
    template_a4 = os.path.join(assets, "letterhead_prescrizione_A4.pdf")
    template_a5 = os.path.join(assets, "letterhead_prescrizione_A5.pdf")
    template = template_a4 if formato.upper()=="A4" else template_a5
    has_template = os.path.exists(template)

    # Start Y: scendi di 8cm se template presente (evita copertura intestazione)
    y = H - (3.6*cm + (TEMPLATE_TOP_OFFSET_CM*cm if has_template else 0))

    # Header solo se non c'è template
    if not has_template:
        c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 12)
        c.drawString(2*cm, H-2.6*cm, "PRESCRIZIONE OCCHIALI")

    # Font base
    f_base = 10 if formato.upper()=="A4" else 8.8
    f_bold = f_base
    c.setFont("Helvetica", f_base)

    paz = _clean(dati.get("paziente_label"))
    data = _clean(dati.get("data"))
    pd = _clean(dati.get("pd_mm"))

    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}"); y -= 14
    if data:
        c.drawString(2*cm, y, f"Data: {data}"); y -= 14
    if pd:
        c.drawString(2*cm, y, f"PD: {pd} mm"); y -= 18
    else:
        y -= 6

    # Tipo occhiale (in una riga)
    tipi = dati.get("tipi_selezionati", []) or []
    note_tipo = _clean(dati.get("tipo_note"))
    if tipi:
        c.setFont("Helvetica-Bold", f_bold)
        c.drawString(2*cm, y, "Tipo:")
        c.setFont("Helvetica", f_base)
        c.drawString(3.5*cm, y, ", ".join([str(x) for x in tipi]))
        y -= 14
    if note_tipo:
        c.setFont("Helvetica-Bold", f_bold)
        c.drawString(2*cm, y, "Note:")
        c.setFont("Helvetica", f_base)
        c.drawString(3.5*cm, y, note_tipo[:120])
        y -= 16

    # Dati refrazione
    presc = dati.get("prescrizione", {}) or {}
    lont = presc.get("lontano", {}) or {}
    inter = presc.get("intermedio", {}) or {}
    vicino = presc.get("vicino", {}) or {}

    def g(block, eye, k):
        return _clean(((block.get(eye, {}) or {}).get(k)))

    def any_eye(block):
        return any(g(block,"odx",k) for k in ["sf","cil","ax"]) or any(g(block,"osn",k) for k in ["sf","cil","ax"])

    # Colonne (A4 più larghe; A5 più strette)
    xD = 1.8*cm if formato.upper()=="A5" else 2.0*cm
    xOD = 6.1*cm if formato.upper()=="A5" else 7.2*cm
    xOS = 10.0*cm if formato.upper()=="A5" else 13.2*cm

    c.setLineWidth(0.8)
    c.setFont("Helvetica-Bold", f_bold)
    c.drawString(xD, y, "Distanza")
    c.drawString(xOD, y, "ODX  SF  CIL  AX")
    c.drawString(xOS, y, "OSN  SF  CIL  AX")
    y -= 8
    c.line(xD, y, W - xD, y)
    y -= 12

    c.setFont("Helvetica", f_base)

    def row(label, block, add_val=""):
        nonlocal y
        if not any_eye(block) and _clean(add_val)=="" :
            return
        c.setFont("Helvetica-Bold", f_bold)
        c.drawString(xD, y, label)
        c.setFont("Helvetica", f_base)

        if any(g(block,"odx",k) for k in ["sf","cil","ax"]):
            c.drawString(xOD, y, f"{g(block,'odx','sf')}  {g(block,'odx','cil')}  {g(block,'odx','ax')}")
        if any(g(block,"osn",k) for k in ["sf","cil","ax"]):
            c.drawString(xOS, y, f"{g(block,'osn','sf')}  {g(block,'osn','cil')}  {g(block,'osn','ax')}")
        y -= 16
        if _clean(add_val):
            c.setFont("Helvetica-Bold", f_bold)
            c.drawString(xD, y, "ADD")
            c.setFont("Helvetica", f_base)
            c.drawString(xOD, y, _clean(add_val))
            y -= 16
        y -= 2

    row("Lontano", lont)
    row("Intermedio", inter)
    row("Vicino", vicino, add_val=(vicino.get("add","") if isinstance(vicino, dict) else ""))

    # Semicerchi TABO in basso
    ax_odx = g(lont, "odx", "ax")
    ax_osn = g(lont, "osn", "ax")
    def to_int(s):
        try:
            return int(str(s).strip())
        except Exception:
            return None
    a1 = to_int(ax_odx)
    a2 = to_int(ax_osn)

    r = 2.4*cm if formato.upper()=="A5" else 3.0*cm
    cy = 4.6*cm if formato.upper()=="A5" else 5.6*cm
    dx = 3.2*cm if formato.upper()=="A5" else 4.2*cm
    cx1 = W/2 - dx
    cx2 = W/2 + dx

    if a1 is not None or a2 is not None:
        _draw_semiluna_tabo(c, cx1, cy, r, a1, "ODX", mirror=False)
        _draw_semiluna_tabo(c, cx2, cy, r, a2, "OSN", mirror=True)

    c.setFont("Helvetica", f_base)
    c.drawString(2*cm, 2.0*cm, "Firma e Timbro")

    c.save()
    pdf_bytes = buf.getvalue()
    return _overlay_on_template(pdf_bytes, template)

