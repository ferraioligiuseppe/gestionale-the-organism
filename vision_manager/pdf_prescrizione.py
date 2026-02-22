from __future__ import annotations
from typing import Dict, Any
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from .pdf_utils import draw_axis_semicircle

def _fmt_rx(rx: Dict[str, Any]) -> str:
    sf = rx.get("sf", "")
    cyl = rx.get("cyl", "")
    ax = rx.get("ax", "")
    def f(v):
        if v is None or v == "": return ""
        try: return f"{float(v):+0.2f}"
        except Exception: return str(v)
    def axf(v):
        if v is None or v == "": return ""
        try: return f"{int(float(v))}°"
        except Exception: return str(v)
    return f"SF {f(sf)}  CIL {f(cyl)}  AX {axf(ax)}"

def build_prescrizione_occhiali_a4(data: Dict[str, Any], letterhead_jpeg_path: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    try:
        c.drawImage(letterhead_jpeg_path, 0, 0, width=w, height=h, mask='auto')
    except Exception:
        pass

    x = 2.2*cm
    y = h - 3.5*cm
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 2.2*cm, y, f"Data: {data.get('data','')}")
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, f"Paziente: {data.get('paziente','')}")
    y -= 28

    ax_od = (data.get("lontano") or {}).get("od", {}).get("ax", 0) or 0
    ax_os = (data.get("lontano") or {}).get("os", {}).get("ax", 0) or 0
    draw_axis_semicircle(c, cx=x+5.2*cm, cy=y-0.5*cm, r=3.3*cm, axis_deg=float(ax_od or 0))
    draw_axis_semicircle(c, cx=x+12.8*cm, cy=y-0.5*cm, r=3.3*cm, axis_deg=float(ax_os or 0))
    y -= 5.2*cm

    def section(title: str, rx_block: Dict[str, Any]):
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, title)
        y -= 16
        c.setFont("Helvetica", 10)
        od = rx_block.get("od", {})
        os_ = rx_block.get("os", {})
        c.drawString(x, y, f"OD: {_fmt_rx(od)}")
        y -= 14
        c.drawString(x, y, f"OS: {_fmt_rx(os_)}")
        y -= 22

    if data.get("lontano"):
        section("LONTANO", data["lontano"])
    if data.get("intermedio"):
        section("INTERMEDIO", data["intermedio"])
    if data.get("vicino"):
        section("VICINO", data["vicino"])

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Lenti consigliate:")
    y -= 14
    c.setFont("Helvetica", 10)
    lenti = data.get("lenti") or []
    for item in lenti:
        c.drawString(x, y, f"[x] {item}")
        y -= 13
    if not lenti:
        c.drawString(x, y, "(nessuna selezionata)")
        y -= 13

    y_sig = 3.3*cm
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 2.2*cm, y_sig + 10, "Firma / Timbro")
    c.line(w - 6.2*cm, y_sig, w - 2.2*cm, y_sig)

    c.showPage()
    c.save()
    return buf.getvalue()
