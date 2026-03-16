from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .analytics_gaze import run_gaze_analytics
from .db_gaze_tracking import init_gaze_tracking_db, insert_gaze_samples_bulk, insert_gaze_session, upsert_gaze_report
from .importer_gaze import import_eye_tracking_file
from .protocols_gaze import list_protocols


def apply_gaze_ui_style() -> None:
    st.markdown(
        """
        <style>
        /* Text inputs */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input,
        div[data-testid="stTimeInput"] input {
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
        }

        /* Selectbox / multiselect */
        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] input {
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
        }

        /* Uploaded file box */
        section[data-testid="stFileUploader"] {
            background-color: rgba(255,255,255,0.04);
            padding: 0.5rem;
            border-radius: 0.75rem;
        }

        /* JSON / code blocks */
        div[data-testid="stCodeBlock"] * {
            color: inherit !important;
        }

        /* Dataframe readability */
        div[data-testid="stDataFrame"] {
            background-color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def ui_gaze_tracking(
    paziente_id: int,
    get_conn,
    paziente_label: str | None = None,
) -> None:
    apply_gaze_ui_style()

    st.subheader("Eye Tracking")
    st.caption("Import multi-vendor, analisi clinica e salvataggio sessione.")

    if not paziente_id:
        st.warning("Seleziona prima un paziente.")
        return

    with st.expander("Contesto paziente", expanded=True):
        st.write(f"**Paziente ID:** {paziente_id}")
        st.write(f"**Paziente:** {paziente_label or '-'}")

    protocol_options = list_protocols()
    protocol_map = {p["label"]: p["key"] for p in protocol_options}

    col1, col2 = st.columns(2)
    with col1:
        selected_protocol_label = st.selectbox(
            "Protocollo clinico",
            options=list(protocol_map.keys()),
            index=0,
        )
    with col2:
        vendor = st.selectbox(
            "Vendor import",
            options=["auto", "tobii", "thomson", "generic"],
            index=0,
        )

    uploaded_file = st.file_uploader(
        "Carica file eye tracker",
        type=["csv", "xls", "xlsx"],
        accept_multiple_files=False,
    )

    session_notes = st.text_area("Note sessione", height=100)

    if uploaded_file is None:
        st.info("Carica un file per iniziare.")
        return

    if st.button("Analizza file", type="primary", use_container_width=True):
        try:
            import_result = import_eye_tracking_file(uploaded_file, forced_vendor=vendor)
        except Exception as exc:
            st.error(f"Errore durante importazione: {exc}")
            return

        validation = import_result.validation
        metadata = import_result.metadata
        df = import_result.df

        st.success("Import completato.")

        with st.expander("Validazione import", expanded=True):
            st.json(validation)
            st.json(metadata)

        if not validation.get("valid", False):
            st.error("Il file non ha superato la validazione.")
            return

        st.markdown("### Anteprima dati normalizzati")
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

        if st.button("Salva sessione nel database", use_container_width=True):
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
                    f"Sessione salvata correttamente. "
                    f"Session ID: {session_id} · Campioni inseriti: {inserted_count}"
                )
            except Exception as exc:
                st.error(f"Errore nel salvataggio DB: {exc}")
