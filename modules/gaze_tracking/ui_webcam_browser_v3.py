import streamlit as st
from components.gaze_tracker_component import gaze_tracker_component


def ui_webcam_browser_v3(paziente_id=None, paziente_label="", get_connection=None):
    st.subheader("Eye Tracking")

    if paziente_label:
        st.caption(f"Paziente: {paziente_label}")

    gaze_tracker_component()

    st.info(
        "Custom component attivo. Questa base serve per avviare la webcam in modo più stabile su Streamlit Cloud. "
        "Il salvataggio diretto su DB può essere agganciato nel passaggio successivo."
    )
