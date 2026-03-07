VERSIONE MODULARIZZATA (STEP 1)

Questa versione NON stravolge il gestionale: riduce il rischio di rottura.

Cosa è stato estratto:
- app.py -> bootstrap minimo + set_page_config + main()
- app_core.py -> logica storica del gestionale
- modules/app_menu.py -> definizione menu sidebar
- modules/app_udito_router.py -> routing moduli uditivi

Perché è più sicura:
- app.py diventa piccolo e stabile
- le voci di menu non sono più mischiate alla logica clinica
- la parte uditiva è isolata in un router dedicato
- vision_manager non è stato toccato

Prossimo step consigliato:
1) estrarre Pazienti / Anamnesi
2) estrarre Privacy
3) estrarre Relazioni Cliniche
4) mantenere vision_manager separato
