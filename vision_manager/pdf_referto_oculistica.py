from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from vision_manager.pdf_letterhead_the_organism import draw_letterhead

def build_referto_oculistico_a4(data, letterhead_path=None, professional=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    draw_letterhead(c, professional)

    c.setFont("Helvetica", 11)
    c.drawString(40, 700, "Referto visita oculistica")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
