
PACCHETTO B — VIDEOCAMERA + FACE / EYE / ORAL
=============================================

Contenuto:
- ui_gaze_tracking.py               -> UI aggiornata con tabs Import / Videocamera / Tobii live
- video_face_pipeline.py           -> pipeline snapshot camera + MediaPipe Face Mesh
- metrics_face_oral.py             -> metriche base occhi / bocca / postura testa
- mediapipe_draw.py                -> overlay landmarks sull'immagine

Dipendenze consigliate per Streamlit Cloud:
- mediapipe
- opencv-python-headless
- numpy
- Pillow

Aggiungi a requirements.txt:
mediapipe
opencv-python-headless
numpy
Pillow

Note:
- Questa V1 usa st.camera_input() e analizza uno snapshot statico.
- Il realtime continuo frame-by-frame NON è incluso in questa versione.
- La tab Tobii live è predisposta ma richiede SDK tobii-research.
