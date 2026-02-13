from __future__ import annotations
from io import BytesIO
from typing import Any, Dict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader, PdfWriter
import os

START_UNDER_GREEN_CM = 5.0  # distanza dal bordo superiore (sotto riga verde)

def _s(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()

def _clean(v: Any) -> str:
    return _s(v)

def _bullet(c: canvas.Canvas, y: float, text: str, font="Helvetica", size=10) -> float:
    c.setFont(font, size)
    max_w = A4[0] - 4*cm
    lines = simpleSplit(text, font, size, max_w)
    for i, ln in enumerate(lines):
        prefix = "- " if i == 0 else "  "
        c.drawString(2*cm, y, prefix + ln)
        y -= 12
    return y

def _section_title(c: canvas.Canvas, y: float, title: str) -> float:
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, title.upper())
    return y - 14

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

def _fmt_ref(eye: str, d: Dict[str, Any]) -> str:
    sf = _clean(d.get("sf"))
    cil = _clean(d.get("cil"))
    ax = _clean(d.get("ax"))
    parts = []
    if sf:
        parts.append(sf)
    if cil and ax:
        parts.append(f"({cil} x {ax}°)")
    elif cil:
        parts.append(f"({cil})")
    elif ax:
        parts.append(f"(x {ax}°)")
    if not parts:
        return ""
    return f"- {eye}: " + " ".join(parts)

