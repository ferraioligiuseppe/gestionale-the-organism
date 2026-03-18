# modules/gaze_tracking/ui_webcam_browser_v3.py

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from .webcam_browser_v3_embed import get_webcam_browser_v3_html


def ui_webcam_browser_v3(paziente_id=None, paziente_label=""):
    st.subheader("Eye Tracking / Webcam AI")

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )

    components.html(html, height=1250, scrolling=True)
