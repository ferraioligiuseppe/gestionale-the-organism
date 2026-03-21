from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

LETTERHEAD = "vision_manager/assets/letterhead_the_organism_clean_A4.jpg"

def build_prescrizione_occhiali_a4(data, letterhead_path=None):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # SOLO carta intestata (NO nomi professionisti qui)
    c.drawImage(letterhead_path or LETTERHEAD, 0, 0, width=width, height=height)

    # contenuto base (mantieni il tuo originale qui)
    c.setFont("Helvetica", 11)
    c.drawString(40, 700, "Prescrizione occhiali")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf
