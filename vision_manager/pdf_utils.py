from __future__ import annotations
import math
from reportlab.pdfgen.canvas import Canvas

def draw_axis_semicircle(c: Canvas, cx: float, cy: float, r: float, axis_deg: float):
    """Semicerchio Tabo 180°→0° con freccia asse (0..180)."""
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, cy + r + 10, "90°")
    c.drawString(cx - r - 18, cy - 3, "180°/0°")
    c.drawString(cx + r + 4,  cy - 3, "180°/0°")

    a = float(axis_deg or 0)
    a = max(0.0, min(180.0, a))
    theta = math.radians(a)
    x = cx + r * math.cos(theta)
    y = cy + r * math.sin(theta)
    x0 = cx + (r - 12) * math.cos(theta)
    y0 = cy + (r - 12) * math.sin(theta)
    c.line(x0, y0, x, y)
    ah = 6.0
    ang1 = theta + math.radians(150)
    ang2 = theta - math.radians(150)
    c.line(x, y, x + ah * math.cos(ang1), y + ah * math.sin(ang1))
    c.line(x, y, x + ah * math.cos(ang2), y + ah * math.sin(ang2))
