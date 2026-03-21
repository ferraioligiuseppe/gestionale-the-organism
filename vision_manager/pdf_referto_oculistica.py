from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from vision_manager.pdf_layout_the_organism import (
    draw_professional_block,
    draw_the_organism_letterhead,
)


def build_referto_oculistico_a4(data, letterhead_path=None, professional=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    draw_the_organism_letterhead(c, letterhead_path)
    draw_professional_block(c, professional)

    paziente = str(data.get("paziente", "") or "")
    data_visita = str(data.get("data", "") or "")
    anamnesi = str(data.get("anamnesi", "") or "")
    note = str(data.get("note", "") or "")

    y = 705
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Referto visita oculistica")
    y -= 24

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Paziente: {paziente}")
    c.drawString(350, y, f"Data: {data_visita}")
    y -= 28

    sections = [
        ("Anamnesi", anamnesi),
        ("Acuità visiva", str(data.get("acuita", "") or "")),
        ("Esame obiettivo", str(data.get("esame_obiettivo", "") or "")),
        ("Note", note),
    ]

    for title, content in sections:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, title)
        y -= 14
        c.setFont("Helvetica", 10)
        text = c.beginText(40, y)
        for line in str(content).splitlines() or [""]:
            text.textLine(line[:120])
            y -= 12
            if y < 80:
                c.drawText(text)
                c.showPage()
                draw_the_organism_letterhead(c, letterhead_path)
                draw_professional_block(c, professional)
                y = 760
                text = c.beginText(40, y)
        c.drawText(text)
        y -= 18

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
