from __future__ import annotations

import json
from typing import Any, Callable

import pandas as pd
import streamlit as st

from components.gaze_tracker_component import gaze_tracker_component
from .analytics_gaze import run_gaze_analytics
from .db_gaze_tracking import (
    init_gaze_tracking_db,
    insert_gaze_samples_bulk,
    insert_gaze_session,
    upsert_gaze_report,
)


def _normalize_component_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    payload.setdefault("samples", [])
    payload.setdefault("metrics", {})
    payload.setdefault("pnev_indexes", {})
    payload.setdefault("meta", {})
    payload.setdefault("component_status", "idle")
    return payload


def _save_payload_to_db(conn, paziente_id: int, paziente_label: str, payload: dict[str, Any]) -> int:
    init_gaze_tracking_db(conn)
    samples = payload.get("samples") or []
    df = pd.DataFrame(samples)
    if df.empty:
        raise ValueError("Nessun campione disponibile da salvare.")

    session_id = insert_gaze_session(
        conn,
        {
            "paziente_id": paziente_id,
            "paziente_label": paziente_label,
            "protocol_name": payload.get("protocol_name") or "free_observation",
            "source_vendor": "browser_facemesh",
            "source_format": "streamlit_component",
            "source_filename": None,
            "operator_name": None,
            "session_notes": f"Custom component • samples={len(df)} • status={payload.get('component_status')}",
        },
    )
    insert_gaze_samples_bulk(conn, session_id, df)
    analytics = run_gaze_analytics(
        df,
        protocol_name=payload.get("protocol_name") or "reading_standard",
        metadata={
            "source_vendor": "browser_facemesh",
            "source_filename": None,
            "row_count": int(len(df)),
        },
    )
    analytics["summary_json"]["live_metrics"] = payload.get("metrics") or {}
    analytics["summary_json"]["live_pnev_indexes"] = payload.get("pnev_indexes") or {}
    if payload.get("meta", {}).get("snapshot_png_dataurl"):
        analytics["summary_json"]["snapshot_png_dataurl"] = payload["meta"]["snapshot_png_dataurl"]
    upsert_gaze_report(conn, session_id, analytics)
    return session_id


def _load_history(conn, paziente_id: int):
    init_gaze_tracking_db(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.created_at, s.protocol_name, s.source_vendor, r.summary_json
            FROM gaze_sessions s
            LEFT JOIN gaze_reports r ON r.session_id = s.id
            WHERE s.paziente_id = %s
            ORDER BY s.created_at DESC
            LIMIT 20
            """,
            (int(paziente_id),),
        )
        return cur.fetchall() or []


def ui_webcam_browser_v3(
    paziente_id=None,
    paziente_label="",
    get_connection: Callable[[], Any] | None = None,
):
    st.subheader("Eye Tracking / Webcam AI")
    st.caption("Custom Streamlit component: webcam e MediaPipe girano nel browser e il salvataggio avviene in Python.")

    payload = gaze_tracker_component(
        key=f"gaze_component_{paziente_id or 'none'}",
        patient_id=paziente_id,
        patient_label=paziente_label,
        protocol_name="free_observation",
        height=980,
    )
    payload = _normalize_component_payload(payload)
    st.session_state["gaze_component_payload"] = payload

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", payload.get("component_status", "idle"))
    c2.metric("Campioni", len(payload.get("samples") or []))
    c3.metric("Gaze", (payload.get("metrics") or {}).get("gaze_direction", "--"))

    with st.expander("Metriche live", expanded=False):
      st.json({
          "metrics": payload.get("metrics") or {},
          "pnev_indexes": payload.get("pnev_indexes") or {},
          "meta": {k: v for k, v in (payload.get("meta") or {}).items() if k != "snapshot_png_dataurl"},
      })

    if payload.get("samples"):
        st.download_button(
            "Scarica JSON sessione",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name=f"gaze_session_{paziente_id or 'na'}.json",
            mime="application/json",
            use_container_width=True,
        )

    if get_connection is None:
        st.info("Salvataggio DB non attivo in questa schermata: manca il collegamento get_connection().")
        return

    conn = get_connection()
    history = _load_history(conn, int(paziente_id)) if paziente_id else []

    save_disabled = not payload.get("samples")
    if st.button("Salva sessione su DB", type="primary", use_container_width=True, disabled=save_disabled):
        try:
            session_id = _save_payload_to_db(conn, int(paziente_id), paziente_label, payload)
            st.success(f"Sessione salvata con successo. ID sessione: {session_id}")
            st.rerun()
        except Exception as e:
            st.error(f"Errore salvataggio sessione: {e}")

    st.markdown("### Storico sessioni paziente")
    if not history:
        st.caption("Nessuna sessione salvata per questo paziente.")
    else:
        rows = []
        for row in history:
            sid, created_at, protocol_name, source_vendor, summary_json = row
            summary_json = summary_json or {}
            metrics = summary_json.get("metrics") or {}
            live_metrics = summary_json.get("live_metrics") or {}
            rows.append({
                "session_id": sid,
                "created_at": str(created_at),
                "protocol": protocol_name,
                "vendor": source_vendor,
                "fixation_count": metrics.get("fixation_count"),
                "regressions": metrics.get("regressions"),
                "blink_index_live": live_metrics.get("blink_index"),
                "gaze_direction_live": live_metrics.get("gaze_direction"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
