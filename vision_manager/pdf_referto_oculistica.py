
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

LETTERHEAD = "vision_manager/assets/letterhead_the_organism_clean_A4.jpg"

def build_referto_oculistico_a4(data, letterhead_path=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # carta intestata
    c.drawImage(letterhead_path or LETTERHEAD, 0, 0, width=width, height=height)

    # professionista (FIX STATICO STEP1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, 780, "Dott. Giuseppe Ferraioli")

    c.setFont("Helvetica", 12)
    c.drawString(40, 762, "Neuropsicologo")

    # contenuto base
    c.setFont("Helvetica", 11)
    c.drawString(40, 700, "Referto visita oculistica")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
