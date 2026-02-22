from __future__ import annotations

import io
from typing import Any, Dict, Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from vision_manager.pdf_utils import draw_tabo_semicircle


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default


def _rx_get(rx: Optional[Dict[str, Any]], eye: str) -> Dict[str, Any]:
    # supporta sia {"od": {...}, "os": {...}} che {"odx": {...}, "osn": {...}}
    if not isinstance(rx, dict):
        return {}
    if eye in rx and isinstance(rx.get(eye), dict):
        return rx.get(eye) or {}
    # fallback naming
    if eye == "od" and isinstance(rx.get("odx"), dict):
        return rx.get("odx") or {}
    if eye == "os" and isinstance(rx.get("osn"), dict):
        return rx.get("osn") or {}
    return {}


def _draw_rx_grid(c: canvas.Canvas, x: float, y_top: float, col_w: float, row_h: float,
                  header: bool = True):
    # cornice esterna 3 colonne x 3 righe (+ header)
    # header row
    if header:
        c.setLineWidth(1)
        c.rect(x, y_top - row_h, col_w * 3, row_h, stroke=1, fill=0)
        # vertical lines
        c.line(x + col_w, y_top - row_h, x + col_w, y_top)
        c.line(x + 2 * col_w, y_top - row_h, x + 2 * col_w, y_top)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + col_w * 0.5, y_top - row_h + 6, "SFERO")
        c.drawCentredString(x + col_w * 1.5, y_top - row_h + 6, "CILINDRO")
        c.drawCentredString(x + col_w * 2.5, y_top - row_h + 6, "ASSE")

    # 3 righe dati
    y = y_top - row_h
    for i in range(3):
        y0 = y - (i + 1) * row_h
        c.rect(x, y0, col_w * 3, row_h, stroke=1, fill=0)
        c.line(x + col_w, y0, x + col_w, y0 + row_h)
        c.line(x + 2 * col_w, y0, x + 2 * col_w, y0 + row_h)

    return y_top - row_h * 4  # bottom y


def _put_cell(c: canvas.Canvas, x: float, y: float, col_w: float, row_h: float,
              row_idx: int, col_idx: int, text: str):
    # row_idx 0..2 (dati), col_idx 0..2
    # y è y_top (top of header row)
    # header row occupies row 0; data rows start at row 1
    # data row top = y - row_h*(1+row_idx)
    cell_x = x + col_w * col_idx
    cell_y = y - row_h * (2 + row_idx)  # bottom of data row
    c.setFont("Helvetica", 10)
    c.drawCentredString(cell_x + col_w / 2, cell_y + row_h / 2 - 4, text or "")


def build_prescrizione_occhiali_a4(data: dict, letterhead_path: str) -> bytes:
    """Prescrizione occhiali A4 in stile modulo (TABO + griglie SF/CIL/AX)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # letterhead come sfondo (jpeg)
    try:
        c.drawImage(letterhead_path, 0, 0, width=w, height=h, preserveAspectRatio=True, mask="auto")
    except Exception:
        pass

    # titolo e intestazione dati
    x_margin = 2.0 * cm
    y = h - 5.6 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, y, "Prescrizione occhiali")
    c.setFont("Helvetica", 11)
    c.drawRightString(w - x_margin, y, f"Data: {data.get('data','')}")
    y -= 1.0 * cm

    c.setFont("Helvetica", 11)
    c.drawString(x_margin, y, "Sig.:")
    c.line(x_margin + 1.2 * cm, y - 2, w - x_margin, y - 2)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin + 1.4 * cm, y, f"{data.get('paziente','')}")
    y -= 1.1 * cm

    # TABO semicircles (più grandi e freccia lunga)
    # centers
    cy = y - 1.0 * cm
    cx_od = x_margin + 6.3 * cm
    cx_os = x_margin + 14.8 * cm
    r = 3.8 * cm

    lont = data.get("lontano") or {}
    ax_od = _safe_num(_rx_get(lont, "od").get("ax"), 0.0)
    ax_os = _safe_num(_rx_get(lont, "os").get("ax"), 0.0)

    draw_tabo_semicircle(c, cx=cx_od, cy=cy, r=r, axis_deg=ax_od, label="Occhio Destro", tick_step=5)
    draw_tabo_semicircle(c, cx=cx_os, cy=cy, r=r, axis_deg=ax_os, label="Occhio Sinistro", tick_step=5)

    # griglie diottrie sotto i semicirchi
    grid_top = cy - r - 0.3 * cm
    col_w = 2.0 * cm
    row_h = 0.85 * cm

    grid_x_od = x_margin + 2.1 * cm
    grid_x_os = x_margin + 11.0 * cm

    _draw_rx_grid(c, grid_x_od, grid_top, col_w, row_h, header=True)
    _draw_rx_grid(c, grid_x_os, grid_top, col_w, row_h, header=True)

    # etichette righe centrali (LONTANO / INTERMEDIO / VICINO)
    c.setFont("Helvetica-Bold", 9)
    labels = ["LONTANO", "INTERMEDIO\n(COMPUTER)", "VICINO\n(LETTURA)"]
    for i, lab in enumerate(labels):
        ly = grid_top - row_h * (1 + i) - row_h * 0.55
        for j, line in enumerate(lab.split("\n")):
            c.drawCentredString(x_margin + 9.0 * cm, ly - j * 10, line)

    # riempi celle: lontano / intermedio / vicino
    inter = data.get("intermedio") or {}
    vic = data.get("vicino") or {}

    def fill_row(src, row_idx):
        od = _rx_get(src, "od")
        os_ = _rx_get(src, "os")
        # OD
        _put_cell(c, grid_x_od, grid_top, col_w, row_h, row_idx, 0, str(od.get("sf","")))
        _put_cell(c, grid_x_od, grid_top, col_w, row_h, row_idx, 1, str(od.get("cyl","")))
        _put_cell(c, grid_x_od, grid_top, col_w, row_h, row_idx, 2, str(od.get("ax","")))
        # OS
        _put_cell(c, grid_x_os, grid_top, col_w, row_h, row_idx, 0, str(os_.get("sf","")))
        _put_cell(c, grid_x_os, grid_top, col_w, row_h, row_idx, 1, str(os_.get("cyl","")))
        _put_cell(c, grid_x_os, grid_top, col_w, row_h, row_idx, 2, str(os_.get("ax","")))

    fill_row(lont, 0)
    fill_row(inter, 1)
    fill_row(vic, 2)

    # sezione lenti consigliate (semplice elenco)
    y_lenti = grid_top - row_h * 4 - 1.3 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_lenti, "LENTI CONSIGLIATE")
    y_lenti -= 0.6 * cm

    lenti = data.get("lenti") or []
    c.setFont("Helvetica", 10.5)
    for item in lenti[:10]:
        c.rect(x_margin, y_lenti - 3, 10, 10, stroke=1, fill=0)
        c.drawString(x_margin + 0.5 * cm, y_lenti, str(item))
        y_lenti -= 0.55 * cm

    c.showPage()
    c.save()
    return buf.getvalue()
