
from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from .analytics_gaze import run_gaze_analytics
from .db_gaze_tracking import init_gaze_tracking_db, insert_gaze_samples_bulk, insert_gaze_session, upsert_gaze_report
from .importer_gaze import import_eye_tracking_file
from .protocols_gaze import list_protocols
from .video_face_pipeline import analyze_face_image, get_video_pipeline_status


def apply_gaze_ui_style():
    st.markdown(
        '''
        <style>
        input, textarea, select { background-color: #ffffff !important; color: #000000 !important; }
        div[data-baseweb="select"] > div { background-color: #ffffff !important; color: #000000 !important; }
        section[data-testid="stFileUploader"] { background-color: #f5f5f5; padding: 10px; border-radius: 8px; }
        .stDataFrame { background-color: white; color: black; }
        code { color: #000000 !important; }
        </style>
        ''',
        unsafe_allow_html=True,
    )


def _render_import_tab(paziente_id: int, paziente_label: str | None, get_conn):
    protocol_options = list_protocols()
    protocol_map = {p["label"]: p["key"] for p in protocol_options}

    col1, col2 = st.columns(2)
    with col1:
        selected_protocol_label = st.selectbox("Protocollo clinico", options=list(protocol_map.keys()), index=0, key="gaze_import_protocol")
    with col2:
        vendor = st.selectbox("Vendor import", options=["auto", "tobii", "thomson", "generic"], index=0, key="gaze_vendor")

    uploaded_file = st.file_uploader("Carica file eye tracker", type=["csv", "xls", "xlsx"], accept_multiple_files=False, key="gaze_import_file")
    session_notes = st.text_area("Note sessione", height=100, key="gaze_import_notes")

    if uploaded_file is None:
        st.info("Carica un file per iniziare.")
        return

    if st.button("Analizza file", type="primary", use_container_width=True, key="gaze_import_analyze"):
        try:
            import_result = import_eye_tracking_file(uploaded_file, forced_vendor=vendor)
        except Exception as exc:
            st.error(f"Errore durante importazione: {exc}")
            return

        validation = import_result.validation
        metadata = import_result.metadata
        df = import_result.df

        with st.expander("Validazione import", expanded=True):
            st.json(validation)
            st.json(metadata)

        if not validation.get("valid", False):
            st.error("Il file non ha superato la validazione.")
            return

        st.dataframe(df.head(50), use_container_width=True)
        protocol_name = protocol_map[selected_protocol_label]

        try:
            analysis = run_gaze_analytics(df=df, protocol_name=protocol_name, metadata=metadata)
        except Exception as exc:
            st.error(f"Errore durante analisi: {exc}")
            return

        metrics = analysis["metrics"]
        clinical_indexes = analysis["clinical_indexes"]
        distance_metrics = analysis["distance_metrics"]
        summary_json = analysis["summary_json"]
        df_enriched: pd.DataFrame = analysis["samples_enriched"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Fixation count", metrics.get("fixation_count"))
        m2.metric("Mean fixation ms", metrics.get("mean_fixation_ms"))
        m3.metric("Regressions", metrics.get("regressions"))
        m4.metric("Saccade count", metrics.get("saccade_count"))

        c1, c2, c3 = st.columns(3)
        c1.metric("Attention instability", clinical_indexes.get("attention_instability_index"))
        c2.metric("Fatigue index", clinical_indexes.get("fatigue_index"))
        c3.metric("Dyslexia risk", clinical_indexes.get("dyslexia_oculomotor_risk"))

        st.json(distance_metrics)
        st.code(json.dumps(summary_json, ensure_ascii=False, indent=2), language="json")
        st.dataframe(df_enriched.head(100), use_container_width=True)

        if st.button("Salva sessione nel database", use_container_width=True, key="gaze_import_save"):
            try:
                conn = get_conn()
                init_gaze_tracking_db(conn)

                session_id = insert_gaze_session(
                    conn,
                    {
                        "paziente_id": paziente_id,
                        "paziente_label": paziente_label,
                        "protocol_name": protocol_name,
                        "source_vendor": metadata.get("source_vendor"),
                        "source_format": metadata.get("source_format"),
                        "source_filename": metadata.get("source_filename"),
                        "operator_name": None,
                        "session_notes": session_notes,
                    },
                )

                inserted_count = insert_gaze_samples_bulk(conn, session_id, df)
                upsert_gaze_report(conn, session_id, analysis)
                st.success(f"Sessione salvata correttamente. Session ID: {session_id} · Campioni inseriti: {inserted_count}")
            except Exception as exc:
                st.error(f"Errore nel salvataggio DB: {exc}")


def _render_video_tab(paziente_id: int, paziente_label: str | None):
    st.markdown("### Videocamera live")
    status = get_video_pipeline_status()
    if not status.get("mediapipe_available", False):
        st.warning(status.get("import_error") or "MediaPipe non disponibile nell'ambiente.")
        return

    protocol_options = list_protocols()
    protocol_map = {p["label"]: p["key"] for p in protocol_options}
    selected_protocol_label = st.selectbox("Protocollo video", options=list(protocol_map.keys()), index=0, key="video_protocol")
    protocol_name = protocol_map[selected_protocol_label]

    camera_file = st.camera_input("Attiva videocamera", key="video_camera_input")
    notes = st.text_area("Note snapshot video", height=80, key="video_notes")

    if camera_file is None:
        st.info("Scatta uno snapshot per analizzare volto, occhi, bocca e postura del capo.")
        return

    if st.button("Analizza snapshot", type="primary", use_container_width=True, key="video_analyze_button"):
        result = analyze_face_image(
            image_bytes=camera_file.getvalue(),
            protocol_name=protocol_name,
            metadata={
                "paziente_id": paziente_id,
                "paziente_label": paziente_label,
                "notes": notes,
                "source": "streamlit_camera_input",
            },
        )

        if not result.get("ok"):
            st.error(result.get("error", "Errore durante analisi video."))
            if result.get("warnings"):
                st.warning("\n".join(result["warnings"]))
            return

        overlay = result.get("overlay_image")
        if overlay:
            st.image(overlay, caption="Overlay face / eyes / mouth / gaze", use_container_width=True)

        metrics = result["metrics"]
        indexes = result["indexes"]

        row1 = st.columns(4)
        row1[0].metric("Gaze", metrics.get("gaze_direction_label"))
        row1[1].metric("Head tilt °", metrics.get("head_tilt_deg"))
        row1[2].metric("Oral state", metrics.get("oral_state"))
        row1[3].metric("Palpebral asym", metrics.get("palpebral_asymmetry"))

        row2 = st.columns(4)
        row2[0].metric("Mouth open ratio", metrics.get("mouth_open_ratio"))
        row2[1].metric("L eye open", metrics.get("left_eye_open_ratio"))
        row2[2].metric("R eye open", metrics.get("right_eye_open_ratio"))
        row2[3].metric("Gaze horiz", metrics.get("gaze_horizontal_score"))

        row3 = st.columns(4)
        row3[0].metric("Oral instability", indexes.get("oral_instability_index"))
        row3[1].metric("Oculo-postural", indexes.get("oculo_postural_index"))
        row3[2].metric("Facial balance", indexes.get("facial_balance_index"))
        row3[3].metric("Gaze stability", indexes.get("gaze_stability_index"))

        with st.expander("Summary JSON", expanded=False):
            st.code(json.dumps(result["summary_json"], ensure_ascii=False, indent=2), language="json")


def _render_tobii_tab():
    st.markdown("### Tobii live")
    st.info("Tab predisposta. Per il live reale servono SDK Tobii e connessione device nell'ambiente.")


def ui_gaze_tracking(paziente_id: int, get_conn, paziente_label: str | None = None) -> None:
    apply_gaze_ui_style()

    st.subheader("Eye Tracking")
    st.caption("Import multi-vendor, videocamera AI e metriche cliniche.")

    if not paziente_id:
        st.warning("Seleziona prima un paziente.")
        return

    with st.expander("Contesto paziente", expanded=True):
        st.write(f"**Paziente ID:** {paziente_id}")
        st.write(f"**Paziente:** {paziente_label or '-'}")

    tab1, tab2, tab3 = st.tabs(["Import file", "Videocamera", "Tobii live"])
    with tab1:
        _render_import_tab(paziente_id=paziente_id, paziente_label=paziente_label, get_conn=get_conn)
    with tab2:
        _render_video_tab(paziente_id=paziente_id, paziente_label=paziente_label)
    with tab3:
        _render_tobii_tab()
