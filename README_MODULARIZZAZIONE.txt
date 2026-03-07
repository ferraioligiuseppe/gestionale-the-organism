MODULARIZZAZIONE SAFE — STEP 3

Base: step 2 funzionante.

Novità di questo step:
- aggiunta cartella modules/pazienti/
- aggiunta cartella modules/anamnesi/
- routing principale aggiornato per passare da entry point modulari dedicati
- comportamento clinico invariato: la logica interna resta in app_core, per non rompere il gestionale

Obiettivo di questo step:
- separare i punti di ingresso di Pazienti e Anamnesi
- preparare lo step successivo, in cui si potranno spostare porzioni interne di codice in modo graduale

File nuovi:
- modules/pazienti/ui_pazienti_section.py
- modules/anamnesi/ui_anamnesi_section.py

File modificato:
- modules/app_main_router.py

Nota:
Questo step è volutamente prudente: non tocca vision_manager, database, login, privacy o firma online.
