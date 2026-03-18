# modules/gaze_tracking/ui_webcam_browser_v3.py

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .db_gaze_tracking import (
    init_gaze_tracking_db,
    list_gaze_sessions_summary,
    save_browser_gaze_session,
)
from .webcam_browser_v3_embed import get_webcam_browser_v3_html


def ui_webcam_browser_v3(paziente_id=None, paziente_label="", get_conn=None, **kwargs):
    st.subheader("Eye Tracking / Webcam AI")

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )
    components.html(html, height=1250, scrolling=True)

    st.markdown("### 💾 Salvataggio sessione su database")
    st.caption(
        "Esporta il JSON dal modulo live e importalo qui per salvarlo nello storico paziente su Neon."
    )

    payload = _payload_input_ui()
    if not get_conn:
        st.info("Salvataggio DB non configurato in questa schermata.")
        return

    operator_default = ""
    try:
        operator_default = (
            (st.session_state.get("user") or {}).get("username")
            or st.session_state.get("username")
            or ""
        )
    except Exception:
        operator_default = ""

    col1, col2 = st.columns(2)
    with col1:
        operator_name = st.text_input(
            "Operatore",
            value=operator_default,
            key=f"gaze_operator_{paziente_id}",
        )
    with col2:
        snapshot_data_url = st.text_input(
            "Snapshot data URL (opzionale)",
            value="",
            key=f"gaze_snapshot_{paziente_id}",
            help="Puoi lasciarlo vuoto. È utile solo se in futuro vuoi archiviare anche l'immagine.",
        )

    session_notes = st.text_area(
        "Note sessione",
        key=f"gaze_notes_{paziente_id}",
        placeholder="Protocollo eseguito, osservazioni cliniche, contesto della registrazione...",
        height=110,
    )

    save_col, hist_col = st.columns([1, 1])
    with save_col:
        if st.button("Salva sessione nel DB", key=f"gaze_save_btn_{paziente_id}", use_container_width=True):
            if paziente_id is None:
                st.error("Paziente non selezionato.")
            elif payload is None:
                st.error("Importa o incolla prima un JSON valido.")
            else:
                try:
                    conn = get_conn()
                    init_gaze_tracking_db(conn)
                    session_id = save_browser_gaze_session(
                        conn,
                        paziente_id=int(paziente_id),
                        paziente_label=str(paziente_label or f"Paziente {paziente_id}"),
                        payload=payload,
                        operator_name=operator_name or None,
                        session_notes=session_notes or None,
                        snapshot_data_url=snapshot_data_url or None,
                    )
                    try:
                        conn.close()
                    except Exception:
                        pass
                    st.success(f"Sessione salvata correttamente. ID sessione: {session_id}")
                    st.rerun()
                except Exception as e:
                    st.error("Errore durante il salvataggio della sessione.")
                    st.exception(e)

    st.markdown("### 🕘 Storico sessioni paziente")
    with hist_col:
        limit = st.number_input(
            "Numero sessioni da mostrare",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            key=f"gaze_hist_limit_{paziente_id}",
        )
    _render_history(get_conn=get_conn, paziente_id=paziente_id, limit=int(limit))


def _payload_input_ui():
    uploaded = st.file_uploader(
        "Carica il JSON esportato",
        type=["json"],
        key="gaze_payload_upload",
        help="Usa il pulsante 'Export JSON' del modulo live, poi carica qui il file.",
    )
    pasted = st.text_area(
        "Oppure incolla qui il JSON",
        key="gaze_payload_text",
        height=220,
        placeholder='{"patient_id": 1, "metrics": {...}, "pnev_indexes": {...}}',
    )

    payload = None
    source = None

    if uploaded is not None:
        try:
            payload = json.loads(uploaded.getvalue().decode("utf-8"))
            source = uploaded.name
        except Exception as e:
            st.error(f"JSON caricato non valido: {e}")
            return None

    elif pasted.strip():
        try:
            payload = json.loads(pasted.strip())
            source = "testo incollato"
        except Exception as e:
            st.error(f"JSON incollato non valido: {e}")
            return None

    if payload:
        st.success(f"Payload pronto da salvare ({source}).")
        with st.expander("Anteprima payload importato", expanded=False):
            st.json(payload)
    return payload


def _render_history(*, get_conn, paziente_id, limit: int):
    if not get_conn or paziente_id is None:
        st.info("Storico non disponibile.")
        return

    try:
        conn = get_conn()
        rows = list_gaze_sessions_summary(conn, int(paziente_id), limit=limit)
        try:
            conn.close()
        except Exception:
            pass
    except Exception as e:
        st.error("Errore nel recupero dello storico sessioni.")
        st.exception(e)
        return

    if not rows:
        st.info("Nessuna sessione salvata per questo paziente.")
        return

    preview = []
    for r in rows:
        metrics = r.get("metrics_json") or {}
        indexes = r.get("clinical_indexes_json") or {}
        preview.append(
            {
                "sessione_id": r.get("id"),
                "data": r.get("created_at"),
                "operatore": r.get("operator_name"),
                "protocollo": r.get("protocol_name"),
                "durata_sec": r.get("session_duration_sec"),
                "gaze_direction": metrics.get("gaze_direction"),
                "head_tilt_deg": metrics.get("head_tilt_deg"),
                "blink_index": metrics.get("blink_index"),
                "facial_balance_index": indexes.get("facial_balance_index"),
                "gaze_stability_index": indexes.get("gaze_stability_index"),
                "note": r.get("session_notes"),
            }
        )

    st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

    selected_id = st.selectbox(
        "Dettaglio sessione",
        options=[r["id"] for r in rows],
        format_func=lambda x: f"Sessione {x}",
        key=f"gaze_session_detail_{paziente_id}",
    )
    selected = next((r for r in rows if r["id"] == selected_id), None)
    if selected:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Metriche**")
            st.json(selected.get("metrics_json") or {})
        with c2:
            st.markdown("**Indici PNEV**")
            st.json(selected.get("clinical_indexes_json") or {})
