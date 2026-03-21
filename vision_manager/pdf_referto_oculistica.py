from __future__ import annotations
from typing import Dict, Any
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from vision_manager.pdf_layout_the_organism import draw_letterhead, draw_professional_block

def _fmt_paziente(p):
    if isinstance(p, dict):
        cog = (p.get("cognome") or "").strip()
        nom = (p.get("nome") or "").strip()
        dn = (p.get("data_nascita") or "").strip()
        s = (cog + " " + nom).strip()
        return (s + (f" ({dn})" if dn else "")).strip() or str(p)
    return str(p or "")


def _clean(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    return True


def _fmt_num(v: Any) -> str:
    try:
        f = float(v)
    except Exception:
        return ""
    if abs(f) < 1e-9:
        return "0.00"
    return f"{f:+.2f}"


def _fmt_ax(v: Any) -> str:
    try:
        return str(int(round(float(v))))
    except Exception:
        return ""


def _ml(c, text: str, x: float, y: float, max_chars=98, line_h=13):
    if not text:
        return y
    chunks = []
    for part in text.split("\n"):
        words = part.replace("\r", "").split()
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if len(test) <= max_chars:
                line = test
            else:
                if line:
                    chunks.append(line)
                line = w
        if line:
            chunks.append(line)
        chunks.append("")
    if chunks and chunks[-1] == "":
        chunks.pop()
    c.setFont("Helvetica", 11)
    for ln in chunks:
        if ln == "":
            y -= line_h // 2
            continue
        c.drawString(x, y, ln)
        y -= line_h
    return y


def _draw_boxed_multiline(c, title: str, text: str, x: float, y_top: float, width: float, min_height: float = 1.5 * cm):
    text = _clean(text)
    if not text:
        return y_top, 0
    line_h = 12
    usable_chars = max(22, int(width / 5.2))
    chunks = []
    for part in text.split("\n"):
        words = part.replace("\r", "").split()
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if len(test) <= usable_chars:
                line = test
            else:
                if line:
                    chunks.append(line)
                line = w
        if line:
            chunks.append(line)
        chunks.append("")
    if chunks and chunks[-1] == "":
        chunks.pop()
    box_h = max(min_height, 12 + len(chunks) * line_h + 8)
    y_bottom = y_top - box_h
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y_top + 2, title)
    c.rect(x, y_bottom, width, box_h, stroke=1, fill=0)
    yy = y_top - 10
    c.setFont("Helvetica", 10)
    for ln in chunks:
        if yy < y_bottom + 8:
            break
        if ln == "":
            yy -= line_h // 2
            continue
        c.drawString(x + 6, yy, ln)
        yy -= line_h
    return y_bottom, box_h


def _build_acuita_body(av: Dict[str, Any]) -> str:
    rows = []
    for k, label in [("naturale", "Naturale"), ("abituale", "Abituale"), ("corretta", "Corretta")]:
        b = av.get(k) or {}
        if not isinstance(b, dict):
            continue
        vals = []
        if _has_value(b.get("od")):
            vals.append(f"OD {b.get('od')}")
        if _has_value(b.get("os")):
            vals.append(f"OS {b.get('os')}")
        if _has_value(b.get("oo")):
            vals.append(f"OO {b.get('oo')}")
        if vals:
            rows.append(f"{label}: " + "   ".join(vals))
    return "\n".join(rows)


def _build_eo_body(eo: Dict[str, Any]) -> str:
    labels = {
        "congiuntiva": "Congiuntiva",
        "cornea": "Cornea",
        "camera_anteriore": "Camera anteriore",
        "cristallino": "Cristallino",
        "vitreo": "Vitreo",
        "fondo_oculare": "Fondo oculare",
        "pressione_endoculare_od": "IOP OD",
        "pressione_endoculare_os": "IOP OS",
        "pachimetria_od": "Pachimetria OD",
        "pachimetria_os": "Pachimetria OS",
    }
    rows = []
    for key, label in labels.items():
        val = eo.get(key)
        if _has_value(val):
            rows.append(f"{label}: {val}")
    return "\n".join(rows)


def _rx_eye_line(label: str, d: Dict[str, Any]) -> str:
    if not isinstance(d, dict):
        return ""
    parts = []
    sf = _fmt_num(d.get("sf"))
    cyl = _fmt_num(d.get("cyl"))
    ax = _fmt_ax(d.get("ax"))
    if sf:
        parts.append(f"SF {sf}")
    if cyl:
        parts.append(f"CIL {cyl}")
    if ax:
        parts.append(f"AX {ax}")
    if not parts:
        return ""
    return f"{label}: " + "   ".join(parts)


def _build_rx_body(rx: Dict[str, Any]) -> str:
    if not isinstance(rx, dict):
        return ""
    rows = []
    od_line = _rx_eye_line("OD", rx.get("od") or {})
    os_line = _rx_eye_line("OS", rx.get("os") or {})
    if od_line:
        rows.append(od_line)
    if os_line:
        rows.append(os_line)
    add = rx.get("add")
    if _has_value(add):
        rows.append(f"Addizione: {_fmt_num(add) or add}")
    return "\n".join(rows)


def build_referto_oculistico_a4(data: Dict[str, Any], letterhead_jpeg_path: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    draw_the_organism_letterhead(c, letterhead_path)
    draw_professional_block(c, professional)
    w, h = A4
    try:
       
    except Exception:
        pass

    left_x = 2.2 * cm
    right_margin = 2.2 * cm
    content_w = w - left_x - right_margin
    y = h - 5.2 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_x, y, "Referto visita oculistica")
    y -= 18

    # Riga anagrafica e data
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_x, y, f"Paziente: {_fmt_paziente(data.get('paziente', ''))}")
    c.setFont("Helvetica", 11)
    c.drawRightString(w - right_margin, y, f"Data: {_clean(data.get('data', ''))}")

    # Anamnesi a destra sotto la data, solo se compilata
    anamnesi = _clean(data.get("anamnesi", ""))
    if anamnesi:
        box_w = 7.0 * cm
        box_x = w - right_margin - box_w
        _, box_h = _draw_boxed_multiline(c, "Anamnesi", anamnesi, box_x, y - 18, box_w, min_height=1.8 * cm)
        y -= max(24, box_h + 8)
    else:
        y -= 18

    def section(title: str, body: str):
        nonlocal y
        body = _clean(body)
        if not body:
            return
        if y < 6 * cm:
            c.showPage()
            try:
                c.drawImage(letterhead_jpeg_path, 0, 0, width=w, height=h, mask='auto')
            except Exception:
                pass
            y = h - 5.2 * cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y, title)
        y -= 14
        y = _ml(c, body, left_x, y)
        y -= 8

    av_body = _build_acuita_body(data.get("acuita") or {})
    section("Acuità visiva (decimi)", av_body)

    eo_body = _build_eo_body(data.get("esame_obiettivo") or {})
    section("Esame obiettivo", eo_body)

    rx_ab_body = _build_rx_body(data.get("correzione_abituale") or {})
    section("Correzione abituale", rx_ab_body)

    rx_fin_body = _build_rx_body(data.get("correzione_finale") or {})
    section("Correzione finale", rx_fin_body)

    note_body = _clean(data.get("note", ""))
    section("Note", note_body)

    y_sig = 3.3 * cm
    c.setFont("Helvetica", 11)
    c.drawRightString(w - right_margin, y_sig + 10, "Firma / Timbro")
    c.line(w - 6.2 * cm, y_sig, w - right_margin, y_sig)

    c.showPage()
    c.save()
    return buf.getvalue()
