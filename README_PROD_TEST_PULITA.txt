VERSIONE PROD+TEST PULITA

Base: repo MAIN/PROD
Overlay: file e moduli utili dalla TEST
Preservato: vision_manager/ intatto dalla MAIN
App usata: app_test_merged_fixed.py come app.py

Controlli fatti:
- vision_manager mantenuto
- app.py con set_page_config corretto
- assets/ui.css dalla MAIN mantenuto
- assets/pnev.css dalla TEST aggiunto
- requirements.txt unificato

ATTENZIONE:
- In Streamlit TEST usare DATABASE_URL del Neon TEST e APP_MODE="test"
- In Streamlit PROD usare DATABASE_URL del Neon PROD e APP_MODE="prod"
- Non copiare i secrets da un ambiente all'altro
