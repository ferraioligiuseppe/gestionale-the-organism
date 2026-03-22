EYE TRACKING V2 - PATCH MINIMA

Questa versione sostituisce il componente frontend custom con streamlit-webrtc.

FILE PRINCIPALE DA SOSTITUIRE:
- modules/gaze_tracking/ui_gaze_tracking.py

DIPENDENZE DA AGGIUNGERE A requirements.txt:
- streamlit-webrtc>=0.47.9
- aiortc>=1.6.0
- av>=10.0.0
- opencv-python-headless>=4.8.0

NOTE:
- Dopo il commit fai Reboot app su Streamlit Cloud.
- Alla prima apertura premi START nella preview video.
- Questa build verifica la webcam live e salva campioni base manuali.
- Lo step successivo sarà aggiungere tracking gaze/landmarks sopra il feed video.
