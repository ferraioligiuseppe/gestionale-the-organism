from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from vision_manager.pdf_layout_the_organism import (
    draw_professional_block,
    draw_the_organism_letterhead,
)


def _fmt_rx(rx):
    rx = rx or {}
    sf = rx.get("sf", "")
    cyl = rx.get("cyl", "")
    ax = rx.get("ax", "")
    return f"SF {sf}   CIL {cyl}   AX {ax}"


def build_prescrizione_occhiali_a4(data, letterhead_path=None, professional=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    draw_the_organism_letterhead(c, letterhead_path)
    draw_professional_block(c, professional)

    paziente = str(data.get("paziente", "") or "")
    data_visita = str(data.get("data", "") or "")

    lontano = data.get("lontano", {}) or {}
    intermedio = data.get("intermedio", {}) or {}
    vicino = data.get("vicino", {}) or {}

    c.setFont("Helvetica", 11)
    c.drawString(40, 705, f"Data {data_visita}")
    c.drawString(40, 687, f"Sig. {paziente}")

    y = 620
    blocks = [
        ("LONTANO OD", _fmt_rx(lontano.get("od"))),
        ("LONTANO OS", _fmt_rx(lontano.get("os"))),
        ("INTERMEDIO OD", _fmt_rx(intermedio.get("od"))),
        ("INTERMEDIO OS", _fmt_rx(intermedio.get("os"))),
        ("VICINO OD", _fmt_rx(vicino.get("od"))),
        ("VICINO OS", _fmt_rx(vicino.get("os"))),
    ]

    for label, value in blocks:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(180, y, value)
        y -= 22

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
