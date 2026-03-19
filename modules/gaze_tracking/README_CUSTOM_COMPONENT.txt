PATCH CUSTOM COMPONENT VERO

File inclusi:
- components/gaze_tracker_component/__init__.py
- components/gaze_tracker_component/frontend/index.html
- components/gaze_tracker_component/frontend/app.js
- components/gaze_tracker_component/frontend/styles.css
- modules/gaze_tracking/ui_webcam_browser_v3.py
- modules/gaze_tracking/ui_gaze_tracking.py
- modules/gaze_tracking/__init__.py

NOTE
1) Questo sostituisce il vecchio components.html() con un vero custom component Streamlit.
2) Per avere il salvataggio DB diretto, in app_core.py la chiamata deve diventare:

   ui_gaze_tracking(
       paziente_id=int(paziente_id),
       paziente_label=paziente_label,
       get_connection=get_connection,
   )

3) Se non passi get_connection, la webcam funziona ma il salvataggio DB resta disattivato.
