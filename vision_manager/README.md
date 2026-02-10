# Vision Manager – Storico + Confronto nel tempo + Export ottico (DB only)

## Streamlit Cloud
Secrets:
- DATABASE_URL (stesso Neon del gestionale)

Main file:
- vision_manager/app.py

## Funzioni
- Visita visiva: salva JSONB + PDF in DB
- Prescrizione: salva JSONB + PDF in DB (TABO solo OSN, AX da lontano)
- Storico: elenco visite, download PDF
- Confronto: tabella A vs B + grafici trend (SF/CIL lontano)
- Export ottico: CSV (da Visita B selezionata)
