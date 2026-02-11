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
        ang_deg = (180 - deg) if mirror else deg
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
    c.drawCentredString(cx, cy - 15, f"TABO – {label}")

    # freccia asse
    if axis is None:
        return
    try:
        axis_i = int(axis)
    except Exception:
        return

    draw_axis = (180 - axis_i) if mirror else axis_i
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

    # Header solo se non c'è template
    if not has_template:
        c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 12)
        c.drawString(2*cm, H-2.6*cm, "PRESCRIZIONE OCCHIALI")

    # Font base
    f_base = 10 if formato.upper()=="A4" else 8.8
    f_bold = f_base

    paz = _clean(dati.get("paziente_label"))
    data = _clean(dati.get("data"))
    pd = _clean(dati.get("pd_mm"))

    # 1) Paziente + data più grandi (come richiesto)
    y = y_top
    c.setFont("Helvetica-Bold", 13 if formato.upper()=="A4" else 11.5)
    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}")
        y -= 16
    if data:
        c.drawString(2*cm, y, f"Data: {data}")
        y -= 10

    # 2) Semicerchi TABO (ODX/OSN) con PD al centro
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

    r = 2.4*cm if formato.upper()=="A5" else 3.0*cm
    # posizionamento: sotto anagrafica, + spostamento di 1 cm (verso il basso)
    cy = (y - (2.2*cm if formato.upper()=="A5" else 2.6*cm)) - 1.0*cm
    cx1 = W/2 - (3.2*cm if formato.upper()=="A5" else 4.2*cm)
    cx2 = W/2 + (3.2*cm if formato.upper()=="A5" else 4.2*cm)

    _draw_semiluna_tabo(c, cx1, cy, r, ax_odx, "ODX", mirror=False)
    _draw_semiluna_tabo(c, cx2, cy, r, ax_osn, "OSN", mirror=True)

    # PD al centro tra i due semicerchi
    if pd:
        c.setFont("Helvetica-Bold", 11 if formato.upper()=="A4" else 10)
        c.drawCentredString(W/2, cy + 0.2*cm, f"PD {pd} mm")
        c.setFont("Helvetica", f_base)

    # 3) Gradazione sotto i semicerchi, stile "Excel" con rettangoli
    inter = presc.get("intermedio", {}) or {}
    vicino = presc.get("vicino", {}) or {}

    def any_eye(block):
        return any(g(block,"odx",k) for k in ["sf","cil","ax"]) or any(g(block,"osn",k) for k in ["sf","cil","ax"])

    y_table_top = cy - (r + (0.8*cm if formato.upper()=="A5" else 1.0*cm))

    # Disegno tabella a griglia: colonne = Distanza | ODX SF | ODX CIL | ODX AX | OSN SF | OSN CIL | OSN AX
    x0 = 2.0*cm if formato.upper()=="A4" else 1.6*cm
    table_w = W - 2*x0
    # larghezze relative
    col_w = [0.17, 0.14, 0.14, 0.10, 0.14, 0.14, 0.10]  # somma 0.93, resto a margine interno
    scale = table_w / sum(col_w)
    col_w = [w*scale for w in col_w]

    row_h = 16 if formato.upper()=="A4" else 14
    header_h = 18 if formato.upper()=="A4" else 16

    # helper per rettangolo cella + testo centrato
    def cell(x, y_top, w, h, text, bold=False, align="center"):
        c.setLineWidth(0.6)
        c.rect(x, y_top-h, w, h, stroke=1, fill=0)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", f_base if not bold else f_base)
        if align == "left":
            c.drawString(x+3, y_top-h+4, str(text) if text is not None else "")
        else:
            c.drawCentredString(x+w/2, y_top-h+4, str(text) if text is not None else "")

    # Titolo tabella
    c.setFont("Helvetica-Bold", 11 if formato.upper()=="A4" else 10)
    c.drawString(x0, y_table_top, "Gradazione")
    y_table_top -= 8

    # header row
    headers = ["Distanza", "ODX SF", "ODX CIL", "ODX AX", "OSN SF", "OSN CIL", "OSN AX"]
    x = x0
    for htxt, w in zip(headers, col_w):
        cell(x, y_table_top, w, header_h, htxt, bold=True)
        x += w
    y_table_top -= header_h

    def row_values(label, block, add_val=""):
        # always show if any filled, otherwise skip (come prima)
        if not any_eye(block) and _clean(add_val)=="" :
            return None
        return [
            label,
            g(block,"odx","sf"), g(block,"odx","cil"), g(block,"odx","ax"),
            g(block,"osn","sf"), g(block,"osn","cil"), g(block,"osn","ax"),
        ]

    rows = []
    rv = row_values("Lontano", lont)
    if rv: rows.append(rv)
    rv = row_values("Intermedio", inter)
    if rv: rows.append(rv)
    rv = row_values("Vicino", vicino)
    if rv: rows.append(rv)
        # ADD in riga separata se presente
    add_val = (vicino.get("add","") if isinstance(vicino, dict) else "")
    if _clean(add_val):
        rows.append(["ADD", add_val, "", "", "", "", ""])

    # draw rows
    for rvals in rows:
        x = x0
        for i, w in enumerate(col_w):
            txtv = rvals[i] if i < len(rvals) else ""
            cell(x, y_table_top, w, row_h, txtv, bold=(i==0))
            x += w
        y_table_top -= row_h

    # 4) Tipo occhiale in fondo pagina
    tipi = dati.get("tipi_selezionati", []) or []
    note_tipo = _clean(dati.get("tipo_note"))
    tipo_txt = ", ".join([str(x) for x in tipi]) if tipi else ""
    if note_tipo:
        tipo_txt = (tipo_txt + " – " if tipo_txt else "") + note_tipo

    # area bassa
    y_tipo = 4.4*cm if formato.upper()=="A4" else 3.8*cm
    if tipo_txt:
        c.setFont("Helvetica-Bold", 10.5 if formato.upper()=="A4" else 9.5)
        c.drawString(2*cm, y_tipo+12, "Tipo occhiale prescritto:")
        c.setFont("Helvetica", f_base)
        c.drawString(2*cm, y_tipo, tipo_txt[:190])

    c.setFont("Helvetica", f_base)
    c.drawString(2*cm, 2.0*cm, "Firma e Timbro")

    c.save()
    pdf_bytes = buf.getvalue()
    return _overlay_on_template(pdf_bytes, template)