def genera_referto_visita_bytes(dati: Dict[str, Any]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    template = os.path.join(os.path.dirname(__file__), "assets", "letterhead_referto_A4.pdf")
    has_template = os.path.exists(template)

    # start position
    y = H - (START_UNDER_GREEN_CM*cm if has_template else 3.0*cm)

    if not has_template:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2*cm, H-2.2*cm, "Referto oculistico / optometrico")
        c.setFont("Helvetica", 10)
        y = H-3.0*cm

    # anagrafica
    c.setFont("Helvetica", 10)
    paz = _clean(dati.get("paziente_label"))
    dn = _clean(dati.get("data_nascita"))
    dv = _clean(dati.get("data_visita"))
    pd = _clean(dati.get("pd_mm"))

    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}"); y -= 12
    if dn:
        c.drawString(2*cm, y, f"Data di nascita: {dn}"); y -= 12
    if dv:
        c.drawString(2*cm, y, f"Data visita: {dv}"); y -= 12
    if pd:
        c.drawString(2*cm, y, f"PD: {pd} mm"); y -= 16
    else:
        y -= 4

    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Dettaglio clinico")
    y -= 18

    # AV abituale (decimi)
    ava = dati.get("av_abituale") or {}
    if isinstance(ava, dict) and (_clean(ava.get("odx")) or _clean(ava.get("osn"))):
        y = _section_title(c, y, "AV abituale (decimi)")
        y = _bullet(c, y, f"ODX: {_clean(ava.get('odx'))} | OSN: {_clean(ava.get('osn'))}")
        y -= 6

        # AV decimi
    avd = dati.get("av_decimi", {}) or {}
    if any(_clean(avd.get(k)) for k in ["lontano_odx","lontano_osn","intermedio_odx","intermedio_osn","vicino_odx","vicino_osn"]):
        y = _section_title(c, y, "Acuità visiva (decimi)")
        lon = f"Lontano: ODX {_clean(avd.get('lontano_odx'))} | OSN {_clean(avd.get('lontano_osn'))}"
        inte = f"Intermedio: ODX {_clean(avd.get('intermedio_odx'))} | OSN {_clean(avd.get('intermedio_osn'))}"
        vic = f"Vicino: ODX {_clean(avd.get('vicino_odx'))} | OSN {_clean(avd.get('vicino_osn'))}"
        if any(_clean(avd.get(k)) for k in ["lontano_odx","lontano_osn"]): y = _bullet(c, y, lon)
        if any(_clean(avd.get(k)) for k in ["intermedio_odx","intermedio_osn"]): y = _bullet(c, y, inte)
        if any(_clean(avd.get(k)) for k in ["vicino_odx","vicino_osn"]): y = _bullet(c, y, vic)
        y -= 6

    # Refrazione oggettiva
    ro = dati.get("ref_oggettiva") or {}
    if isinstance(ro, dict):
        odx = _fmt_ref("ODX", ro.get("odx") or {})
        osn = _fmt_ref("OSN", ro.get("osn") or {})
        if odx or osn:
            y = _section_title(c, y, "Refrazione oggettiva (SF / CIL x AX)")
            if odx: y = _bullet(c, y, odx[2:])
            if osn: y = _bullet(c, y, osn[2:])
            y -= 6

    # Refrazione soggettiva
    rs = dati.get("ref_soggettiva") or {}
    if isinstance(rs, dict):
        odx = _fmt_ref("ODX", rs.get("odx") or {})
        osn = _fmt_ref("OSN", rs.get("osn") or {})
        if odx or osn:
            y = _section_title(c, y, "Refrazione soggettiva (SF / CIL x AX)")
            if odx: y = _bullet(c, y, odx[2:])
            if osn: y = _bullet(c, y, osn[2:])
            y -= 6

    # altri campi (come prima)
    ker = dati.get("cheratometria") or {}
    if isinstance(ker, dict) and any(_clean(v) for v in ker.values()):
        y = _section_title(c, y, "Cheratometria")
        if _clean(ker.get("odx")): y = _bullet(c, y, f"ODX: {_clean(ker.get('odx'))}")
        if _clean(ker.get("osn")): y = _bullet(c, y, f"OSN: {_clean(ker.get('osn'))}")
        y -= 6

    ton = dati.get("tonometria") or {}
    if isinstance(ton, dict) and any(_clean(v) for v in ton.values()):
        y = _section_title(c, y, "Tonometria")
        if _clean(ton.get("odx")): y = _bullet(c, y, f"ODX: {_clean(ton.get('odx'))} mmHg")
        if _clean(ton.get("osn")): y = _bullet(c, y, f"OSN: {_clean(ton.get('osn'))} mmHg")
        y -= 6

    mot = _clean(dati.get("motilita_allineamento"))
    if mot:
        y = _section_title(c, y, "Motilità / allineamento")
        y = _bullet(c, y, mot)
        y -= 6

    col = _clean(dati.get("colori"))
    pach = dati.get("pachimetria") or {}
    if col or (isinstance(pach, dict) and any(_clean(v) for v in pach.values())):
        y = _section_title(c, y, "Colori / Pachimetria")
        if col: y = _bullet(c, y, col)
        if isinstance(pach, dict):
            if _clean(pach.get("odx")): y = _bullet(c, y, f"Pachimetria ODX: {_clean(pach.get('odx'))} µm")
            if _clean(pach.get("osn")): y = _bullet(c, y, f"Pachimetria OSN: {_clean(pach.get('osn'))} µm")
        y -= 6

    eo = dati.get("esame_obiettivo") or {}
    if isinstance(eo, dict) and any(_clean(eo.get(k)) for k in ["cornea","congiuntiva","camera_anteriore","cristallino"]):
        y = _section_title(c, y, "Esame obiettivo")
        y = _bullet(c, y, f"Cornea: {_clean(eo.get('cornea'))}")
        y = _bullet(c, y, f"Congiuntiva: {_clean(eo.get('congiuntiva'))}")
        y = _bullet(c, y, f"Camera anteriore: {_clean(eo.get('camera_anteriore'))}")
        y = _bullet(c, y, f"Cristallino: {_clean(eo.get('cristallino'))}")
        y -= 6

    fondo_oculare = _clean(dati.get("fondo_oculare"))
    if fondo_oculare:
        y = _section_title(c, y, "Fondo oculare")
        c.setFont("Helvetica", 10)
        max_w = A4[0] - 4*cm
        lines = simpleSplit(fondo_oculare, "Helvetica", 10, max_w)
        for ln in lines:
            c.drawString(2*cm, y, ln)
            y -= 14
        y -= 6

    note = _clean(dati.get("note"))
    if note:
        y = _section_title(c, y, "Note")
        y = _bullet(c, y, note)
        y -= 6

    c.setFont("Helvetica", 10)
    c.drawString(W-8.5*cm, 2.2*cm, "Firma / Timbro")
    c.line(W-8.5*cm, 2.0*cm, W-2*cm, 2.0*cm)

    c.save()
    pdf_bytes = buf.getvalue()
    return _overlay_on_template(pdf_bytes, template)
