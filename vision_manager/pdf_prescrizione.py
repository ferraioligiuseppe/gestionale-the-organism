from __future__ import annotations

import io
import math
import os
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _fmt_num(x: Any, nd: int = 2) -> str:
    try:
        v = float(x)
    except Exception:
        return ""
    # show sign always for sphere/cyl to look clinical
    s = f"{v:+.{nd}f}"
    # avoid +0.00 clutter
    if abs(v) < 1e-9:
        s = f"{0:.{nd}f}"
    return s


def _fmt_ax(x: Any) -> str:
    try:
        v = int(round(float(x)))
    except Exception:
        return ""
    if v < 0:
        v = 0
    if v > 180:
        v = 180
    return str(v)


def build_prescrizione_occhiali_a4(data: Dict[str, Any], letterhead_path: Optional[str] = None) -> bytes:
    """
    Genera PDF A4 "Prescrizione occhiali" nello stile del canovaccio The Organism.

    Atteso in input (come da Vision Manager):
      data = {
        "data": "YYYY-MM-DD",
        "paziente": "Cognome Nome",
        "lontano": {"od": {"sf":..,"cyl":..,"ax":..}, "os": {...}},
        "intermedio": {"od": {...}, "os": {...}},
        "vicino": {"od": {...}, "os": {...}},
        "lenti": ["Progressive", ...]
      }
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # palette / styles
    green = colors.Color(0 / 255, 150 / 255, 80 / 255)  # The Organism-like green
    dark = colors.black
    lightgray = colors.Color(0.92, 0.92, 0.92)
    midgray = colors.Color(0.85, 0.85, 0.85)

    margin_x = 18 * mm
    top_y = H - 18 * mm

    # optional background/letterhead
    has_letterhead = bool(letterhead_path and os.path.exists(letterhead_path))
    header_h = 35 * mm  # reserved header height when using a letterhead image

    if has_letterhead:
        # draw the letterhead only; do NOT redraw doctor/brand text to avoid duplicates
        try:
            img = ImageReader(letterhead_path)
            iw, ih = img.getSize()
            target_w = W
            # scale letterhead to full page width, but clamp visible height to header_h
            scale = target_w / float(iw)
            target_h = float(ih) * scale
            # draw anchored to top; we let it spill above header_h if needed, but content starts below header_h
            c.drawImage(img, 0, H - target_h, width=target_w, height=target_h, mask="auto")
        except Exception:
            has_letterhead = False  # fallback to drawn header if image fails

    # Header
    if not has_letterhead:
        # header (left)
        c.setFillColor(dark)
        c.setFont("Times-Bold", 12)
        c.drawString(margin_x, top_y, "Dott. Salvatore Adriano Cirillo")
        c.setFont("Times-Bold", 11)
        c.drawString(margin_x, top_y - 14, "Medico Chirurgo")
        c.drawString(margin_x, top_y - 28, "Oculista")

        # header (right) - text fallback (no logo)
        c.setFillColor(green)
        c.setFont("Helvetica", 10)
        c.drawRightString(W - margin_x, top_y - 2, "Studio Associato")
        c.setFont("Helvetica-Bold", 22)
        c.drawRightString(W - margin_x, top_y - 24, "THE")
        c.setFont("Helvetica-Bold", 28)
        c.drawRightString(W - margin_x, top_y - 52, "ORGANISM")
        c.setFillColor(dark)

        # green line under header
        line_y = top_y - 64
        c.setStrokeColor(green)
        c.setLineWidth(1.5)
        c.line(margin_x, line_y, W - margin_x, line_y)
        c.setStrokeColor(dark)
        c.setLineWidth(1)
    else:
        # when letterhead is present, start content below the reserved header area
        line_y = H - 18 * mm - header_h

    # Date & patient lines
    date_str = str(data.get("data") or "").strip()
    paziente = str(data.get("paziente") or "").strip()

    # we draw "boxed" lines in dedicated spaces, avoiding the TABO area.
    y = line_y - 24

    # Compute TABO geometry early (we'll use it to keep header lines clear)
    content_left = margin_x
    content_right = W - margin_x
    content_w = content_right - content_left
    gap = 18 * mm  # central gap (DI space / breathing)
    r_max = (content_w - gap) / 4.0
    r = min(34 * mm, r_max)  # keep TABO compact to avoid overlapping header lines

    mid = W / 2.0
    left_cx = mid - (gap / 2.0 + r)
    right_cx = mid + (gap / 2.0 + r)

    # Place TABO vertically so its top never touches the patient/date lines
    # Patient/date block occupies ~28mm; keep at least 8mm clearance.
    header_clearance = 8 * mm
    tabo_drop = 10 * mm  # requested: push TABO 1 cm lower
    cy = (y - header_clearance) - r - 10*mm - tabo_drop  # keep top clear + extra drop

    c.setFont("Times-Roman", 11)

    # Date (right) -> push further right with a short line
    date_label_x = W - margin_x - 40 * mm
    c.drawString(date_label_x, y, "Data")
    line_x0 = date_label_x + 18 * mm
    line_x1 = W - margin_x
    c.line(line_x0, y - 2, line_x1, y - 2)
    c.drawRightString(line_x1, y, date_str)

    # Patient (left) -> short line that stops BEFORE the left semicircle
    y -= 22
    paz_label = paziente
    if paz_label.lower().startswith("sig."):
        paz_label = paz_label[4:].strip()
    c.drawString(margin_x, y, "Sig.")
    pat_line_x0 = margin_x + 14 * mm
    left_tabo_left = left_cx - r
    pat_line_x1 = min(left_tabo_left - 6 * mm, mid - 20 * mm)
    c.line(pat_line_x0, y - 2, pat_line_x1, y - 2)
    c.drawString(pat_line_x0 + 2 * mm, y, paz_label)

    # TABO semicircles

    def _filled_band(cx, cy, r1, r2, col):
        path = c.beginPath()
        steps = 60
        for i in range(steps + 1):
            ang = math.pi - (math.pi * i / steps)
            x = cx + r2 * math.cos(ang)
            y2 = cy + r2 * math.sin(ang)
            if i == 0:
                path.moveTo(x, y2)
            else:
                path.lineTo(x, y2)
        for i in range(steps + 1):
            ang = 0 + (math.pi * i / steps)
            x = cx + r1 * math.cos(ang)
            y2 = cy + r1 * math.sin(ang)
            path.lineTo(x, y2)
        path.close()
        c.setFillColor(col)
        c.setStrokeColor(col)
        c.drawPath(path, stroke=0, fill=1)
        c.setFillColor(dark)
        c.setStrokeColor(dark)

    def draw_semicircle(cx, cy, r, show_tabo=False):
        # baseline
        c.line(cx - r, cy, cx + r, cy)

        # grey zones
        _filled_band(cx, cy, r * 0.20, r * 0.38, midgray)
        _filled_band(cx, cy, r * 0.38, r * 0.56, lightgray)

        # arc outline
        c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

        # ticks every 5°, long every 30°
        for deg in range(0, 181, 5):
            ang = math.radians(deg)
            x0 = cx + r * math.cos(ang)
            y0 = cy + r * math.sin(ang)
            if deg % 30 == 0:
                tl = 10
            elif deg % 10 == 0:
                tl = 7
            else:
                tl = 4
            x1 = cx + (r - tl) * math.cos(ang)
            y1 = cy + (r - tl) * math.sin(ang)
            c.line(x0, y0, x1, y1)

        # labels
        c.setFont("Helvetica", 7)
        for deg in (0, 30, 60, 90, 120, 150, 180):
            ang = math.radians(deg)
            lx = cx + (r + 6) * math.cos(ang)
            ly = cy + (r + 6) * math.sin(ang)
            c.drawCentredString(lx, ly - 2, str(deg))

        # center dot
        c.circle(cx, cy + 2, 1.2, stroke=1, fill=1)

        if show_tabo:
            c.setFont("Times-Bold", 10)
            c.drawCentredString(cx, cy + r * 0.55, "TABO")

    # cy, left_cx, right_cx, r already computed above (keeps TABO compact and clear of header lines)


    draw_semicircle(left_cx, cy, r, show_tabo=False)
    draw_semicircle(right_cx, cy, r, show_tabo=True)

    c.setFont("Times-Bold", 10)
    c.drawCentredString(left_cx, cy - 12, "Occhio Destro")
    c.drawCentredString(right_cx, cy - 12, "Occhio Sinistro")

    # RX table (3 rows x 3 cols)
    table_top = cy - 24 * mm
    box_w = 48 * mm
    box_h = 8 * mm
    gap_col = 2 * mm
    col_w = (box_w - 2 * gap_col) / 3

    def draw_rx_table(x0, y0, side: str):
        c.setFont("Times-Bold", 8)
        headers = ["SFERO", "CILINDRO", "ASSE"]
        for i, hdr in enumerate(headers):
            c.drawCentredString(x0 + i * (col_w + gap_col) + col_w / 2, y0 + box_h + 3, hdr)

        # rows values: lontano / intermedio / vicino
        lont = (data.get("lontano") or {}).get(side) or {}
        inter = (data.get("intermedio") or {}).get(side) or {}
        vic = (data.get("vicino") or {}).get(side) or {}
        rows = [lont, inter, vic]

        c.setFont("Times-Roman", 9)
        for row_i, rx in enumerate(rows):
            yb = y0 - row_i * (box_h + 5)
            # boxes
            for i in range(3):
                xb = x0 + i * (col_w + gap_col)
                c.rect(xb, yb, col_w, box_h, stroke=1, fill=0)

            # fill text (centered)
            sf = _fmt_num(rx.get("sf", ""))
            cyl = _fmt_num(rx.get("cyl", ""))
            ax = _fmt_ax(rx.get("ax", ""))
            vals = [sf, cyl, ax]
            for i, val in enumerate(vals):
                c.drawCentredString(x0 + i * (col_w + gap_col) + col_w / 2, yb + 2.2, val)

        # prisma/base line placeholders
        y_pr = y0 - 3 * (box_h + 5) - 8
        c.setFont("Times-Bold", 8)
        c.drawString(x0, y_pr, "PRISMA")
        c.drawRightString(x0 + box_w, y_pr, "BASE")
        c.setLineWidth(0.8)
        c.line(x0 + 18, y_pr - 10, x0 + 18, y_pr + 2)
        c.line(x0 + box_w - 18, y_pr - 10, x0 + box_w - 18, y_pr + 2)
        c.setLineWidth(1)

    left_table_x = left_cx - box_w / 2
    right_table_x = right_cx - box_w / 2
    y0 = table_top

    draw_rx_table(left_table_x, y0, "od")
    draw_rx_table(right_table_x, y0, "os")

    # middle distance labels
    mid_x = W / 2
    c.setFont("Times-Roman", 9)
    labels = ["LONTANO", "INTERMEDIO\n(COMPUTER)", "VICINO\n(LETTURA)"]
    for row, lab in enumerate(labels):
        yb = y0 - row * (box_h + 5) + box_h / 2 - 2
        lines = lab.split("\n")
        if len(lines) == 1:
            c.drawCentredString(mid_x, yb, lines[0])
        else:
            c.drawCentredString(mid_x, yb + 4, lines[0])
            c.drawCentredString(mid_x, yb - 6, lines[1])

    # Lenti consigliate list + checkboxes
    lenti_y = y0 - 3 * (box_h + 5) - 30 * mm
    c.setFont("Times-Bold", 9)
    c.drawString(margin_x + 6, lenti_y, "LENTI CONSIGLIATE")
    c.setFont("Times-Roman", 9)

    # left list (as in canovaccio)
    left_items = [
        ("Progressive", "PROGRESSIVE"),
        ("Per vicino/intermedio", "PER VICINO/INTERMEDIO"),
        ("Fotocromatiche", "FOTOCROMATICHE"),
        ("Polarizzate", "POLARIZZATE"),
    ]
    selected = set([str(x) for x in (data.get("lenti") or [])])

    # checkbox primitive (same style used later)
    def _cb(x, y, checked=False):
        c.rect(x, y - 2, 9, 9, stroke=1, fill=0)
        if checked:
            c.setFont("Times-Bold", 10)
            c.drawString(x + 2, y - 1, "✓")
            c.setFont("Times-Roman", 9)

    for i, (key, label) in enumerate(left_items):
        yy = lenti_y - 12 * (i + 1)
        _cb(margin_x + 6, yy, checked=(key in selected))
        c.drawString(margin_x + 20, yy, label)

    # right checkboxes
    cxr = W / 2 + 40 * mm
    ycb = lenti_y - 12

    def checkbox(x, y, label, checked=False):
        c.rect(x, y - 2, 9, 9, stroke=1, fill=0)
        if checked:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 1.5, y - 1.5, "✓")
            c.setFont("Times-Roman", 9)
        c.drawString(x + 14, y, label)

    checkbox(cxr, ycb, "TRATTAMENTO ANTIRIFLESSO", checked=("Trattamento antiriflesso" in selected))
    checkbox(cxr, ycb - 14, "ALTRI TRATTAMENTI", checked=("Altri trattamenti" in selected))
    c.line(cxr, ycb - 26, W - margin_x, ycb - 26)
    c.line(cxr, ycb - 38, W - margin_x, ycb - 38)

    # disclaimer
    disc_y = ycb - 54
    c.setFont("Times-Roman", 8.5)
    c.drawString(
        margin_x + 6,
        disc_y,
        "Correzioni ottenute in base ai dati rifrattometrici e alle indicazioni del paziente nell’esame soggettivo del visus.",
    )
    c.drawString(margin_x + 6, disc_y - 10, "Validità 1 anno.")

    # notes lines
    notes_y = disc_y - 30
    c.setFont("Times-Bold", 9)
    c.drawString(margin_x + 6, notes_y, "NOTE:")
    c.setFont("Times-Roman", 8)
    c.drawString(
        margin_x + 6,
        notes_y - 12,
        "La distanza interpupillare è una delle misure necessarie al montaggio delle lenti e dipende dalle caratteristiche tecnologiche delle lenti consigliate",
    )
    for i in range(3):
        yy = notes_y - 26 - i * 12
        c.line(margin_x + 6, yy, W - margin_x, yy)

    # footer
    foot_y = 18 * mm
    c.setFont("Times-Roman", 8)
    c.drawCentredString(
        W / 2,
        foot_y + 10,
        "Via De Rosa, 46 - 84016 Pagani (SA) - Viale Marconi, 55 p.co Beethoven - 84013 Cava de’ Tirreni (SA)",
    )
    c.drawCentredString(W / 2, foot_y, "Tel. 081 5152334 - Cell. 392 1873914 - studiotheorganism@gmail.com")

    c.showPage()
    c.save()
    return buf.getvalue()
