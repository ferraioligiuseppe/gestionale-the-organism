from __future__ import annotations
import streamlit as st

from components.gaze_tracker_component import gaze_tracker_component
from .tasks_gaze import build_9_point_calibration, build_fixation_task, build_horizontal_saccades
from .analytics_gaze import compute_basic_metrics
from .db_gaze_tracking import ensure_schema, create_gaze_session, insert_gaze_samples, save_gaze_report, list_sessions


PROTOCOLS = {
    "calibration": "Calibrazione 9 punti",
    "fixation_center": "Fissazione centrale",
    "saccadi_orizzontali": "Saccadi orizzontali",
}


def ui_gaze_tracking(paziente_id: int, get_conn, paziente_label: str = ""):
    st.subheader("👁 Eye Tracking / Gaze Pointer")
    st.caption("Prototype webcam-based con WebGazer. Buono per valutazione funzionale, non equivalente a un eye tracker clinico dedicato.")

    st.session_state.setdefault("gaze_session_id", None)
    st.session_state.setdefault("gaze_component_payload", None)

    conn = get_conn()
    ensure_schema(conn)
    try:
        conn.close()
    except Exception:
        pass

    if paziente_label:
        st.markdown(f"**Paziente:** {paziente_label}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        protocollo = st.selectbox("Protocollo", list(PROTOCOLS.keys()), format_func=lambda x: PROTOCOLS.get(x, x))
    with c2:
        camera_type = st.selectbox("Camera", ["webcam_integrata", "webcam_usb"])
    with c3:
        distance_cm = st.number_input("Distanza monitor (cm)", min_value=20, max_value=120, value=50)
    with c4:
        operatore = st.text_input("Operatore", value="")

    screen_w = 1280
    screen_h = 720

    if protocollo == "calibration":
        targets = build_9_point_calibration(screen_w, screen_h)
    elif protocollo == "fixation_center":
        targets = build_fixation_task(screen_w, screen_h)
    else:
        targets = build_horizontal_saccades(screen_w, screen_h)

    left, right = st.columns([2, 1])
    with right:
        st.markdown("### Sessione")
        if st.button("🆕 Crea sessione", use_container_width=True):
            conn = get_conn()
            ensure_schema(conn)
            session_id = create_gaze_session(conn, {
                "paziente_id": paziente_id,
                "operatore": operatore,
                "protocollo": protocollo,
                "camera_type": camera_type,
                "screen_width": screen_w,
                "screen_height": screen_h,
                "distance_cm": distance_cm,
                "calibration_points": 9 if protocollo == "calibration" else None,
                "status": "draft",
            })
            try:
                conn.close()
            except Exception:
                pass
            st.session_state["gaze_session_id"] = session_id
            st.success(f"Sessione creata: {session_id}")

        session_id = st.session_state.get("gaze_session_id")
        st.write("Session ID:", session_id or "—")
        st.write("Target protocollo:", len(targets))
        st.info("Premi Avvia dentro il riquadro. Poi Stop. Infine salva campioni e calcola report.")

    with left:
        payload = gaze_tracker_component(
            key=f"gaze_tracking_{st.session_state.get('gaze_session_id') or 'draft'}_{protocollo}",
            mode=protocollo,
            task={
                "screen_width": screen_w,
                "screen_height": screen_h,
                "targets": targets,
            },
            height=760,
        )
        st.session_state["gaze_component_payload"] = payload

    payload = st.session_state.get("gaze_component_payload") or {}
    samples = payload.get("samples") or []

    c5, c6, c7 = st.columns(3)
    with c5:
        st.metric("Campioni live", payload.get("sample_count", len(samples)))
    with c6:
        st.metric("Calibration score", payload.get("calibration_score") or "—")
    with c7:
        st.metric("Stato componente", payload.get("component_status") or "idle")

    if samples:
        with st.expander("Anteprima campioni", expanded=False):
            st.dataframe(samples[-25:], use_container_width=True)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Salva campioni nel DB", use_container_width=True, disabled=not (st.session_state.get("gaze_session_id") and samples)):
            conn = get_conn()
            ensure_schema(conn)
            inserted = insert_gaze_samples(conn, int(st.session_state["gaze_session_id"]), samples)
            try:
                conn.close()
            except Exception:
                pass
            st.success(f"Campioni salvati: {inserted}")
    with b2:
        if st.button("📊 Calcola report", use_container_width=True, disabled=not (st.session_state.get("gaze_session_id") and samples)):
            report = compute_basic_metrics(samples, screen_w, screen_h, current_targets=targets)
            conn = get_conn()
            ensure_schema(conn)
            save_gaze_report(conn, int(st.session_state["gaze_session_id"]), report)
            try:
                conn.close()
            except Exception:
                pass
            st.success("Report salvato.")
            st.json(report)

    st.markdown("### Storico sessioni")
    conn = get_conn()
    ensure_schema(conn)
    rows = list_sessions(conn, paziente_id)
    try:
        conn.close()
    except Exception:
        pass
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.caption("Nessuna sessione ancora salvata per questo paziente.")
