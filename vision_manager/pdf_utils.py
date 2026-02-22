from __future__ import annotations
import math
from typing import Optional
from reportlab.pdfgen.canvas import Canvas

def draw_axis_semicircle(
    c: Canvas,
    cx: float,
    cy: float,
    r: float,
    axis_deg: float,
    label: Optional[str] = None
):
    """
    Semicerchio TABO (180° a sinistra → 0° a destra, 90° in alto) con freccia asse.
    axis_deg: 0..180 (TABO)
    """
    c.setLineWidth(1.4)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, cy + r + 10, "90°")
    c.drawString(cx - r - 18, cy - 4, "180°")
    c.drawString(cx + r + 6,  cy - 4, "0°")

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(cx, cy + r * 0.35, "TABO")

    if label:
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(cx, cy - r - 14, label)

    a = float(axis_deg or 0.0)
    a = max(0.0, min(180.0, a))
    theta = math.radians(a)

    x = cx + r * math.cos(theta)
    y = cy + r * math.sin(theta)

    c.setLineWidth(1.8)
    c.line(cx, cy, x, y)

    ah = 10.0
    ang1 = theta + math.radians(150)
    ang2 = theta - math.radians(150)
    c.line(x, y, x + ah * math.cos(ang1), y + ah * math.sin(ang1))
    c.line(x, y, x + ah * math.cos(ang2), y + ah * math.sin(ang2))
