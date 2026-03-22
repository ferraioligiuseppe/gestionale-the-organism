from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from .webcam_browser_v3_embed import get_webcam_browser_v3_html
from .report_gaze_pnev import build_report_from_payloads


def ui_webcam_browser_v3(paziente_id=None, paziente_label=""):
    st.subheader("Eye Tracking / Webcam AI")
    st.caption(
        "Versione browser-based stabile. La webcam viene gestita lato browser "
        "con MediaPipe JS, senza OpenCV lato server."
    )

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )

    components.html(html, height=1240, scrolling=True)

    st.markdown("---")
    st.markdown("### Referto automatico PNEV")

    uploaded_webcam_json = st.file_uploader(
        "Carica il JSON esportato dalla sessione webcam",
        type=["json"],
        key="gaze_webcam_json_uploader",
    )

    uploaded_clinical_eye_json = st.file_uploader(
        "Carica eventuale JSON/estratto Clinical Eye",
        type=["json"],
        key="gaze_clinical_eye_json_uploader",
    )

    operator_name = st.text_input(
        "Operatore",
        value="Dott. Giuseppe Ferraioli",
        key="gaze_operator_name",
    )

    webcam_payload = None
    clinical_eye_payload = None

    if uploaded_webcam_json is not None:
        try:
            webcam_payload = json.load(uploaded_webcam_json)
            st.success("JSON webcam caricato correttamente.")
        except Exception as e:
            st.error(f"Errore lettura JSON webcam: {e}")

    if uploaded_clinical_eye_json is not None:
        try:
            clinical_eye_payload = json.load(uploaded_clinical_eye_json)
            st.success("JSON Clinical Eye caricato correttamente.")
        except Exception as e:
            st.error(f"Errore lettura JSON Clinical Eye: {e}")

    if st.button("Genera referto automatico PNEV", key="btn_generate_gaze_report"):
        if webcam_payload is None and clinical_eye_payload is None:
            st.warning("Carica almeno un JSON (webcam oppure Clinical Eye).")
        else:
            try:
                report = build_report_from_payloads(
                    patient_label=paziente_label or "",
                    patient_id=paziente_id,
                    operator_name=operator_name,
                    clinical_eye_payload=clinical_eye_payload,
                    webcam_payload=webcam_payload,
                )

                st.session_state["gaze_auto_report_text"] = report["report_text"]
                st.session_state["gaze_auto_report_struct"] = report
                st.success("Referto generato correttamente.")
            except Exception as e:
                st.error(f"Errore generazione referto: {e}")

    report_text = st.session_state.get("gaze_auto_report_text", "")
    report_struct = st.session_state.get("gaze_auto_report_struct", None)

    if report_text:
        st.text_area(
            "Referto automatico PNEV",
            value=report_text,
            height=520,
            key="gaze_auto_report_textarea",
        )

        st.download_button(
            "Scarica referto TXT",
            data=report_text.encode("utf-8"),
            file_name=f"referto_gaze_pnev_{paziente_id or 'nd'}.txt",
            mime="text/plain",
            key="download_gaze_report_txt",
        )

        with st.expander("Dettaglio strutturato referto"):
            st.json(report_struct)
