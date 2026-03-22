from __future__ import annotations

import json
import streamlit as st

from modules.gaze_tracking.eye_metrics_engine import compute_eye_metrics
from modules.gaze_tracking.report_gaze_pnev import build_report_from_payloads


def ui_reading_tobii_extension(paziente_id=None, paziente_label: str = ""):
    st.markdown("---")
    st.subheader("Tobii / Eye tracker – analisi sessione")

    uploaded_tobii = st.file_uploader("Carica sessione Tobii JSON", type=["json"], key="reading_tobii_json_upload")
    uploaded_webcam = st.file_uploader("Carica sessione webcam/orofacciale JSON (opzionale)", type=["json"], key="reading_webcam_json_upload")
    operator_name = st.text_input("Operatore referto", value="Dott. Giuseppe Ferraioli", key="reading_tobii_operator_name")

    tobii_payload = None
    webcam_payload = None

    if uploaded_tobii is not None:
        try:
            tobii_payload = json.load(uploaded_tobii)
            st.success("Sessione Tobii caricata.")
        except Exception as e:
            st.error(f"Errore lettura JSON Tobii: {e}")

    if uploaded_webcam is not None:
        try:
            webcam_payload = json.load(uploaded_webcam)
            st.success("Sessione webcam caricata.")
        except Exception as e:
            st.error(f"Errore lettura JSON webcam: {e}")

    if tobii_payload and st.button("Calcola metriche eye tracking", key="btn_calc_tobii_metrics"):
        samples = tobii_payload.get("samples", []) or []
        metrics = compute_eye_metrics(samples)
        clinical_eye_payload = {
            "stimulus_name": tobii_payload.get("stimulus_name", ""),
            "reading_mode": tobii_payload.get("reading_mode", ""),
            "viewing_distance_mm": tobii_payload.get("screen_distance_mm"),
            "fixations_total": metrics.get("fixations_total"),
            "fixations_per_min": metrics.get("fixations_per_min"),
            "fixation_mean_ms": metrics.get("fixation_mean_ms"),
            "fixation_sd_ms": metrics.get("fixation_sd_ms"),
            "fixation_median_ms": metrics.get("fixation_median_ms"),
            "blinks_total": tobii_payload.get("blinks_total"),
            "blink_rate_min": tobii_payload.get("blink_rate_min"),
            "saccades_right_total": tobii_payload.get("saccades_right_total"),
            "regressions_total": metrics.get("regressions_total"),
            "gaze_stability_index": tobii_payload.get("gaze_stability_index"),
        }
        st.session_state["reading_clinical_eye_payload"] = clinical_eye_payload
        st.json(clinical_eye_payload)

    if st.button("Genera referto integrato PNEV", key="btn_generate_integrated_reading_report"):
        clinical_eye_payload = st.session_state.get("reading_clinical_eye_payload")
        if not clinical_eye_payload and tobii_payload:
            samples = tobii_payload.get("samples", []) or []
            metrics = compute_eye_metrics(samples)
            clinical_eye_payload = {
                "stimulus_name": tobii_payload.get("stimulus_name", ""),
                "reading_mode": tobii_payload.get("reading_mode", ""),
                "viewing_distance_mm": tobii_payload.get("screen_distance_mm"),
                "fixations_total": metrics.get("fixations_total"),
                "fixations_per_min": metrics.get("fixations_per_min"),
                "fixation_mean_ms": metrics.get("fixation_mean_ms"),
                "fixation_sd_ms": metrics.get("fixation_sd_ms"),
                "fixation_median_ms": metrics.get("fixation_median_ms"),
                "blinks_total": tobii_payload.get("blinks_total"),
                "blink_rate_min": tobii_payload.get("blink_rate_min"),
                "saccades_right_total": tobii_payload.get("saccades_right_total"),
                "regressions_total": metrics.get("regressions_total"),
                "gaze_stability_index": tobii_payload.get("gaze_stability_index"),
            }

        if not clinical_eye_payload and not webcam_payload:
            st.warning("Carica almeno una sessione Tobii o webcam.")
        else:
            report = build_report_from_payloads(
                patient_label=paziente_label or "",
                patient_id=paziente_id,
                operator_name=operator_name,
                clinical_eye_payload=clinical_eye_payload,
                webcam_payload=webcam_payload,
            )
            st.text_area("Referto integrato PNEV", value=report["report_text"], height=540, key="reading_integrated_report_text")
            st.download_button(
                "Scarica referto TXT",
                data=report["report_text"].encode("utf-8"),
                file_name=f"referto_lettura_integrata_{paziente_id or 'nd'}.txt",
                mime="text/plain",
                key="download_reading_integrated_report",
            )
