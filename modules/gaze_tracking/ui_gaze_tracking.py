
from __future__ import annotations
import streamlit as st

from .protocols_gaze import PROTOCOLS, DISTANCE_MODES
from .tasks_gaze import build_9_point_calibration, build_fixation_task, build_horizontal_saccades
from .analytics_gaze import compute_basic_metrics
from .db_gaze_tracking import ensure_schema, create_gaze_session, insert_gaze_samples, save_gaze_report, list_sessions
from .distance_gaze import classify_distance_zone

try:
    import av  # noqa: F401
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    WEBRTC_AVAILABLE = True
    WEBRTC_ERROR = None
except Exception as e:
    WEBRTC_AVAILABLE = False
    WEBRTC_ERROR = e

def _build_demo_samples(targets: list[dict], distance_mode: str, target_min: float | None, target_max: float | None) -> list[dict]:
    # Campioni dimostrativi coerenti con la UI corrente.
    samples = []
    ts = 0
    distances = [32, 36, 42, 48, 57, 63] if distance_mode == "multi" else [45, 47, 46, 44, 43]
    for i, target in enumerate(targets[: min(len(targets), 30)]):
        d = distances[i % len(distances)]
        if distance_mode == "guided" and target_min and target_max:
            d = round((target_min + target_max) / 2, 1)
        samples.append({
            "ts_ms": ts,
            "gaze_x": target.get("x"),
            "gaze_y": target.get("y"),
            "confidence": 0.85,
            "tracking_ok": True,
            "distance_cm_est": d,
            "distance_zone": classify_distance_zone(d),
            "target_x": target.get("x"),
            "target_y": target.get("y"),
            "target_label": target.get("label"),
        })
        ts += 120
    return samples

def ui_gaze_tracking(paziente_id: int, get_conn, paziente_label: str = ""):
    st.subheader("👁 Eye Tracking V3.0")
    st.caption("Versione V3: webcam live + distanza dinamica + modalità libera/guidata/multi-distanza.")

    st.session_state.setdefault("gaze_session_id", None)
    st.session_state.setdefault("gaze_component_payload", {})
    st.session_state.setdefault("gaze_v3_samples", [])

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
        distance_mode = st.selectbox("Modalità distanza", list(DISTANCE_MODES.keys()), format_func=lambda x: DISTANCE_MODES.get(x, x))
    with c4:
        operatore = st.text_input("Operatore", value="")

    g1, g2, g3 = st.columns(3)
    with g1:
        distance_cm = st.number_input("Distanza iniziale dichiarata (cm)", min_value=20, max_value=120, value=50)
    with g2:
        target_min = st.number_input("Target min cm", min_value=20, max_value=120, value=35 if distance_mode != "free" else 35)
    with g3:
        target_max = st.number_input("Target max cm", min_value=20, max_value=120, value=55 if distance_mode != "free" else 55)

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
                "distance_mode": distance_mode,
                "distance_target_min_cm": target_min if distance_mode != "free" else None,
                "distance_target_max_cm": target_max if distance_mode != "free" else None,
                "calibration_points": 9 if protocollo == "calibration" else None,
                "status": "draft",
            })
            try:
                conn.close()
            except Exception:
                pass
            st.session_state["gaze_session_id"] = session_id
            st.success(f"Sessione creata: {session_id}")

        st.write("Session ID:", st.session_state.get("gaze_session_id") or "—")
        st.write("Target protocollo:", len(targets))
        st.write("Modalità distanza:", DISTANCE_MODES.get(distance_mode, distance_mode))

        if distance_mode == "guided":
            st.info(f"Fascia obiettivo: {target_min}–{target_max} cm")
        elif distance_mode == "multi":
            st.info("Blocchi consigliati: vicino / medio / lontano")
        else:
            st.info("Distanza libera: osservazione ecologica del comportamento visivo.")

        if st.button("🧪 Genera campioni demo V3", use_container_width=True):
            st.session_state["gaze_v3_samples"] = _build_demo_samples(targets, distance_mode, target_min, target_max)
            st.success("Campioni demo generati.")

    with left:
        st.markdown("### Webcam / Feed")
        if not WEBRTC_AVAILABLE:
            st.error("Dipendenze webcam mancanti.")
            st.exception(WEBRTC_ERROR)
        else:
            webrtc_streamer(
                key=f"gaze_v3_webrtc_{st.session_state.get('gaze_session_id') or 'draft'}",
                mode=WebRtcMode.SENDRECV,
                media_stream_constraints={"video": True, "audio": False},
            )
            st.caption("Premi START nella preview per attivare la webcam. In V3.0 la distanza live è pronta a livello logico; la stima automatica frame-by-frame sarà il prossimo step.")

    samples = st.session_state.get("gaze_v3_samples") or []

    st.markdown("### Distanza dinamica")
    d1, d2, d3, d4 = st.columns(4)
    distances = [s.get("distance_cm_est") for s in samples if s.get("distance_cm_est") is not None]
    if distances:
        current = distances[-1]
        zone = classify_distance_zone(current)
    else:
        current = None
        zone = "unknown"
    with d1:
        st.metric("Distanza attuale", f"{current} cm" if current is not None else "—")
    with d2:
        st.metric("Fascia", zone)
    with d3:
        st.metric("Campioni", len(samples))
    with d4:
        st.metric("Protocollo", PROTOCOLS.get(protocollo, protocollo))

    if samples:
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
        if st.button("📊 Calcola report V3", use_container_width=True, disabled=not (st.session_state.get("gaze_session_id") and samples)):
            report = compute_basic_metrics(samples, screen_w, screen_h, current_targets=targets)
            conn = get_conn()
            ensure_schema(conn)
            save_gaze_report(conn, int(st.session_state["gaze_session_id"]), report)
            try:
                conn.close()
            except Exception:
                pass
            st.success("Report V3 salvato.")
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
