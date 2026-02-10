
# Vision Manager – estrazione chirurgica (indipendente)

## Online (Streamlit Cloud)
Secrets (stessi del gestionale):
- DATABASE_URL
- S3_BUCKET
- S3_ACCESS_KEY
- S3_SECRET_KEY
- S3_REGION
- PRESIGN_EXPIRE_SECONDS

## Asset carta intestata
Inserisci gli sfondi in:
- vision_core/assets/print_bg/

Se non presenti, la prescrizione viene generata senza sfondo (fallback).

## Run
pip install -r requirements.txt
streamlit run app.py
