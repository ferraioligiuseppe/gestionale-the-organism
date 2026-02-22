from __future__ import annotations
import math
from reportlab.pdfgen.canvas import Canvas

def draw_axis_semicircle(c: Canvas, cx: float, cy: float, r: float, axis_deg: float):
    """
    Semicerchio TABO corretto:
    180° a sinistra – 0° a destra – 90° in alto
    con scritta TABO centrale e freccia asse.
    """

    # Disegno arco
    c.setLineWidth(1.2)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # Gradi
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, cy + r + 12, "90°")
    c.drawString(cx - r - 18, cy - 3, "180°")
    c.drawString(cx + r + 6,  cy - 3, "0°")

    # Scritta TABO interna
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(cx, cy + r*0.35, "TABO")

    # Conversione asse
    a = float(axis_deg or 0)
    a = max(0.0, min(180.0, a))
    theta = math.radians(a)

    # Punto freccia
    x = cx + r * math.cos(theta)
    y = cy + r * math.sin(theta)

    # Linea asse
    c.setLineWidth(1.6)
    c.line(cx, cy, x, y)

    # Testa freccia grande
    ah = 10
    ang1 = theta + math.radians(150)
    ang2 = theta - math.radians(150)

    c.line(x, y, x + ah * math.cos(ang1), y + ah * math.sin(ang1))
    c.line(x, y, x + ah * math.cos(ang2), y + ah * math.sin(ang2))
