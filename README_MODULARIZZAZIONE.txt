MODULARIZZAZIONE SICURA — STEP 2

Questa versione prosegue la modularizzazione senza toccare la logica clinica.

Cosa è stato estratto:
- app.py -> bootstrap minimale
- modules/app_menu.py -> definizione menu/sidebar
- modules/app_udito_router.py -> routing moduli uditivi
- modules/app_sections.py -> costanti condivise delle sezioni
- modules/app_main_router.py -> routing sezioni principali (Pazienti, PNEV, Vision, ecc.)

Cosa NON è stato toccato:
- vision_manager
- logica database
- login
- privacy/firma online
- implementazioni profonde di ui_pazienti / ui_anamnesi / Vision

Obiettivo di questo step:
- ridurre il rischio quando si modifica il menu
- evitare refusi tra etichette menu e routing
- preparare lo step successivo: estrazione vera di Pazienti / Anamnesi in moduli dedicati
