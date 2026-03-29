PATCH — SALVATAGGIO DIRETTO ON CLICK

File inclusi:
- app_core.py
- modules/app_core.py
- modules/gaze_tracking/ui_gaze_tracking.py
- modules/gaze_tracking/ui_webcam_browser_v3.py
- modules/gaze_tracking/webcam_browser_v3_embed.py
- modules/gaze_tracking/db_gaze_tracking.py
- modules/gaze_tracking/__init__.py

Cosa fa:
- aggiunge il bottone "Salva su DB" dentro il modulo webcam browser-based
- invia il payload live al gestionale tramite query params
- salva direttamente su Neon/PostgreSQL in gaze_sessions + gaze_reports
- mostra conferma salvataggio e storico sessioni del paziente

Nota:
- questo salvataggio diretto memorizza metriche e indici del payload browser-based
- non salva i frame completi o i landmarks estesi
- il JSON grezzo viene conservato in gaze_reports.raw_payload_json
