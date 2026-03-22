RIPRISTINO VERSIONE FUNZIONANTE

1) Sostituisci nel repo questi file:
   - modules/gaze_tracking/__init__.py
   - modules/gaze_tracking/ui_gaze_tracking.py
   - modules/gaze_tracking/ui_webcam_browser_v3.py
   - modules/gaze_tracking/webcam_browser_v3_embed.py

2) NON usare il custom component components/gaze_tracker_component per la webcam live.
   Se vuoi, puoi anche cancellare quella cartella per evitare confusione.

3) In app_core.py lascia la chiamata così:
   ui_gaze_tracking(
       paziente_id=int(paziente_id),
       paziente_label=paziente_label,
       get_connection=get_connection,
   )

4) Fai commit, push e reboot dell'app su Streamlit Cloud.

Nota:
Questa è la versione browser-based che usa components.html(...), non il custom component.
È quella che aveva maggiori probabilità di avviare davvero la webcam.
