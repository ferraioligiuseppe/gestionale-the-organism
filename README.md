# Pacchetto unico – PNEV integrata + IA stub + Auth stabile

## Contenuto
- app.py (questo file va in root repo)
- pnev_module.py (UI + JSON + summary PNEV)
- pnev_ai.py (stub IA rule-based; nessuna chiamata esterna)
- README.md (questo)

## Installazione (repo)
1) Copia **app_final.py** nel repo e rinominalo in **app.py**
2) Copia **pnev_module.py** e **pnev_ai.py** nella stessa cartella di app.py
3) Commit & push sul branch TEST
4) Streamlit Cloud → Reboot app

## Secrets consigliati (TEST)
APP_MODE = "test"
DB_ENV   = "test"

[db]
DATABASE_URL = "postgresql://...sslmode=require"

[ai]
ENABLED = true

[breakglass]
ENABLED = true
USERNAME = "emergency"
PASSWORD = "..."

## Secrets consigliati (PROD)
APP_MODE = "prod"
DB_ENV   = "prod"

[db]
DATABASE_URL = "postgresql://...sslmode=require"

[ai]
ENABLED = false

[breakglass]
ENABLED = false

## Nota
- L'hash password (_pwd_hash / _pwd_verify) ha import locali: evita NameError anche se gli import globali cambiano.
- L'audit log è break-glass safe: user_id < 1 viene salvato come NULL per evitare ForeignKeyViolation.
