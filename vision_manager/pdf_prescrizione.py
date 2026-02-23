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
    """Supporta sia {"od": {...}, "os": {...}} che {"odx": {...}, "osn": {...}}."""
    if not isinstance(rx, dict):
        return {}
    if eye in rx and isinstance(rx.get(eye), dict):
        return rx.get(eye) or {}
    if eye == "od" and isinstance(rx.get("odx"), dict):
        return rx.get("odx") or {}
    if eye == "os" and isinstance(rx.get("osn"), dict):
        return rx.get("osn") or {}
    return {}


def _draw_rx_table(c: canvas.Canvas, x: float, y_top: float, w: float, h_row: float, title: str):
    """Tabella 3 colonne (SF/CIL/AX) + 3 righe (Lontano/Intermedio/Vicino)."""
    col_w = w / 3.0

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + w/2, y_top + 8, title)

    c.setLineWidth(1)
    c.rect(x, y_top - h_row, w, h_row, stroke=1, fill=0)
    c.line(x + col_w, y_top - h_row, x + col_w, y_top)
    c.line(x + 2*col_w, y_top - h_row, x + 2*col_w, y_top)

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + col_w*0.5, y_top - h_row + 6, "SF")
    c.drawCentredString(x + col_w*1.5, y_top - h_row + 6, "CIL")
    c.drawCentredString(x + col_w*2.5, y_top - h_row + 6, "AX")

    for i in range(3):
        y0 = y_top - h_row*(2+i)
        c.rect(x, y0, w, h_row, stroke=1, fill=0)
        c.line(x + col_w, y0, x + col_w, y0 + h_row)
        c.line(x + 2*col_w, y0, x + 2*col_w, y0 + h_row)

    return col_w


def _put_cell_center(c: canvas.Canvas, x: float, y_top: float, col_w: float, h_row: float, row_idx: int, col_idx: int, text: str):
    cell_x = x + col_w*col_idx
    cell_y = y_top - h_row*(2+row_idx)
    c.setFont("Helvetica", 10)
    c.drawCentredString(cell_x + col_w/2, cell_y + h_row/2 - 4, (text or "").strip())


def build_prescrizione_occhiali_a4(data: dict, letterhead_path: str) -> bytes:
    """Prescrizione occhiali A4: layout pulito (no sovrapposizioni)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    try:
        c.drawImage(letterhead_path, 0, 0, width=W, height=H, preserveAspectRatio=True, mask="auto")
    except Exception:
        pass

    x_margin = 2.0 * cm

    # HEADER
    y_title = H - 6.2 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2.0, y_title, "Prescrizione occhiali")

    c.setFont("Helvetica", 11)
    c.drawRightString(W - x_margin, y_title + 2, f"Data: {data.get('data','')}")

    y_sig = H - 7.2 * cm
    c.setFont("Helvetica", 11)
    c.drawString(x_margin, y_sig, "Sig.:")
    c.line(x_margin + 1.3*cm, y_sig - 2, x_margin + 8.5*cm, y_sig - 2)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin + 1.5*cm, y_sig, f"{data.get('paziente','')}")

    # TABO: centrati rispetto alla linea mediana della pagina e spazio centrale per DI
    r = 3.6 * cm
    cy = (H - 11.2 * cm) - 1.0 * cm  # già sceso di 1 cm

    # spazio centrale per DI (distanza interpupillare) - solo testo con puntini
    di_gap = 4.2 * cm  # spazio totale al centro tra i due semicirchi (testo DI)
    cx_mid = W / 2.0
    cx_od = cx_mid - (di_gap / 2.0 + r)
    cx_os = cx_mid + (di_gap / 2.0 + r)

    lont = data.get("lontano") or {}
    ax_od = _safe_num(_rx_get(lont, "od").get("ax"), 0.0)
    ax_os = _safe_num(_rx_get(lont, "os").get("ax"), 0.0)

    # Richiesta: scritta TABO solo su OSN
    draw_tabo_semicircle(c, cx=cx_od, cy=cy, r=r, axis_deg=ax_od, label=None, tick_step=5, show_tabo_text=False)
    draw_tabo_semicircle(c, cx=cx_os, cy=cy, r=r, axis_deg=ax_os, label=None, tick_step=5, show_tabo_text=True)

    # Testo DI (senza quadratino) centrato tra i semicirchi
    c.setFont("Helvetica", 10.5)
    c.drawCentredString(cx_mid, cy - 6, "Distanza interpupillare: ................")

    # Tabelle
    table_top = cy - r - 1.0*cm
    table_w = 6.2 * cm
    row_h = 0.9 * cm

    # Centra le due tabelle sulla linea mediana, lasciando un gap centrale per le etichette righe
    label_gap = 2.6 * cm
    total_w = table_w * 2 + label_gap
    x_od = (W - total_w) / 2.0
    x_os = x_od + table_w + label_gap

    col_w = _draw_rx_table(c, x_od, table_top, table_w, row_h, "Occhio Destro")
    _draw_rx_table(c, x_os, table_top, table_w, row_h, "Occhio Sinistro")

    # Etichette righe al centro
    c.setFont("Helvetica-Bold", 9.2)
    mid_x = x_od + table_w + label_gap/2.0
    row_labels = [("LONTANO", 0), ("INTERMEDIO\n(COMPUTER)", 1), ("VICINO\n(LETTURA)", 2)]
    for lab, i in row_labels:
        y_row_center = table_top - row_h*(1.5+i)
        for j, ln in enumerate(lab.split("\n")):
            c.drawCentredString(mid_x, y_row_center - j*10, ln)

    inter = data.get("intermedio") or {}
    vic = data.get("vicino") or {}

    def fill_row(src, row_idx: int):
        od = _rx_get(src, "od")
        os_ = _rx_get(src, "os")

        _put_cell_center(c, x_od, table_top, col_w, row_h, row_idx, 0, str(od.get("sf","")))
        _put_cell_center(c, x_od, table_top, col_w, row_h, row_idx, 1, str(od.get("cyl","")))
        _put_cell_center(c, x_od, table_top, col_w, row_h, row_idx, 2, str(od.get("ax","")))

        _put_cell_center(c, x_os, table_top, col_w, row_h, row_idx, 0, str(os_.get("sf","")))
        _put_cell_center(c, x_os, table_top, col_w, row_h, row_idx, 1, str(os_.get("cyl","")))
        _put_cell_center(c, x_os, table_top, col_w, row_h, row_idx, 2, str(os_.get("ax","")))

    fill_row(lont, 0)
    fill_row(inter, 1)
    fill_row(vic, 2)

    # Lenti
    y_lenti = table_top - row_h*4 - 1.4*cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y_lenti, "LENTI CONSIGLIATE")
    y_lenti -= 0.7*cm

    lenti = data.get("lenti") or []
    c.setFont("Helvetica", 10.5)
    for item in lenti[:10]:
        c.rect(x_margin, y_lenti - 3, 10, 10, stroke=1, fill=0)
        c.drawString(x_margin + 0.5*cm, y_lenti, str(item))
        y_lenti -= 0.55*cm

    c.showPage()
    c.save()
    return buf.getvalue()
