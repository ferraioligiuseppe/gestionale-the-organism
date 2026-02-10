from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Tuple, Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit


from pypdf import PdfReader, PdfWriter
import os

def _overlay_on_template(content_pdf_bytes: bytes, template_path: str) -> bytes:
    try:
        if not os.path.exists(template_path):
            return content_pdf_bytes
        r_t = PdfReader(template_path)
        r_c = PdfReader(BytesIO(content_pdf_bytes))
        w = PdfWriter()

        base = r_t.pages[0]
        overlay = r_c.pages[0]

        base.merge_page(overlay)
        w.add_page(base)

        # if content has more pages, append them as-is (rare)
        for i in range(1, len(r_c.pages)):
            w.add_page(r_c.pages[i])

        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception:
        return content_pdf_bytes

def _s(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()

def _has(v: Any) -> bool:
    return _s(v) != ""

def _fmt_ref(eye: str, d: Dict[str, Any]) -> str:
    # prints only filled parts, like: "ODX: -1.00 (-0.50 x 90°)"
    sf = _s(d.get("sf"))
    cil = _s(d.get("cil"))
    ax = _s(d.get("ax"))
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

def _section_title(c: canvas.Canvas, y: float, title: str) -> float:
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, title.upper())
    return y - 14

def _bullet(c: canvas.Canvas, y: float, text: str, font="Helvetica", size=10) -> float:
    c.setFont(font, size)
    max_w = A4[0] - 4*cm
    lines = simpleSplit(text, font, size, max_w)
    for i, ln in enumerate(lines):
        prefix = "- " if i == 0 else "  "
        c.drawString(2*cm, y, prefix + ln)
        y -= 12
    return y

