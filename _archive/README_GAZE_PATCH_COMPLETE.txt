PATCH COMPLETA EYE TRACKING / WEBCAM AI

File inclusi:
- app_core.py
- modules/app_core.py
- modules/gaze_tracking/ui_gaze_tracking.py
- modules/gaze_tracking/video_face_pipeline.py

Cosa cambia:
1. ui_gaze_tracking_section ora accetta anche parametri legacy e usa solo il modulo browser-based.
2. ui_gaze_tracking ignora kwargs legacy come get_conn.
3. video_face_pipeline non mostra più il warning cloud-safe legacy.

Dopo la sostituzione:
- commit
- push
- reboot app su Streamlit Cloud
