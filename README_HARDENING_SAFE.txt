VERSIONE TEST — HARDENING SAFE

Pulizie eseguite:
- rimossi __pycache__ e file .pyc dallo ZIP
- rimossi file storici/backup non necessari:
  app_OLD1.py
  app_OLD2.py
  app_patched.py
  app_pre_variazione _moduli.py
- rimosso file temporaneo tmp_a5_no.png
- normalizzato ui_generatore_stimolazione.py di root come shim compatibile verso:
  modules/stimolazione_uditiva/ui_generatore_stimolazione.py
- aggiunto .gitignore per evitare di ricommitare cache e file temporanei

Non sono stati modificati:
- vision_manager
- database / secrets
- login
- logica clinica delle sezioni
- moduli uditivi canonici

Uso consigliato:
1) caricare prima su TEST
2) verificare apertura app
3) controllare Pazienti, Anamnesi, Privacy, Referti, Vision, Udito
4) salvare questa base come TEST_STABILE_FINALE se tutto è ok
