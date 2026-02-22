from __future__ import annotations
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from .pdf_utils import draw_axis_semicircle

def _rx_line(c, x, y, label, rx):
    if not rx:
        return y
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, label)
    y -= 0.5*cm
    c.setFont("Helvetica", 11)
    od = rx.get("od") or {}
    os_ = rx.get("os") or {}
    c.drawString(x, y, f"OD  SF {od.get('sf','')}  CIL {od.get('cyl','')}  AX {od.get('ax','')}")
    y -= 0.45*cm
    c.drawString(x, y, f"OS  SF {os_.get('sf','')}  CIL {os_.get('cyl','')}  AX {os_.get('ax','')}")
    y -= 0.55*cm
    return y

def build_prescrizione_occhiali_a4(data: dict, letterhead_path: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    try:
        c.drawImage(letterhead_path, 0, 0, width=w, height=h, preserveAspectRatio=True, mask="auto")
    except Exception:
        pass

    x = 2.0*cm
    y = h - 5.6*cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Prescrizione occhiali")
    c.setFont("Helvetica", 11)
    c.drawRightString(w - 2.0*cm, y, f"Data: {data.get('data','')}")
    y -= 1.0*cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, f"Paziente: {data.get('paziente','')}")
    y -= 0.9*cm

    ax_od = ((data.get("lontano") or {}).get("od") or {}).get("ax", 0)
    ax_os = ((data.get("lontano") or {}).get("os") or {}).get("ax", 0)

    cy = y - 2.2*cm
    draw_axis_semicircle(c, cx=x+6.2*cm, cy=cy, r=3.4*cm, axis_deg=float(ax_od or 0), label="OD")
    draw_axis_semicircle(c, cx=x+14.0*cm, cy=cy, r=3.4*cm, axis_deg=float(ax_os or 0), label="OS")
    y -= 6.0*cm

    y = _rx_line(c, x, y, "Lontano", data.get("lontano") or {})
    y = _rx_line(c, x, y, "Intermedio", data.get("intermedio") or {})
    y = _rx_line(c, x, y, "Vicino", data.get("vicino") or {})

    lenti = data.get("lenti") or []
    if lenti:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Tipo di lenti")
        y -= 0.6*cm
        c.setFont("Helvetica", 11)
        for item in lenti:
            c.drawString(x+0.3*cm, y, f"• {item}")
            y -= 0.5*cm

    c.showPage()
    c.save()
    return buf.getvalue()
