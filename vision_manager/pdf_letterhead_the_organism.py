from reportlab.lib.pagesizes import A4

def draw_letterhead(c, professional=None):
    width, height = A4

    # logo placeholder
    c.setFont("Helvetica-Bold", 16)
    c.drawString(width - 250, height - 60, "THE ORGANISM")

    # green line
    c.setStrokeColorRGB(0, 0.6, 0)
    c.setLineWidth(2)
    c.line(30, height - 80, width - 30, height - 80)

    # professional
    if professional:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(30, height - 60, professional.get("riga_1",""))

        c.setFont("Helvetica", 13)
        if professional.get("riga_2"):
            c.drawString(30, height - 78, professional.get("riga_2"))
