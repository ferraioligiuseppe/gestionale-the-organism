
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .analytics_gaze import run_gaze_analytics
from .db_gaze_tracking import init_gaze_tracking_db, insert_gaze_samples_bulk, insert_gaze_session, upsert_gaze_report
from .importer_gaze import import_eye_tracking_file
from .protocols_gaze import list_protocols
from .video_face_pipeline import analyze_face_image, get_video_pipeline_status


def apply_gaze_ui_style() -> None:
    st.markdown(
        """
        <style>
        /* Fix generale per widget in tema scuro */
        div[data-baseweb="select"] > div,
        div[data-baseweb="base-input"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div,
        .stNumberInput input,
        .stDateInput input,
        .stTimeInput input {
            background: #ffffff !important;
            color: #111111 !important;
        }

        .stTextArea textarea::placeholder,
        .stTextInput input::placeholder {
            color: #666666 !important;
        }

        /* Menu aperto selectbox */
        div[role="listbox"],
        div[role="option"] {
            background: #ffffff !important;
            color: #111111 !important;
        }

        /* File uploader */
        [data-testid="stFileUploaderDropzone"],
        [data-testid="stFileUploaderDropzone"] * {
            background: #f8fafc !important;
            color: #111111 !important;
            border-color: #cbd5e1 !important;
        }

        [data-testid="stFileUploaderFileName"],
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] p,
        [data-testid="stFileUploader"] label {
            color: #111111 !important;
        }

        /* Tabs */
        button[data-baseweb="tab"] {
            color: #1f2937 !important;
        }

        /* Expander */
        details, summary {
            color: #111111 !important;
        }

        /* Code block / json */
        .stCodeBlock, .stCodeBlock pre, .stJson {
            color: #111111 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def _render_import_tab(
    paziente_id: int,
    get_conn,
    paziente_label: str | None = None,
) -> None:
    protocol_options = list_protocols()
    protocol_map = {p["label"]: p["key"] for p in protocol_options}

    col1, col2 = st.columns(2)
    with col1:
        selected_protocol_label = st.selectbox(
            "Protocollo clinico",
            options=list(protocol_map.keys()),
            index=0,
            key="gaze_protocol_select",
        )
    with col2:
        vendor = st.selectbox(
            "Vendor import",
            options=["auto", "tobii", "thomson", "generic"],
            index=0,
            key="gaze_vendor_select",
        )

    uploaded_file = st.file_uploader(
        "Carica file eye tracker",
        type=["csv", "xls", "xlsx"],
        accept_multiple_files=False,
        key="gaze_file_uploader",
    )

    session_notes = st.text_area("Note sessione", height=100, key="gaze_session_notes")

    if uploaded_file is None:
        st.info("Carica un file per iniziare.")
        return

    if st.button("Analizza file", type="primary", use_container_width=True, key="gaze_analyze_file_btn"):
        try:
            import_result = import_eye_tracking_file(uploaded_file, forced_vendor=vendor)
        except Exception as exc:
            st.error(f"Errore durante importazione: {exc}")
            return

        validation = import_result.validation
        metadata = import_result.metadata
        df = import_result.df

        st.session_state["gaze_import_df"] = df
        st.session_state["gaze_import_validation"] = validation
        st.session_state["gaze_import_metadata"] = metadata
        st.session_state["gaze_import_protocol_name"] = protocol_map[selected_protocol_label]
        st.session_state["gaze_import_session_notes"] = session_notes

        st.success("Import completato.")

    if "gaze_import_df" not in st.session_state:
        return

    df = st.session_state["gaze_import_df"]
    validation = st.session_state["gaze_import_validation"]
    metadata = st.session_state["gaze_import_metadata"]
    protocol_name = st.session_state["gaze_import_protocol_name"]
    session_notes = st.session_state.get("gaze_import_session_notes", "")

    with st.expander("Validazione import", expanded=True):
        st.json(validation)
        st.json(metadata)

    if not validation.get("valid", False):
        st.error("Il file non ha superato la validazione.")
        return

    st.markdown("### Anteprima dati normalizzati")
    st.dataframe(df.head(50), use_container_width=True)

    analysis = st.session_state.get("gaze_import_analysis")
    if analysis is None or st.session_state.get("gaze_import_analysis_protocol") != protocol_name:
        try:
            analysis = run_gaze_analytics(df=df, protocol_name=protocol_name, metadata=metadata)
            st.session_state["gaze_import_analysis"] = analysis
            st.session_state["gaze_import_analysis_protocol"] = protocol_name
        except Exception as exc:
            st.error(f"Errore durante analisi: {exc}")
            return

    metrics = analysis["metrics"]
    clinical_indexes = analysis["clinical_indexes"]
    distance_metrics = analysis["distance_metrics"]
    summary_json = analysis["summary_json"]
    df_enriched: pd.DataFrame = analysis["samples_enriched"]

    st.markdown("### Metriche cliniche")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Fixation count", metrics.get("fixation_count"))
    m2.metric("Mean fixation ms", metrics.get("mean_fixation_ms"))
    m3.metric("Regressions", metrics.get("regressions"))
    m4.metric("Saccade count", metrics.get("saccade_count"))

    st.markdown("### Indici sintetici")
    c1, c2, c3 = st.columns(3)
    c1.metric("Attention instability", clinical_indexes.get("attention_instability_index"))
    c2.metric("Fatigue index", clinical_indexes.get("fatigue_index"))
    c3.metric("Dyslexia oculomotor risk", clinical_indexes.get("dyslexia_oculomotor_risk"))

    st.markdown("### Distanza visiva")
    st.json(distance_metrics)

    st.markdown("### Summary JSON")
    st.code(json.dumps(summary_json, ensure_ascii=False, indent=2), language="json")

    st.markdown("### Dati arricchiti")
    st.dataframe(df_enriched.head(100), use_container_width=True)

    if st.button("Salva sessione nel database", use_container_width=True, key="gaze_save_file_btn"):
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

            st.success(
                f"Sessione salvata correttamente. Session ID: {session_id} · Campioni inseriti: {inserted_count}"
            )
        except Exception as exc:
            st.error(f"Errore nel salvataggio DB: {exc}")



def _render_video_tab(paziente_id: int, paziente_label: str | None = None) -> None:
    st.markdown("## Videocamera live")
    status = get_video_pipeline_status()

    if not status["mediapipe_available"]:
        st.warning(
            "MediaPipe non è disponibile nell'ambiente Streamlit. La tab resta pronta, ma serve installare `mediapipe`, `opencv-python-headless`, `numpy` e `Pillow`."
        )
    else:
        st.success("Pipeline MediaPipe disponibile.")

    st.info(
        "Questa versione acquisisce uno snapshot dalla camera e calcola metriche base per occhi, bocca e postura del capo."
    )

    protocol_name = st.selectbox(
        "Protocollo videocamera",
        options=["face_eye_oral_screening", "face_posture_screening", "eye_oral_attention"],
        index=0,
        key="video_protocol_select",
    )
    capture_label = st.text_input("Etichetta sessione", value=paziente_label or "", key="video_capture_label")
    session_notes = st.text_area("Note videocamera", height=80, key="video_session_notes")

    camera_file = st.camera_input("Attiva videocamera", key="gaze_camera_input")
    if camera_file is None:
        st.caption("Scatta una foto per avviare l'analisi face/eye/oral.")
        return

    st.image(camera_file, caption="Snapshot acquisito", use_container_width=True)

    if st.button("Analizza snapshot", type="primary", use_container_width=True, key="video_analyze_btn"):
        result = analyze_face_image(
            image_bytes=camera_file.getvalue(),
            protocol_name=protocol_name,
            metadata={
                "paziente_id": paziente_id,
                "paziente_label": paziente_label,
                "capture_label": capture_label,
                "session_notes": session_notes,
            },
        )
        st.session_state["video_face_result"] = result

    result = st.session_state.get("video_face_result")
    if not result:
        return

    if not result.get("ok", False):
        st.error(result.get("error", "Analisi non riuscita."))
        return

    st.markdown("### Preview con landmarks")
    if result.get("overlay_image") is not None:
        st.image(result["overlay_image"], caption="Landmarks face/eye/oral", use_container_width=True)

    metrics = result.get("metrics", {})
    indexes = result.get("indexes", {})
    warnings = result.get("warnings", [])

    st.markdown("### Metriche principali")
    a, b, c, d = st.columns(4)
    a.metric("Eye aperture ratio", metrics.get("eye_aperture_ratio_mean"))
    b.metric("Mouth opening ratio", metrics.get("mouth_opening_ratio"))
    c.metric("Head tilt °", metrics.get("head_tilt_deg"))
    d.metric("Head yaw est.", metrics.get("head_yaw_est"))

    st.markdown("### Indici sintetici")
    i1, i2, i3 = st.columns(3)
    i1.metric("Oculo-postural index", indexes.get("oculo_postural_index"))
    i2.metric("Oral motor index", indexes.get("oral_motor_index"))
    i3.metric("PNEV multimodal index", indexes.get("pnev_multimodal_index"))

    if warnings:
        with st.expander("Warning analisi", expanded=False):
            st.json(warnings)

    st.markdown("### Summary JSON")
    st.code(json.dumps(result.get("summary_json", {}), ensure_ascii=False, indent=2), language="json")

    st.caption(
        "In questa v1 la parte videocamera analizza uno snapshot statico. Il realtime continuo richiederà un componente dedicato frame-by-frame."
    )



def _render_tobii_tab() -> None:
    st.markdown("## Tobii live")
    st.warning(
        "Questa tab è predisposta, ma il collegamento live al sensore richiede l'SDK Tobii nell'ambiente di deploy e il device collegato."
    )
    st.code(
        "pip install tobii-research",
        language="bash",
    )
    st.markdown(
        """
        **Cosa resta da fare per il live reale:**

        - rilevare il sensore collegato
        - aprire la sessione con SDK Tobii
        - acquisire stream gaze in tempo reale
        - salvare i campioni nel formato interno del modulo
        - agganciare il realtime ai protocolli clinici
        """
    )



def ui_gaze_tracking(
    paziente_id: int,
    get_conn,
    paziente_label: str | None = None,
) -> None:
    apply_gaze_ui_style()

    st.subheader("Eye Tracking")
    st.caption("Import multi-vendor, analisi clinica, videocamera base e predisposizione Tobii live.")

    if not paziente_id:
        st.warning("Seleziona prima un paziente.")
        return

    with st.expander("Contesto paziente", expanded=True):
        st.write(f"**Paziente ID:** {paziente_id}")
        st.write(f"**Paziente:** {paziente_label or '-'}")

    tab_import, tab_video, tab_tobii = st.tabs(["Import file", "Videocamera", "Tobii live"])

    with tab_import:
        _render_import_tab(paziente_id=paziente_id, get_conn=get_conn, paziente_label=paziente_label)

    with tab_video:
        _render_video_tab(paziente_id=paziente_id, paziente_label=paziente_label)

    with tab_tobii:
        _render_tobii_tab()
