from __future__ import annotations
from typing import Dict, Any
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def _ml(c, text: str, x: float, y: float, max_chars=98, line_h=13):
    if not text:
        return y
    # support newlines too
    chunks = []
    for part in text.split("\n"):
        words = part.replace("\r","").split()
        line=""
        for w in words:
            test=(line+" "+w).strip()
            if len(test)<=max_chars:
                line=test
            else:
                if line: chunks.append(line)
                line=w
        if line: chunks.append(line)
        chunks.append("")  # paragraph break
    if chunks and chunks[-1]=="": chunks.pop()
    c.setFont("Helvetica", 10)
    for ln in chunks:
        if ln=="":
            y -= line_h//2
            continue
        c.drawString(x, y, ln)
        y -= line_h
    return y

def build_referto_oculistico_a4(data: Dict[str, Any], letterhead_jpeg_path: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    try:
        c.drawImage(letterhead_jpeg_path, 0, 0, width=w, height=h, mask='auto')
    except Exception:
        pass

    x = 2.2*cm
    y = h - 3.6*cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Referto visita oculistica")
    y -= 18

    c.setFont("Helvetica", 10)
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
            y = h - 3.6*cm
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
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 2.2*cm, y_sig + 10, "Firma / Timbro")
    c.line(w - 6.2*cm, y_sig, w - 2.2*cm, y_sig)

    c.showPage()
    c.save()
    return buf.getvalue()
