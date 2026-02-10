from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit

def _clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join([_clean(x) for x in v if _clean(x)])
    return str(v).strip()

def _add_line(lines: List[Tuple[str,str]], label: str, value: Any):
    v = _clean(value)
    if v != "":
        lines.append((label, v))

def genera_referto_visita_bytes(dati: Dict[str, Any]) -> bytes:
    """Referto visita visiva A4. Stampa SOLO i campi valorizzati."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, H-2.2*cm, "THE ORGANISM – STUDIO CLINICO")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, H-2.8*cm, "Dott. Giuseppe Ferraioli – Dott. Cirillo")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2*cm, H-3.7*cm, "REFERTO VISITA VISIVA")
    c.setLineWidth(0.5)
    c.line(2*cm, H-3.9*cm, W-2*cm, H-3.9*cm)

    y = H - 4.6*cm
    c.setFont("Helvetica", 10)

    lines: List[Tuple[str,str]] = []
    _add_line(lines, "Paziente", dati.get("paziente_label"))
    _add_line(lines, "Data", dati.get("data_visita"))

    av = dati.get("av", {})
    if isinstance(av, dict):
        _add_line(lines, "AV Lontano OD", av.get("lontano_od"))
        _add_line(lines, "AV Lontano OS", av.get("lontano_os"))
        _add_line(lines, "AV Vicino OD", av.get("vicino_od"))
        _add_line(lines, "AV Vicino OS", av.get("vicino_os"))
        _add_line(lines, "AV Intermedio OD", av.get("intermedio_od"))
        _add_line(lines, "AV Intermedio OS", av.get("intermedio_os"))

    eo = dati.get("esame_obiettivo", {})
    if isinstance(eo, dict):
        _add_line(lines, "Congiuntiva", eo.get("congiuntiva"))
        _add_line(lines, "Cornea", eo.get("cornea"))
        _add_line(lines, "Cristallino", eo.get("cristallino"))
        _add_line(lines, "Fondo oculare", eo.get("fondo_oculare"))
        _add_line(lines, "Pressione oculare", eo.get("pressione_oculare"))
        _add_line(lines, "Pachimetria", eo.get("pachimetria"))

    _add_line(lines, "Motilità oculare", dati.get("motilita_oculare"))
    _add_line(lines, "Foria/Tropia (Δ prismatiche)", dati.get("foria_tropia"))

    for key, title in [("ref_abituale", "Refrazione abituale"), ("ref_corretta", "Refrazione corretta")]:
        ref = dati.get(key, {})
        if isinstance(ref, dict):
            for dist_key, dist_label in [("lontano","Lontano"), ("intermedio","Intermedio"), ("vicino","Vicino")]:
                d = ref.get(dist_key, {})
                if isinstance(d, dict):
                    od = d.get("od", {})
                    os_ = d.get("os", {})
                    if any(_clean(x) for x in [od.get("sf"), od.get("cil"), od.get("ax"), os_.get("sf"), os_.get("cil"), os_.get("ax"), d.get("add")]):
                        _add_line(lines, f"{title} {dist_label} OD", f"SF {od.get('sf','')}  CIL {od.get('cil','')}  AX {od.get('ax','')}")
                        _add_line(lines, f"{title} {dist_label} OS", f"SF {os_.get('sf','')}  CIL {os_.get('cil','')}  AX {os_.get('ax','')}")
                        _add_line(lines, f"{title} {dist_label} ADD", d.get("add"))

    _add_line(lines, "Note", dati.get("note"))
    _add_line(lines, "Conclusioni/Indicazioni", dati.get("conclusioni"))

    label_w = 5.2*cm
    max_w = W - 4*cm
    for label, value in lines:
        if y < 2.5*cm:
            c.showPage()
            y = H - 2.5*cm
            c.setFont("Helvetica", 10)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(2*cm, y, f"{label}:")
        c.setFont("Helvetica", 10)
        wrapped = simpleSplit(value, "Helvetica", 10, max_w - label_w)
        yy = y
        for line in wrapped:
            c.drawString(2*cm + label_w, yy, line)
            yy -= 12
        y = yy - 6

    c.setFont("Helvetica", 10)
    c.drawString(2*cm, 2*cm, "Firma e Timbro")
    c.save()
    return buf.getvalue()
