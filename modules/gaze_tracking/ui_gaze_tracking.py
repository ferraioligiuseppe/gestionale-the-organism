from __future__ import annotations

import time
from typing import List, Dict, Any

import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer

from .tasks_gaze import build_9_point_calibration, build_fixation_task, build_horizontal_saccades
from .analytics_gaze import compute_basic_metrics
from .db_gaze_tracking import (
    ensure_schema,
    create_gaze_session,
    insert_gaze_samples,
    save_gaze_report,
    list_sessions,
)

PROTOCOLS = {
    "calibration": "Calibrazione 9 punti",
    "fixation_center": "Fissazione centrale",
    "saccadi_orizzontali": "Saccadi orizzontali",
}


class VideoProcessor:
    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        h, w = img.shape[:2]

        # Overlay minimo: serve solo per verificare che la webcam sia viva.
        cv2.rectangle(img, (10, 10), (330, 80), (20, 20, 20), -1)
        cv2.putText(img, "Eye Tracking V2 - webcam live", (22, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"{w}x{h}", (22, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


def _ensure_state() -> None:
    st.session_state.setdefault("gaze_session_id", None)
    st.session_state.setdefault("gaze_samples_manual", [])
    st.session_state.setdefault("gaze_last_sample_ts", None)



def _capture_manual_sample() -> None:
    now_ms = int(time.time() * 1000)
    last_ts = st.session_state.get("gaze_last_sample_ts")
    if last_ts and (now_ms - last_ts) < 80:
        return
    st.session_state["gaze_last_sample_ts"] = now_ms
    st.session_state["gaze_samples_manual"].append(
        {
            "ts_ms": now_ms,
            "gaze_x": None,
            "gaze_y": None,
            "confidence": 0.0,
            "tracking_ok": True,
        }
    )



def ui_gaze_tracking(paziente_id: int, get_conn, paziente_label: str = ""):
    _ensure_state()

    st.subheader("👁 Eye Tracking / Gaze Pointer V2")
    st.caption(
        "Versione V2 con streamlit-webrtc: webcam live stabile per il gestionale TEST. "
        "Questa build accende la camera e raccoglie campioni base; il gaze stimato verrà aggiunto nello step successivo."
    )

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

    side_a, side_b = st.columns([2, 1])
    with side_b:
        st.markdown("### Sessione")
        if st.button("🆕 Crea sessione", use_container_width=True):
            conn = get_conn()
            ensure_schema(conn)
            session_id = create_gaze_session(
                conn,
                {
                    "paziente_id": paziente_id,
                    "operatore": operatore,
                    "protocollo": protocollo,
                    "camera_type": camera_type,
                    "screen_width": screen_w,
                    "screen_height": screen_h,
                    "distance_cm": distance_cm,
                    "calibration_points": 9 if protocollo == "calibration" else None,
                    "status": "draft",
                },
            )
            try:
                conn.close()
            except Exception:
                pass
            st.session_state["gaze_session_id"] = session_id
            st.success(f"Sessione creata: {session_id}")

        st.write("Session ID:", st.session_state.get("gaze_session_id") or "—")
        st.write("Target protocollo:", len(targets))
        st.info("Apri la webcam qui a sinistra. Se la preview si vede, la parte video è risolta.")

    with side_a:
        ctx = webrtc_streamer(
            key=f"gaze_v2_{protocollo}",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": False},
            video_processor_factory=VideoProcessor,
            async_processing=True,
        )

        if ctx.state.playing:
            st.success("Webcam attiva")
            if st.button("➕ Registra campione manuale", use_container_width=True):
                _capture_manual_sample()
                st.success("Campione aggiunto")
        else:
            st.warning("Premi START sulla preview per accendere la webcam")

    samples = st.session_state.get("gaze_samples_manual", [])

    c5, c6, c7 = st.columns(3)
    with c5:
        st.metric("Campioni raccolti", len(samples))
    with c6:
        st.metric("Protocollo", PROTOCOLS.get(protocollo, protocollo))
    with c7:
        st.metric("Webcam", "ON" if ctx.state.playing else "OFF")

    if samples:
        with st.expander("Anteprima campioni", expanded=False):
            st.dataframe(samples[-25:], use_container_width=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("🧹 Azzera campioni", use_container_width=True):
            st.session_state["gaze_samples_manual"] = []
            st.success("Campioni azzerati")
    with b2:
        if st.button(
            "💾 Salva campioni nel DB",
            use_container_width=True,
            disabled=not (st.session_state.get("gaze_session_id") and samples),
        ):
            conn = get_conn()
            ensure_schema(conn)
            inserted = insert_gaze_samples(conn, int(st.session_state["gaze_session_id"]), samples)
            try:
                conn.close()
            except Exception:
                pass
            st.success(f"Campioni salvati: {inserted}")
    with b3:
        if st.button(
            "📊 Calcola report",
            use_container_width=True,
            disabled=not (st.session_state.get("gaze_session_id") and samples),
        ):
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
