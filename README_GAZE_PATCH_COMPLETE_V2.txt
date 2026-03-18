PATCH GAZE TRACKING – PATIENT FILTER + SESSION HISTORY + TIMELINE EXPORT

File inclusi:
- app_core.py
- modules/app_core.py
- modules/gaze_tracking/ui_gaze_tracking.py
- modules/gaze_tracking/ui_webcam_browser_v3.py
- modules/gaze_tracking/webcam_browser_v3_embed.py
- modules/gaze_tracking/db_gaze_tracking.py
- modules/gaze_tracking/video_face_pipeline.py
- modules/gaze_tracking/__init__.py

Cosa cambia:
1) selezione paziente con filtro testo e conteggio pazienti rilevati
2) sessione browser con timeline vera dentro il JSON esportato
3) salvataggio su DB tramite upload del JSON sequenza
4) storico sessioni salvate per paziente con download JSON
5) overlay migliorato: smoothing, modalità ridotta se volto laterale
6) evidenziazione aree/muscoli funzionali (didattico-funzionale, non EMG)

Nota:
Il salvataggio completamente diretto on-click browser->DB non è affidabile con components.html semplice.
Questa patch usa una strada stabile: export JSON sequenza -> upload -> salva nel DB -> storico sessioni.
