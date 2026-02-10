
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm

def genera_prescrizione_occhiali_bytes(formato: str, dati: dict, with_cirillo: bool = True) -> bytes:
    pagesize = A4 if formato.upper() == "A4" else A5
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=3.5*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    story = []

    intest = "Dott. Giuseppe Ferraioli – Dott. Cirillo" if with_cirillo else "Dott. Giuseppe Ferraioli"
    story.append(Paragraph(f"<b>THE ORGANISM – STUDIO CLINICO</b><br/>{intest}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>PRESCRIZIONE OCCHIALI</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    table = Table([
        ["Occhio", "Sfera", "Cilindro", "Asse"],
        ["OD", dati.get("od_sfera",""), dati.get("od_cil",""), dati.get("od_asse","")],
        ["OS", dati.get("os_sfera",""), dati.get("os_cil",""), dati.get("os_asse","")],
    ])
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Firma e Timbro", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
