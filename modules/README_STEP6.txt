STEP 6 SAFE — Riduzione dipendenze di app_core

Cosa cambia:
- il router principale non riceve più una lunga lista di callback da app_core
- le sezioni principali usano wrapper lazy modulari
- aggiunto package modules/sections per Vision, Sedute, Dashboard, Coupon, Debug, Import, Utenti
- pazienti/anamnesi/privacy/referti/pnev continuano a funzionare con import lazy

Cosa NON cambia:
- Vision Manager
- database e secrets
- comportamento clinico delle sezioni
- routing uditivo già stabile

Obiettivo:
- ridurre il rischio quando si modifica app_core.py
- preparare il passo successivo: spostare logica interna reale fuori da app_core
