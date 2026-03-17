
PACCHETTO UPGRADE VIDEO / WEBCAM GAZE

Contenuto:
- ui_gaze_tracking.py
- video_face_pipeline.py
- metrics_face_oral.py
- mediapipe_draw.py

Cosa aggiunge:
- overlay volto / occhi / bocca
- stima direzione sguardo base da iris
- indici oculo-posturali e oro-facciali
- tab videocamera aggiornata

Istruzioni:
1) sostituire i file nella cartella modules/gaze_tracking/
2) fare commit su GitHub
3) verificare requirements:
   mediapipe==0.10.32
   opencv-python-headless==4.10.0.84
   numpy==1.26.4
   Pillow
4) riavviare l'app Streamlit