def genera_referto_visita_bytes(dati: Dict[str, Any]) -> bytes:
    """Referto oculistico/optometrico A4, stile pulito (come tuo esempio). Stampa solo campi valorizzati."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # Header (testuale; se vuoi sfondo/intestazione grafica la mettiamo dopo)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, H-2.2*cm, "Referto oculistico / optometrico")
    c.setFont("Helvetica", 10)
    y = H-3.0*cm

    paz = _s(dati.get("paziente_label"))
    dn = _s(dati.get("data_nascita"))
    dv = _s(dati.get("data_visita"))

    if paz:
        c.drawString(2*cm, y, f"Paziente: {paz}"); y -= 12
    if dn:
        c.drawString(2*cm, y, f"Data di nascita: {dn}"); y -= 12
    if dv:
        c.drawString(2*cm, y, f"Data visita: {dv}"); y -= 16

    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Dettaglio clinico")
    y -= 18

    # ACUITA' VISIVA (modello libero) + ACUITA' VISIVA (decimi)
    av = dati.get("av", {}) or {}
    avd = dati.get("av_decimi", {}) or {}
    av_rows = []
    nat_odx = _s(av.get("nat_odx")); nat_osn = _s(av.get("nat_osn")); nat_oo = _s(av.get("nat_oo"))
    cor_odx = _s(av.get("corr_odx")); cor_osn = _s(av.get("corr_osn")); cor_oo = _s(av.get("corr_oo"))
    if any([nat_odx, nat_osn, nat_oo, cor_odx, cor_osn, cor_oo]):
        y = _section_title(c, y, "Acuità visiva")
        if any([nat_odx, nat_osn, nat_oo]):
            y = _bullet(c, y, f"NAT: ODX {nat_odx or ''} | OSN {nat_osn or ''} | OO {nat_oo or ''}")
        if any([cor_odx, cor_osn, cor_oo]):
            y = _bullet(c, y, f"CORR: ODX {cor_odx or ''} | OSN {cor_osn or ''} | OO {cor_oo or ''}")
        y -= 6


# AV decimi (L/I/V)
if isinstance(avd, dict):
    dvals = [
        ("lontano_odx","AV Lontano ODX"), ("lontano_osn","AV Lontano OSN"),
        ("intermedio_odx","AV Intermedio ODX"), ("intermedio_osn","AV Intermedio OSN"),
        ("vicino_odx","AV Vicino ODX"), ("vicino_osn","AV Vicino OSN"),
    ]
    if any(_s(avd.get(k)) for k,_ in dvals):
        y = _section_title(c, y, "Acuità visiva (decimi)")
        # group into 3 lines
        lon = f"Lontano: ODX {_s(avd.get('lontano_odx'))} | OSN {_s(avd.get('lontano_osn'))}"
        inte = f"Intermedio: ODX {_s(avd.get('intermedio_odx'))} | OSN {_s(avd.get('intermedio_osn'))}"
        vic = f"Vicino: ODX {_s(avd.get('vicino_odx'))} | OSN {_s(avd.get('vicino_osn'))}"
        if any(_s(avd.get(k)) for k in ["lontano_odx","lontano_osn"]): y = _bullet(c, y, lon)
        if any(_s(avd.get(k)) for k in ["intermedio_odx","intermedio_osn"]): y = _bullet(c, y, inte)
        if any(_s(avd.get(k)) for k in ["vicino_odx","vicino_osn"]): y = _bullet(c, y, vic)
        y -= 6

    # REFR. OGGETTIVA / SOGGETTIVA
    ro = (dati.get("ref_oggettiva") or {})
    rs = (dati.get("ref_soggettiva") or {})
    if isinstance(ro, dict) and any(_has(((ro.get("odx") or {}).get(k))) for k in ["sf","cil","ax"]):
        y = _section_title(c, y, "Refrazione oggettiva (SF / CIL x AX)")
        line = _fmt_ref("ODX", ro.get("odx") or {})
        if line: y = _bullet(c, y, line[2:])  # already has "- "
        line = _fmt_ref("OSN", ro.get("osn") or {})
        if line: y = _bullet(c, y, line[2:])
        y -= 6

    if isinstance(rs, dict) and any(_has(((rs.get("odx") or {}).get(k))) for k in ["sf","cil","ax"]):
        y = _section_title(c, y, "Refrazione soggettiva (SF / CIL x AX)")
        line = _fmt_ref("ODX", rs.get("odx") or {})
        if line: y = _bullet(c, y, line[2:])
        line = _fmt_ref("OSN", rs.get("osn") or {})
        if line: y = _bullet(c, y, line[2:])
        y -= 6

    # CHERATOMETRIA
    ker = dati.get("cheratometria") or {}
    if isinstance(ker, dict) and any(_has(v) for v in ker.values()):
        y = _section_title(c, y, "Cheratometria")
        if _has(ker.get("odx")): y = _bullet(c, y, f"ODX: {ker.get('odx')}")
        if _has(ker.get("osn")): y = _bullet(c, y, f"OSN: {ker.get('osn')}")
        y -= 6

    # TONOMETRIA
    ton = dati.get("tonometria") or {}
    if isinstance(ton, dict) and any(_has(v) for v in ton.values()):
        y = _section_title(c, y, "Tonometria")
        if _has(ton.get("odx")): y = _bullet(c, y, f"ODX: {ton.get('odx')} mmHg")
        if _has(ton.get("osn")): y = _bullet(c, y, f"OSN: {ton.get('osn')} mmHg")
        y -= 6

    # MOTILITA' / ALLINEAMENTO
    mot = _s(dati.get("motilita_allineamento"))
    if mot:
        y = _section_title(c, y, "Motilità / allineamento")
        y = _bullet(c, y, mot)
        y -= 6

    # COLORI / PACHIMETRIA
    col = _s(dati.get("colori"))
    pach = dati.get("pachimetria") or {}
    if col or (isinstance(pach, dict) and any(_has(v) for v in pach.values())):
        y = _section_title(c, y, "Colori / Pachimetria")
        if col: y = _bullet(c, y, col)
        if isinstance(pach, dict):
            if _has(pach.get("odx")): y = _bullet(c, y, f"Pachimetria ODX: {pach.get('odx')} µm")
            if _has(pach.get("osn")): y = _bullet(c, y, f"Pachimetria OSN: {pach.get('osn')} µm")
        y -= 6

    # NOTE
    note = _s(dati.get("note"))
    if note:
        y = _section_title(c, y, "Note")
        y = _bullet(c, y, note)
        y -= 6

    # Signature line bottom-right
    c.setFont("Helvetica", 10)
    c.drawString(W-8.5*cm, 2.2*cm, "Firma / Timbro")
    c.line(W-8.5*cm, 2.0*cm, W-2*cm, 2.0*cm)

    c.save()
    pdf_bytes = buf.getvalue()
    template = os.path.join(os.path.dirname(__file__), 'assets', 'letterhead_referto_A4.pdf')
    return _overlay_on_template(pdf_bytes, template)
