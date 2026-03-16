from __future__ import annotations

import streamlit as st

from modules.gaze_tracking.analytics_gaze import run_reading_analysis
from modules.gaze_tracking.config_gaze import GAZE_PRESETS, SUPPORTED_IMPORT_TYPES
from modules.gaze_tracking.db_gaze_tracking import (
    init_db_gaze_tracking,
    insert_gaze_session,
    insert_gaze_samples_bulk,
    list_gaze_sessions_by_patient,
    upsert_gaze_report,
)
from modules.gaze_tracking.distance_gaze import add_distance_zone_column, compute_distance_metrics
from modules.gaze_tracking.importer_gaze import (
    dataframe_to_sample_rows,
    load_eye_tracker_file,
    normalize_imported_dataframe,
    validate_imported_dataframe,
)
from modules.gaze_tracking.plots_gaze import (
    build_fixation_histogram_figure,
    build_heatmap_figure,
    build_saccade_histogram_figure,
    build_scanpath_figure,
    build_timeline_figure,
)
from modules.gaze_tracking.protocols_gaze import get_protocol_labels, protocol_label_to_code


def ui_gaze_tracking(conn=None):
    st.subheader("Eye Tracking Clinico")

    if conn is not None:
        try:
            init_db_gaze_tracking(conn)
        except Exception as e:
            st.error(f"Errore init DB gaze_tracking: {e}")
            return

    with st.expander("Nuova sessione", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            paziente_id = st.number_input("Paziente ID", min_value=0, value=0, step=1)
            operatore = st.text_input("Operatore", value="")
            protocol_label = st.selectbox("Protocollo", options=get_protocol_labels())

        with col2:
            camera_type = st.selectbox("Camera type", options=["webcam", "eye_tracker"])
            distance_mode = st.selectbox("Modalità distanza", options=["manual", "estimated", "none"])
            distance_cm = st.number_input("Distanza (cm)", min_value=0.0, value=0.0, step=1.0)

        with col3:
            distance_target_min_cm = st.number_input("Target distanza min (cm)", min_value=0.0, value=0.0, step=1.0)
            distance_target_max_cm = st.number_input("Target distanza max (cm)", min_value=0.0, value=0.0, step=1.0)
            calibration_score = st.number_input("Calibration score", min_value=0.0, value=0.0, step=0.1)

        note = st.text_area("Note sessione", value="", height=80)

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        preset_name = st.selectbox("Preset analisi", options=list(GAZE_PRESETS.keys()), index=0)
    with col_b:
        words_count = st.number_input("Numero parole testo", min_value=0, value=0, step=1)
    with col_c:
        show_debug = st.checkbox("Mostra debug", value=False)

    config = GAZE_PRESETS[preset_name].copy()

    with st.expander("Parametri display / import", expanded=False):
        screen_w_px = st.number_input("Larghezza schermo px", min_value=0, value=1920, step=1)
        screen_h_px = st.number_input("Altezza schermo px", min_value=0, value=1080, step=1)

    uploaded = st.file_uploader("Carica file eye tracker", type=SUPPORTED_IMPORT_TYPES, key="gaze_file_upload")

    if uploaded is None:
        st.info("Carica un file CSV/XLS/XLSX per iniziare.")
        _render_patient_sessions(conn, paziente_id)
        return

    try:
        raw_df = load_eye_tracker_file(uploaded)
    except Exception as e:
        st.error(f"Errore lettura file: {e}")
        return

    st.write("Anteprima file importato")
    st.dataframe(raw_df.head(20), use_container_width=True)

    try:
        df_imported = normalize_imported_dataframe(raw_df, screen_w_px=screen_w_px if screen_w_px > 0 else None, screen_h_px=screen_h_px if screen_h_px > 0 else None)
    except Exception as e:
        st.error(f"Errore normalizzazione file: {e}")
        return

    validation = validate_imported_dataframe(df_imported)
    st.write("Validazione import")
    st.json(validation)

    if not validation["ok"]:
        st.error("File non valido per l'analisi.")
        return

    with st.expander("Preview dataframe normalizzato", expanded=False):
        st.dataframe(df_imported.head(50), use_container_width=True)

    if st.button("Analizza", type="primary"):
        try:
            df_imported = add_distance_zone_column(
                df_imported,
                target_min=distance_target_min_cm if distance_target_min_cm > 0 else None,
                target_max=distance_target_max_cm if distance_target_max_cm > 0 else None,
            )

            result = run_reading_analysis(
                df_samples=df_imported,
                config=config,
                words_count=words_count if words_count > 0 else None,
                screen_w_px=screen_w_px if screen_w_px > 0 else None,
                screen_h_px=screen_h_px if screen_h_px > 0 else None,
            )

            samples_df = result["samples"]
            fix_df = result["fixations"]
            sac_df = result["saccades"]
            lines_df = result["lines"]
            trans_df = result["transitions"]
            metrics = result["metrics"]
            indexes = result["indexes"]
            summary_json = result["summary"]

            distance_metrics = compute_distance_metrics(samples_df)
            metrics.update(distance_metrics)
            summary_json["distance"] = distance_metrics

            st.session_state["gaze_result"] = {
                "samples_df": samples_df,
                "fix_df": fix_df,
                "sac_df": sac_df,
                "lines_df": lines_df,
                "trans_df": trans_df,
                "metrics": metrics,
                "indexes": indexes,
                "summary_json": summary_json,
                "session_payload": {
                    "paziente_id": int(paziente_id) if paziente_id > 0 else None,
                    "operatore": operatore,
                    "protocollo": protocol_label_to_code(protocol_label),
                    "camera_type": camera_type,
                    "distance_cm": distance_cm if distance_cm > 0 else None,
                    "distance_mode": distance_mode,
                    "distance_target_min_cm": distance_target_min_cm if distance_target_min_cm > 0 else None,
                    "distance_target_max_cm": distance_target_max_cm if distance_target_max_cm > 0 else None,
                    "calibration_score": calibration_score if calibration_score > 0 else None,
                    "status": "analyzed",
                    "note": note,
                },
            }

            st.success("Analisi completata.")
        except Exception as e:
            st.error(f"Errore durante l'analisi: {e}")
            return

    gaze_result = st.session_state.get("gaze_result")
    if not gaze_result:
        _render_patient_sessions(conn, paziente_id)
        return

    samples_df = gaze_result["samples_df"]
    fix_df = gaze_result["fix_df"]
    sac_df = gaze_result["sac_df"]
    lines_df = gaze_result["lines_df"]
    trans_df = gaze_result["trans_df"]
    metrics = gaze_result["metrics"]
    indexes = gaze_result["indexes"]
    summary_json = gaze_result["summary_json"]

    st.markdown("---")
    st.subheader("Risultati")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fixations", metrics.get("fixation_count", 0))
    c2.metric("Mean fixation (ms)", metrics.get("mean_fixation_ms", 0))
    c3.metric("Regressions", metrics.get("regression_total", 0))
    c4.metric("WPM", metrics.get("words_per_min") if metrics.get("words_per_min") is not None else "-")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Tracking loss %", metrics.get("tracking_loss_pct", 0))
    d2.metric("Line losses", metrics.get("line_losses", 0))
    d3.metric("Risk", indexes.get("risk_class", "-"))
    d4.metric("Dyslexia oculomotor risk", indexes.get("dyslexia_oculomotor_risk", 0))

    with st.expander("Metriche complete", expanded=False):
        st.json(metrics)

    with st.expander("Indici clinici sintetici", expanded=False):
        st.json(indexes)

    with st.expander("Summary JSON", expanded=False):
        st.json(summary_json)

    tabs = st.tabs(["Fixations", "Saccades", "Transitions", "Lines", "Heatmap", "Scanpath", "Histograms", "Timeline"])

    with tabs[0]:
        st.dataframe(fix_df, use_container_width=True)
    with tabs[1]:
        st.dataframe(sac_df, use_container_width=True)
    with tabs[2]:
        st.dataframe(trans_df, use_container_width=True)
    with tabs[3]:
        st.dataframe(lines_df, use_container_width=True)
    with tabs[4]:
        st.pyplot(build_heatmap_figure(fix_df))
    with tabs[5]:
        st.pyplot(build_scanpath_figure(fix_df, trans_df))
    with tabs[6]:
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.pyplot(build_fixation_histogram_figure(fix_df))
        with col_h2:
            st.pyplot(build_saccade_histogram_figure(sac_df))
    with tabs[7]:
        st.pyplot(build_timeline_figure(samples_df, fix_df, trans_df))

    if show_debug:
        with st.expander("Debug dataframes", expanded=False):
            st.write("Samples")
            st.dataframe(samples_df.head(100), use_container_width=True)
            st.write("Fixations")
            st.dataframe(fix_df.head(100), use_container_width=True)
            st.write("Transitions")
            st.dataframe(trans_df.head(100), use_container_width=True)

    st.markdown("---")
    st.subheader("Salvataggio su database")

    if conn is None:
        st.warning("Connessione DB non disponibile. Analisi eseguita solo in memoria.")
        return

    if st.button("Salva sessione + campioni + report"):
        try:
            session_payload = gaze_result["session_payload"]
            session_id = insert_gaze_session(conn, session_payload)

            sample_rows = dataframe_to_sample_rows(samples_df)
            inserted_count = insert_gaze_samples_bulk(conn, session_id, sample_rows)

            report_payload = {
                "fixation_total_ms": metrics.get("fixation_total_ms"),
                "mean_fixation_ms": metrics.get("mean_fixation_ms"),
                "saccade_count": metrics.get("saccade_count"),
                "target_hit_rate": None,
                "tracking_loss_pct": metrics.get("tracking_loss_pct"),
                "center_bias_pct": None,
                "distance_mean_cm": metrics.get("distance_mean_cm"),
                "distance_min_cm": metrics.get("distance_min_cm"),
                "distance_max_cm": metrics.get("distance_max_cm"),
                "distance_std_cm": metrics.get("distance_std_cm"),
                "time_near_pct": metrics.get("time_near_pct"),
                "time_mid_pct": metrics.get("time_mid_pct"),
                "time_far_pct": metrics.get("time_far_pct"),
                "summary_json": summary_json,
            }
            upsert_gaze_report(conn, session_id, report_payload)

            st.success(f"Sessione salvata. session_id={session_id} | campioni inseriti={inserted_count}")
        except Exception as e:
            st.error(f"Errore salvataggio DB: {e}")

    _render_patient_sessions(conn, paziente_id)


def _render_patient_sessions(conn, paziente_id: int):
    if conn is None or paziente_id <= 0:
        return

    with st.expander("Sessioni precedenti del paziente", expanded=False):
        try:
            sessions = list_gaze_sessions_by_patient(conn, int(paziente_id))
            if not sessions:
                st.info("Nessuna sessione trovata.")
                return
            st.dataframe(sessions, use_container_width=True)
        except Exception as e:
            st.error(f"Errore lettura sessioni: {e}")
