from reportlab.lib.pagesizes import A4

DEFAULT_LETTERHEAD = "vision_manager/assets/letterhead_the_organism_clean_A4.jpg"


def draw_the_organism_letterhead(c, letterhead_path=None):
    width, height = A4
    path = letterhead_path or DEFAULT_LETTERHEAD
    c.drawImage(path, 0, 0, width=width, height=height)


def draw_professional_block(c, professional=None):
    if not professional:
        return

    riga_1 = (professional.get("riga_1") or "").strip()
    riga_2 = (professional.get("riga_2") or "").strip()
    riga_3 = (professional.get("riga_3") or "").strip()

    if not riga_1:
        return

    # posizione fissa coerente con carta intestata
    x = 38
    y = 785

    c.setFont("Helvetica-Bold", 15)
    c.drawString(x, y, riga_1)

    if riga_2:
        c.setFont("Helvetica", 11)
        c.drawString(x, y - 16, riga_2)

    if riga_3:
        c.drawString(x, y - 30, riga_3)
