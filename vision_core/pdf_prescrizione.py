from __future__ import annotations
from io import BytesIO
from typing import Any, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm
import os
import math
from pypdf import PdfReader, PdfWriter

START_UNDER_GREEN_CM = 5.0  # distanza dal bordo superiore (sotto riga verde)

def _clean(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()

def _overlay_on_template(content_pdf_bytes: bytes, template_path: str) -> bytes:
    try:
        if not os.path.exists(template_path):
            return content_pdf_bytes
        r_t = PdfReader(template_path)
        r_c = PdfReader(BytesIO(content_pdf_bytes))
        w = PdfWriter()
        base = r_t.pages[0]
        base.merge_page(r_c.pages[0])
        w.add_page(base)
        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception:
        return content_pdf_bytes

def _draw_semiluna_tabo(c: canvas.Canvas, cx: float, cy: float, r: float, axis: int | None, label: str, mirror: bool = False):
    """Semicerchio TABO 0–180° con tacche + freccia asse.
    mirror=True per OSN (specchio) come da convenzione ottica.
    """
    # forza nero (alcuni template/driver stampanti possono attenuare linee sottili)
    try:
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
    except Exception:
        pass
    # arco + base
    c.setLineWidth(1.4)
    c.arc(cx-r, cy-r, cx+r, cy+r, startAng=0, extent=180)
    c.line(cx-r, cy, cx+r, cy)

    # tacche
    for deg in range(0, 181, 10):
        ang_deg = deg  # TABO: 180 a sinistra, 0 a destra per entrambi
        ang = math.radians(ang_deg)
        x1 = cx + r*math.cos(ang)
        y1 = cy + r*math.sin(ang)
        inner = r - (12 if deg % 30 == 0 else 7)
        x2 = cx + inner*math.cos(ang)
        y2 = cy + inner*math.sin(ang)
        c.setLineWidth(1.0)
        c.line(x1, y1, x2, y2)
        if deg % 30 == 0:
            c.setFont("Helvetica", 7)
            tx = cx + (r+12)*math.cos(ang)
            ty = cy + (r+12)*math.sin(ang)
            c.drawCentredString(tx, ty-2, str(deg))

    # label
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - 15, str(label))

    # freccia asse
    if axis is None:
        return
    try:
        axis_i = int(axis)
    except Exception:
        return

    draw_axis = axis_i  # stessa convenzione per entrambi
    ang = math.radians(draw_axis)

    x_end = cx + (r-10)*math.cos(ang)
    y_end = cy + (r-10)*math.sin(ang)

    c.setLineWidth(2.2)
    c.line(cx, cy, x_end, y_end)

    # punta freccia ben visibile
    ah = 10
    left = ang + math.radians(155)
    right = ang - math.radians(155)
    c.line(x_end, y_end, x_end + ah*math.cos(left), y_end + ah*math.sin(left))
    c.line(x_end, y_end, x_end + ah*math.cos(right), y_end + ah*math.sin(right))
    # valore asse
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy + 6, f"AX {axis_i}°")



