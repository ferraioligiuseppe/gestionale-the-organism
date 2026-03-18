PATCH GAZE TRACKING — SALVATAGGIO DB

File aggiornati:
- app_core.py
- modules/app_core.py
- modules/gaze_tracking/db_gaze_tracking.py
- modules/gaze_tracking/ui_gaze_tracking.py
- modules/gaze_tracking/ui_webcam_browser_v3.py

Cosa aggiunge:
- salvataggio sessione browser-based su tabella gaze_sessions / gaze_reports
- storico sessioni per paziente
- import JSON esportato dal modulo live e salvataggio nel DB

Uso:
1) avvia webcam nel modulo Eye Tracking
2) premi "Export JSON"
3) carica il file JSON nella sezione "Salvataggio sessione su database"
4) premi "Salva sessione nel DB"

Nota:
questo step salva il payload JSON browser-based in modo robusto.
Il prossimo step può essere il salvataggio diretto one-click dal componente senza passare dal file JSON.
