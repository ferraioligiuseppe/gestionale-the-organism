from __future__ import annotations

import math
from typing import Optional
from reportlab.pdfgen.canvas import Canvas


def draw_tabo_semicircle(
    c: Canvas,
    cx: float,
    cy: float,
    r: float,
    axis_deg: float,
    label: Optional[str] = None,
    tick_step: int = 5,
):
    """Disegna un semicerchio TABO più 'stilizzato'.

    - Scala TABO: 180° a sinistra, 0° a destra, 90° in alto.
    - Tacche ogni `tick_step` gradi (default 5).
    - Freccia asse lungo tutto il raggio.
    """
    # arco esterno
    c.setLineWidth(1.4)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # tacche
    for deg in range(0, 181, tick_step):
        theta = math.radians(deg)
        is_major = (deg % 10 == 0)
        is_label = (deg % 30 == 0) or (deg in (0, 90, 180))

        tick_len = r * (0.14 if is_major else 0.08)
        x1 = cx + (r - tick_len) * math.cos(theta)
        y1 = cy + (r - tick_len) * math.sin(theta)
        x2 = cx + r * math.cos(theta)
        y2 = cy + r * math.sin(theta)

        c.setLineWidth(1.2 if is_major else 0.8)
        c.line(x1, y1, x2, y2)

        if is_label:
            # posizione leggermente fuori dall'arco
            lx = cx + (r + 12) * math.cos(theta)
            ly = cy + (r + 12) * math.sin(theta)
            c.setFont("Helvetica", 8.5)
            c.drawCentredString(lx, ly - 3, f"{deg}")

    # scritta TABO
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(cx, cy + r * 0.33, "TABO")

    # label occhio
    if label:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawCentredString(cx, cy - r - 14, label)

    # freccia asse
    try:
        a = float(axis_deg or 0.0)
    except Exception:
        a = 0.0
    a = max(0.0, min(180.0, a))
    theta = math.radians(a)

    # linea fino all'arco
    x = cx + r * math.cos(theta)
    y = cy + r * math.sin(theta)
    c.setLineWidth(1.8)
    c.line(cx, cy, x, y)

    # punta freccia
    ah = 10.0
    ang1 = theta + math.radians(150)
    ang2 = theta - math.radians(150)
    c.line(x, y, x + ah * math.cos(ang1), y + ah * math.sin(ang1))
    c.line(x, y, x + ah * math.cos(ang2), y + ah * math.sin(ang2))