def genera_prescrizione_occhiali_bytes(formato: str, dati: Dict[str, Any], with_cirillo: bool = True) -> bytes:
    pagesize = A4 if formato.upper() == "A4" else A5
    W, H = pagesize
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)

    assets = os.path.join(os.path.dirname(__file__), "assets")
    template_a4 = os.path.join(assets, "letterhead_prescrizione_A4.pdf")
    template_a5 = os.path.join(assets, "letterhead_prescrizione_A5.pdf")
    template = template_a4 if formato.upper()=="A4" else template_a5
    has_template = os.path.exists(template)

    # Start sotto riga verde (quota fissa dal bordo superiore)
    y_top = H - (START_UNDER_GREEN_CM*cm if has_template else 3.6*cm)

    if not has_template:
        c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 12)
        c.drawString(2*cm, H-2.6*cm, "PRESCRIZIONE OCCHIALI")

    f_base = 10 if formato.upper()=="A4" else 8.8

    paz = _clean(dati.get("paziente_label"))
    data = _clean(dati.get("data"))
    pd = _clean(dati.get("pd_mm"))

    # Paziente + data più grandi
    y = y_top
    c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 11.5)
    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}")
        y -= 16
    if data:
        c.drawString(2*cm, y, f"Data: {data}")
        y -= 10
    c.setFont("Helvetica", f_base)

    presc = dati.get("prescrizione", {}) or {}
    lont = presc.get("lontano", {}) or {}

    def g(block, eye, k):
        return _clean(((block.get(eye, {}) or {}).get(k)))

    def to_int(s):
        try:
            return int(str(s).strip())
        except Exception:
            return None

    ax_odx = to_int(g(lont, "odx", "ax"))
    ax_osn = to_int(g(lont, "osn", "ax"))

    # Semicerchi (TABO unico, stesso orientamento per entrambi)
    r = 2.4*cm if formato.upper()=="A5" else 3.0*cm
    cy = (y - (2.2*cm if formato.upper()=="A5" else 2.6*cm)) - 1.0*cm
    cx1 = W/2 - (3.2*cm if formato.upper()=="A5" else 4.2*cm)
    cx2 = W/2 + (3.2*cm if formato.upper()=="A5" else 4.2*cm)

    # scritta TABO unica sopra i semicerchi
    c.setFont("Helvetica-Bold", 11 if formato.upper()=="A4" else 10)
    c.drawCentredString(W/2, cy + r + 0.6*cm, "TABO")
    c.setFont("Helvetica", f_base)

    _draw_semiluna_tabo(c, cx1, cy, r, ax_odx, "ODX", mirror=False)
    _draw_semiluna_tabo(c, cx2, cy, r, ax_osn, "OSN", mirror=False)

    # PD al centro tra i due semicerchi
    if pd:
        c.setFont("Helvetica-Bold", 11 if formato.upper()=="A4" else 10)
        c.drawCentredString(W/2, cy + 0.2*cm, f"PD {pd} mm")
        c.setFont("Helvetica", f_base)

    # Tabella "Excel" sotto semicerchi
    inter = presc.get("intermedio", {}) or {}
    vicino = presc.get("vicino", {}) or {}

    def any_eye(block):
        return any(g(block,"odx",k) for k in ["sf","cil","ax"]) or any(g(block,"osn",k) for k in ["sf","cil","ax"])

    y_table_top = cy - (r + (0.8*cm if formato.upper()=="A5" else 1.0*cm))

    x0 = 2.0*cm if formato.upper()=="A4" else 1.6*cm
    table_w = W - 2*x0

    # Colonne: Distanza | SF | CIL | AX | (spazio) | SF | CIL | AX
    col_w_rel = [0.20, 0.13, 0.13, 0.10, 0.06, 0.13, 0.13, 0.10]
    scale = table_w / sum(col_w_rel)
    col_w = [w*scale for w in col_w_rel]

    row_h = 16 if formato.upper()=="A4" else 14
    header_h = 18 if formato.upper()=="A4" else 16

    def cell(x, y_top, w, h, text, bold=False, align="center", border=True):
        c.setLineWidth(0.6)
        if border:
            c.rect(x, y_top-h, w, h, stroke=1, fill=0)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", f_base)
        if align == "left":
            c.drawString(x+3, y_top-h+4, str(text) if text is not None else "")
        else:
            c.drawCentredString(x+w/2, y_top-h+4, str(text) if text is not None else "")

    # Group labels ODX / OSN sopra le rispettive colonne
    c.setFont("Helvetica-Bold", 10.5 if formato.upper()=="A4" else 9.5)
    # calcola centro gruppi
    x = x0
    # Distanza col 0
    x += col_w[0]
    odx_w = col_w[1] + col_w[2] + col_w[3]
    gap_w = col_w[4]
    osn_w = col_w[5] + col_w[6] + col_w[7]
    c.drawCentredString(x + odx_w/2, y_table_top, "ODX")
    c.drawCentredString(x + odx_w + gap_w + osn_w/2, y_table_top, "OSN")
    y_table_top -= 8

    # header row (senza ODX/OSN nei rettangoli)
    headers = ["Distanza", "SF", "CIL", "AX", "", "SF", "CIL", "AX"]
    x = x0
    for htxt, w in zip(headers, col_w):
        if htxt == "":
            cell(x, y_table_top, w, header_h, "", bold=False, border=False)
        else:
            cell(x, y_table_top, w, header_h, htxt, bold=True)
        x += w
    y_table_top -= header_h

    def row_values(label, block, add_val=""):
        if not any_eye(block) and _clean(add_val)=="" :
            return None
        return [
            label,
            g(block,"odx","sf"), g(block,"odx","cil"), g(block,"odx","ax"),
            "",  # gap
            g(block,"osn","sf"), g(block,"osn","cil"), g(block,"osn","ax"),
        ]

    rows = []
    rv = row_values("Lontano", lont)
    if rv: rows.append(rv)
    rv = row_values("Intermedio", inter)
    if rv: rows.append(rv)
    rv = row_values("Vicino", vicino)
    if rv: rows.append(rv)

    add_val = (vicino.get("add","") if isinstance(vicino, dict) else "")
    if _clean(add_val):
        rows.append(["ADD", add_val, "", "", "", "", "", ""])

    for rvals in rows:
        x = x0
        for i, w in enumerate(col_w):
            if i == 4:  # gap column
                cell(x, y_table_top, w, row_h, "", border=False)
            else:
                txtv = rvals[i] if i < len(rvals) else ""
                cell(x, y_table_top, w, row_h, txtv, bold=(i==0))
            x += w
        y_table_top -= row_h
    # Tipo occhiale (elenco verticale con checkbox) + firma a destra (non nel footer)
    opzioni = ["Monofocale", "Progressivo", "Bifocale", "Office/Intermedio", "Da sole", "Altro"]
    selezionati = set([str(x) for x in (dati.get("tipi_selezionati", []) or [])])
    note_tipo = _clean(dati.get("tipo_note"))

    y_box = 4.9*cm if formato.upper()=="A4" else 4.2*cm  # sopra gli indirizzi in carta intestata
    x_box = 2.0*cm
    box = 10  # dimensione checkbox

    c.setFont("Helvetica-Bold", 10.5 if formato.upper()=="A4" else 9.5)
    c.drawString(x_box, y_box + 26, "Tipo occhiale prescritto:")
    c.setFont("Helvetica", f_base)

    y_list = y_box + 10
    for opt in opzioni:
        c.rect(x_box, y_list-2, box, box, stroke=1, fill=0)
        if opt in selezionati:
            c.setFont("Helvetica-Bold", f_base)
            c.drawString(x_box+2, y_list-2, "X")
            c.setFont("Helvetica", f_base)
        c.drawString(x_box + box + 8, y_list, opt)
        y_list -= 14

    if note_tipo:
        c.setFont("Helvetica-Bold", f_base)
        c.drawString(x_box, y_list-2, "Note:")
        c.setFont("Helvetica", f_base)
        c.drawString(x_box + 36, y_list-2, note_tipo[:140])
        y_list -= 14

    # Firma a destra del testo
    x_sig = W - (8.0*cm if formato.upper()=="A4" else 7.0*cm)
    y_sig = y_box + 22
    c.setFont("Helvetica-Bold", f_base)
    c.drawString(x_sig, y_sig, "Firma / Timbro")
    c.setLineWidth(0.8)
    c.line(x_sig, y_sig-6, W-2.0*cm, y_sig-6)

    c.save()
    pdf_bytes = buf.getvalue()
    return _overlay_on_template(pdf_bytes, template)

