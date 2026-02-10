
# Vision Manager (DB only – senza S3)

## Online (Streamlit Cloud)
Imposta nei Secrets:
- DATABASE_URL (stesso del gestionale)

Al primo avvio l'app crea le tabelle in Neon (public).

## Locale
Se DATABASE_URL non è presente, usa SQLite `vision_manager.db`.
