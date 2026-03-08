STEP 7 SAFE — Rifinitura modulare

Cosa cambia:
- aggiunti entry point canonici per pazienti, anamnesi, privacy, pnev e referti
- i vecchi file restano come shim compatibili
- centralizzati i wrapper clinici in modules/sections/ui_cliniche.py
- aggiornato il router principale per usare i nuovi entry point

Cosa NON cambia:
- logica clinica in app_core.py
- vision_manager
- database, secrets, login
- moduli uditivi

Obiettivo:
preparare il passo successivo, dove si potrà spostare vera logica fuori da app_core.py senza rompere la compatibilità.
