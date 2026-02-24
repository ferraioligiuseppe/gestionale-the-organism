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
    show_tabo_text: bool = True,
):
    """Semicerchio TABO stilizzato.

    - 180° a sinistra, 0° a destra, 90° in alto.
    - Tacche ogni `tick_step` gradi (default 5).
    - Etichette a 0/30/60/90/120/150/180.
    - Freccia asse lungo tutto il raggio.
    - show_tabo_text: se False non stampa la scritta 'TABO' (utile se la vuoi solo su OSN).
    """
    # Arco esterno
    c.setLineWidth(1.4)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # Tacche
    for deg in range(0, 181, tick_step):
        theta = math.radians(deg)
        is_major = (deg % 10 == 0)
        is_label = (deg % 30 == 0) or (deg in (0, 90, 180))

        tick_len = r * (0.14 if is_major else 0.08)
        x1 = cx + (r - tick_len) * math.cos(theta)
        y1 = cy + (r - tick_len) * math.sin(theta)
        x2 = cx + r * math.cos(theta)
        y2 = cy + r * math.sin(theta)

        c.setLineWidth(1.15 if is_major else 0.75)
        c.line(x1, y1, x2, y2)

        if is_label:
            lx = cx + (r + 10) * math.cos(theta)
            ly = cy + (r + 10) * math.sin(theta)
            c.setFont("Helvetica", 8.2)
            c.drawCentredString(lx, ly - 3, f"{deg}")

    # Scritta TABO (opzionale)
    if show_tabo_text:
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(cx, cy + r * 0.33, "TABO")

    # Label (opzionale)
    if label:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawCentredString(cx, cy - r - 12, label)

    # Freccia asse
    try:
        a = float(axis_deg or 0.0)
    except Exception:
        a = 0.0
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
