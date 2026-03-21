from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

LETTERHEAD_PATH = "vision_manager/assets/letterhead_the_organism_clean_A4.jpg"

def draw_letterhead(c):
    width, height = A4
    c.drawImage(LETTERHEAD_PATH, 0, 0, width=width, height=height)

def draw_professional_block(c, professional):
    if not professional:
        return

    x = 40
    y = 780

    # Nome
    c.setFont("Helvetica-Bold", 15)
    c.drawString(x, y, professional.get("riga_1", ""))

    # Riga 2
    if professional.get("riga_2"):
        c.setFont("Helvetica", 11)
        c.drawString(x, y - 18, professional.get("riga_2"))

    # Riga 3
    if professional.get("riga_3"):
        c.drawString(x, y - 34, professional.get("riga_3"))
