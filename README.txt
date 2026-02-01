PACCHETTO TEMPLATE PRESCRIZIONE (da immagine A5 + PDF A4 2-up)

CONTENUTO:
- assets/templates/prescrizione_A5_with_cirillo.pdf
- assets/templates/prescrizione_A5_no_cirillo.pdf  (mascherato: nome + Medico Chirurgo + Oculista)
- assets/templates/prescrizione_A4_2xA5_with_cirillo.pdf
- assets/templates/prescrizione_A4_2xA5_no_cirillo.pdf (mascherato su entrambe le metà)
- pdf_templates.py (helper per overlay+merge)
- README.txt

USO:
1) Copia assets/ e pdf_templates.py nel repo Streamlit.
2) requirements.txt: reportlab, pypdf
3) Nel tuo app.py: from pdf_templates import build_pdf
4) Genera:
   pdf_bytes = build_pdf('a5','with_cirillo', draw_fn)
   oppure  build_pdf('a4_2up','no_cirillo', draw_fn)
