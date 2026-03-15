
from __future__ import annotations
from typing import Dict, Any
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def _fmt_paziente(p):
    if isinstance(p, dict):
        cog = (p.get("cognome") or "").strip()
        nom = (p.get("nome") or "").strip()
        dn = (p.get("data_nascita") or "").strip()
        s = (cog + " " + nom).strip()
        return (s + (f" ({dn})" if dn else "")).strip() or str(p)
    return str(p or "")

def _ml(c, text: str, x: float, y: float, max_chars=98, line_h=13):
    if not text:
        return y
    chunks = []
    for part in text.split("\n"):
        words = part.replace("\r","").split()
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

def _to_float(v):
    try:
        if v is None:
            return None
        s = str(v).strip().replace(",", ".")
        if not s:
            return None
        return float(s)
    except Exception:
        return None

def _iop_adjusted(iop, cct, ref_cct: float = 540.0):
    if iop is None or cct is None:
        return None
    delta = (ref_cct - cct) / 10.0 * 0.7
    return float(iop + delta)

def _clinical_attention(iop_od, iop_os, cct_od, cct_os):
    out = {
        "od": {"flag": False, "reason": "", "adj": None},
        "os": {"flag": False, "reason": "", "adj": None},
    }
    for eye in ("od", "os"):
        iop = iop_od if eye == "od" else iop_os
        cct = cct_od if eye == "od" else cct_os
        adj = _iop_adjusted(iop, cct)

        reasons = []
        flag = False

        if iop is not None and iop >= 21:
            flag = True
            reasons.append("IOP ≥ 21 mmHg")

        if cct is not None and cct < 500 and iop is not None and iop >= 18:
            flag = True
            reasons.append("CCT < 500 µm con IOP ≥ 18 (possibile sottostima)")

        if adj is not None and adj >= 21:
            flag = True
            reasons.append(f"IOP stimata (da CCT) ≈ {adj:.1f} mmHg")

        out[eye]["flag"] = flag
        out[eye]["reason"] = "; ".join(reasons)
        out[eye]["adj"] = adj
    return out

def _build_iop_pachimetria_text(eo: Dict[str, Any]) -> str:
    if not isinstance(eo, dict):
        return ""
    iop_od = _to_float(eo.get("pressione_endoculare_od"))
    iop_os = _to_float(eo.get("pressione_endoculare_os"))
    cct_od = _to_float(eo.get("pachimetria_od"))
    cct_os = _to_float(eo.get("pachimetria_os"))

    # Inserisci la sezione solo se c'è almeno una relazione completa IOP + pachimetria
    complete_od = iop_od is not None and cct_od is not None
    complete_os = iop_os is not None and cct_os is not None
    if not (complete_od or complete_os):
        return ""

    att = _clinical_attention(iop_od, iop_os, cct_od, cct_os)
    lines = []

    if complete_od:
        line = f"OD: IOP {iop_od:.1f} mmHg - Pachimetria {cct_od:.0f} µm"
        if att["od"].get("adj") is not None:
            line += f" - IOP stimata da CCT {att['od']['adj']:.1f} mmHg"
        if att["od"].get("flag") and att["od"].get("reason"):
            line += f" - {att['od']['reason']}"
        lines.append(line)

    if complete_os:
        line = f"OS: IOP {iop_os:.1f} mmHg - Pachimetria {cct_os:.0f} µm"
        if att["os"].get("adj") is not None:
            line += f" - IOP stimata da CCT {att['os']['adj']:.1f} mmHg"
        if att["os"].get("flag") and att["os"].get("reason"):
            line += f" - {att['os']['reason']}"
        lines.append(line)

    return "\n".join(lines)

def build_referto_oculistico_a4(data: Dict[str, Any], letterhead_jpeg_path: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    try:
        c.drawImage(letterhead_jpeg_path, 0, 0, width=w, height=h, mask='auto')
    except Exception:
        pass

    x = 2.2*cm
    y = h - 5.2*cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "Referto visita oculistica")
    y -= 18

    c.setFont("Helvetica", 11)
    c.drawRightString(w - 2.2*cm, y+2, f"Data: {data.get('data','')}")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, f"Paziente: {data.get('paziente','')}")
    y -= 18

    def section(title: str, body: str):
        nonlocal y
        if not body:
            return
        if y < 6*cm:
            c.showPage()
            try:
                c.drawImage(letterhead_jpeg_path, 0, 0, width=w, height=h, mask='auto')
            except Exception:
                pass
            y = h - 5.2*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y, title)
        y -= 14
        y = _ml(c, body, x, y)
        y -= 8

    section("Anamnesi", data.get("anamnesi",""))

    av = data.get("acuita") or {}
    if av:
        body = []
        for k in ["naturale","abituale","corretta"]:
            b = av.get(k) or {}
            if b:
                body.append(f"{k.capitalize()}: OD {b.get('od','')}  OS {b.get('os','')}  OO {b.get('oo','')}")
        section("Acuità visiva (decimi)", "\n".join(body))

    eo = data.get("esame_obiettivo") or {}
    if eo:
        parts = []
        for campo in ["congiuntiva","cornea","camera_anteriore","cristallino","vitreo","fondo_oculare"]:
            v = eo.get(campo)
            if v:
                parts.append(f"{campo.replace('_',' ').title()}: {v}")
        if parts:
            section("Esame obiettivo", "\n".join(parts))

        rapporto_text = _build_iop_pachimetria_text(eo)
        if rapporto_text:
            section("Rapporto IOP / Pachimetria", rapporto_text)

    def rx_block(title, rx):
        if not rx:
            return
        od, os_ = rx.get("od",{}), rx.get("os",{})
        body = (
            f"OD: SF {od.get('sf','')}  CIL {od.get('cyl','')}  AX {od.get('ax','')}\n"
            f"OS: SF {os_.get('sf','')}  CIL {os_.get('cyl','')}  AX {os_.get('ax','')}"
        )
        if rx.get("add") not in (None, ""):
            body += f"\nAddizione: {rx.get('add')}"
        section(title, body)

    rx_block("Correzione abituale", data.get("correzione_abituale"))
    rx_block("Correzione finale", data.get("correzione_finale"))

    section("Note", data.get("note",""))

    y_sig = 3.3*cm
    c.setFont("Helvetica", 11)
    c.drawRightString(w - 2.2*cm, y_sig + 10, "Firma / Timbro")
    c.line(w - 6.2*cm, y_sig, w - 2.2*cm, y_sig)

    c.showPage()
    c.save()
    return buf.getvalue()
