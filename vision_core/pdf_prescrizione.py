from __future__ import annotations
from io import BytesIO
from typing import Any, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm, mm
import math


from pypdf import PdfReader, PdfWriter
from io import BytesIO
import os

def _overlay_on_template(content_pdf_bytes: bytes, template_path: str) -> bytes:
    try:
        if not os.path.exists(template_path):
            return content_pdf_bytes
        r_t = PdfReader(template_path)
        r_c = PdfReader(BytesIO(content_pdf_bytes))
        w = PdfWriter()
        base = r_t.pages[0]
        overlay = r_c.pages[0]
        base.merge_page(overlay)
        w.add_page(base)
        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception:
        return content_pdf_bytes

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
    """Prescrizione 'da ottico' (A4 consigliato): tabella pulita + 2 semicerchi (ODX/OSN) con freccia asse.

    Nota: se è presente la carta intestata in `vision_core/assets/letterhead_prescrizione_*.pdf`,
    il contenuto viene disegnato più in basso per non coprire l'intestazione.
    """
    pagesize = A4 if formato.upper() == "A4" else A5
    W, H = pagesize
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)

    assets = os.path.join(os.path.dirname(__file__), 'assets')
    template_a4 = os.path.join(assets, 'letterhead_prescrizione_A4.pdf')
    template_a5 = os.path.join(assets, 'letterhead_prescrizione_A5.pdf')
    has_template = os.path.exists(template_a4 if formato.upper()=="A4" else template_a5)

    # Margine superiore (più basso se c'è template)
    top_y = H - (5.4*cm if has_template else 3.6*cm)

    # Header testuale solo se NON c'è template
    if not has_template:
        c.setFont("Helvetica-Bold", 12 if formato.upper()=="A4" else 11)
        c.drawString(2*cm, H-2.2*cm, "THE ORGANISM – STUDIO CLINICO")
        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
        intest = "Dott. Giuseppe Ferraioli – Dott. Cirillo" if with_cirillo else "Dott. Giuseppe Ferraioli"
        c.drawString(2*cm, H-2.8*cm, intest)
        c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 12)
        c.drawString(2*cm, H-3.7*cm, "PRESCRIZIONE OCCHIALI")

    # Anagrafica
    c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
    paz = _clean(dati.get("paziente_label"))
    data = _clean(dati.get("data"))
    y = top_y
    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}")
        y -= 14
    if data:
        c.drawString(2*cm, y, f"Data: {data}")
        y -= 16

    # Tipo occhiale
    tipi = dati.get("tipi_selezionati", []) or []
    note_tipo = _clean(dati.get("tipo_note"))
    if tipi:
        c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
        c.drawString(2*cm, y, "Tipo occhiale:")
        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
        c.drawString(6.2*cm, y, ", ".join([str(x) for x in tipi]))
        y -= 14
    if note_tipo:
        c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
        c.drawString(2*cm, y, "Note lente:")
        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
        c.drawString(6.2*cm, y, note_tipo)
        y -= 18

    # Tabella ottico
    presc = dati.get("prescrizione", {}) or {}
    lont = presc.get("lontano", {}) or {}
    inter = presc.get("intermedio", {}) or {}
    vicino = presc.get("vicino", {}) or {}

    def vref(block, eye, k):
        return _clean(((block.get(eye, {}) or {}).get(k)))

    def has_any(block):
        return any(_clean(vref(block,"odx",k)) or _clean(vref(block,"osn",k)) for k in ["sf","cil","ax"])

    x0 = 2*cm
    col_w = (W - 4*cm) / 3
    x_odx = x0 + col_w
    x_osn = x0 + 2*col_w

    c.setLineWidth(0.8)
    c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
    c.drawString(x0, y, "Distanza")
    c.drawString(x_odx, y, "ODX")
    c.drawString(x_osn, y, "OSN")
    y -= 8
    c.line(2*cm, y, W-2*cm, y)
    y -= 14

    def row(dist_label, block, add_val=""):
        nonlocal y
        if not has_any(block) and _clean(add_val)=="" :
            return
        c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
        c.drawString(x0, y, dist_label)

        c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
        if any(_clean(vref(block,'odx',k)) for k in ["sf","cil","ax"]):
            c.drawString(x_odx, y, f"SF {vref(block,'odx','sf')}  CIL {vref(block,'odx','cil')}  AX {vref(block,'odx','ax')}")
        if any(_clean(vref(block,'osn',k)) for k in ["sf","cil","ax"]):
            c.drawString(x_osn, y, f"SF {vref(block,'osn','sf')}  CIL {vref(block,'osn','cil')}  AX {vref(block,'osn','ax')}")

        y -= 16
        if _clean(add_val):
            c.setFont("Helvetica-Bold", 10 if formato.upper()=="A4" else 9)
            c.drawString(x0, y, "ADD")
            c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
            c.drawString(x_odx, y, _clean(add_val))
            y -= 16
        y -= 4

    row("Lontano", lont)
    row("Intermedio", inter)
    row("Vicino", vicino, add_val=vicino.get("add",""))

    # Due semicerchi per asse (ODX e OSN) – tipico ottico
    ax_odx = vref(lont, "odx", "ax")
    ax_osn = vref(lont, "osn", "ax")

    r = 3.0*cm if formato.upper()=="A4" else 2.4*cm
    cy = max(4.8*cm, y - 2.0*cm)
    cx1 = W/2 - 4.0*cm
    cx2 = W/2 + 4.0*cm

    if _clean(ax_odx) or _clean(ax_osn):
        _draw_semiluna_tabo(c, cx1, cy, r, int(ax_odx) if _clean(ax_odx) else None, "TABO – ODX")
        _draw_semiluna_tabo(c, cx2, cy, r, int(ax_osn) if _clean(ax_osn) else None, "TABO – OSN")

    c.setFont("Helvetica", 10 if formato.upper()=="A4" else 9)
    c.drawString(2*cm, 2*cm, "Firma e Timbro")

    c.save()
    pdf_bytes = buf.getvalue()

    template = template_a4 if formato.upper()=="A4" else template_a5
    return _overlay_on_template(pdf_bytes, template)

