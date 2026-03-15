from __future__ import annotations

import time
from typing import Dict, Any

import av
import cv2
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

        cv2.rectangle(img, (10, 10), (420, 90), (20, 20, 20), -1)
        cv2.putText(img, "Eye Tracking V2.1 - webcam live", (22, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"{w}x{h}", (22, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


def _ensure_state() -> None:
    st.session_state.setdefault("gaze_session_id", None)
    st.session_state.setdefault("gaze_samples_manual", [])
    st.session_state.setdefault("gaze_last_sample_ts", None)

    st.session_state.setdefault("gaze_calibration_running", False)
    st.session_state.setdefault("gaze_calibration_index", 0)
    st.session_state.setdefault("gaze_calibration_started_at", None)
    st.session_state.setdefault("gaze_calibration_completed", False)
    st.session_state.setdefault("gaze_calibration_points_done", [])


def _capture_manual_sample(extra: Dict[str, Any] | None = None) -> None:
    now_ms = int(time.time() * 1000)
    last_ts = st.session_state.get("gaze_last_sample_ts")
    if last_ts and (now_ms - last_ts) < 80:
        return

    payload = {
        "ts_ms": now_ms,
        "gaze_x": None,
        "gaze_y": None,
        "confidence": 0.0,
        "tracking_ok": True,
    }
    if extra:
        payload.update(extra)

    st.session_state["gaze_last_sample_ts"] = now_ms
    st.session_state["gaze_samples_manual"].append(payload)


def _reset_calibration() -> None:
    st.session_state["gaze_calibration_running"] = False
    st.session_state["gaze_calibration_index"] = 0
    st.session_state["gaze_calibration_started_at"] = None
    st.session_state["gaze_calibration_completed"] = False
    st.session_state["gaze_calibration_points_done"] = []


def _start_calibration() -> None:
    st.session_state["gaze_calibration_running"] = True
    st.session_state["gaze_calibration_index"] = 0
    st.session_state["gaze_calibration_started_at"] = time.time()
    st.session_state["gaze_calibration_completed"] = False
    st.session_state["gaze_calibration_points_done"] = []


def _current_target(targets: list[dict]) -> dict | None:
    idx = st.session_state.get("gaze_calibration_index", 0)
    if 0 <= idx < len(targets):
        return targets[idx]
    return None


def _render_target_box(target: dict, screen_w: int, screen_h: int) -> None:
    left_pct = float(target["x"]) / float(screen_w) * 100.0
    top_pct = float(target["y"]) / float(screen_h) * 100.0
    label = target.get("label") or f"P{st.session_state.get('gaze_calibration_index', 0) + 1}"

    st.markdown(
        f"""
        <div style="
            position:relative;
            width:100%;
            height:420px;
            border:1px solid #d9d9d9;
            border-radius:14px;
            background:#ffffff;
            overflow:hidden;
        ">
            <div style="
                position:absolute;
                left:{left_pct}%;
                top:{top_pct}%;
                width:26px;
                height:26px;
                background:#d32020;
                border:4px solid #ffffff;
                border-radius:999px;
                transform:translate(-50%,-50%);
                box-shadow:0 0 0 2px rgba(211,32,32,0.25);
            "></div>
            <div style="
                position:absolute;
                left:{left_pct}%;
                top:calc({top_pct}% + 24px);
                transform:translateX(-50%);
                background:rgba(255,255,255,0.92);
                padding:4px 8px;
                border-radius:10px;
                font-size:12px;
                color:#444;
                border:1px solid #eee;
            ">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _capture_calibration_point(target: dict) -> None:
    idx = st.session_state.get("gaze_calibration_index", 0)
    extra = {
        "target_index": idx,
        "target_label": target.get("label") or f"P{idx + 1}",
        "target_x": target.get("x"),
        "target_y": target.get("y"),
        "event_type": "calibration_point",
    }
    _capture_manual_sample(extra=extra)
    done = list(st.session_state.get("gaze_calibration_points_done", []))
    done.append(extra["target_label"])
    st.session_state["gaze_calibration_points_done"] = done
    st.session_state["gaze_calibration_index"] = idx + 1
    st.session_state["gaze_calibration_started_at"] = time.time()

    # completa se finiti
    if st.session_state["gaze_calibration_index"] >= 9:
        st.session_state["gaze_calibration_running"] = False
        st.session_state["gaze_calibration_completed"] = True


def ui_gaze_tracking(paziente_id: int, get_conn, paziente_label: str = ""):
    _ensure_state()

    st.subheader("👁 Eye Tracking / Gaze Pointer V2.1")
    st.caption(
        "Versione V2.1 con webcam live e calibrazione guidata a 9 punti. "
        "Questa build guida l'operatore punto per punto e salva marcatori di calibrazione; "
        "la stima automatica del gaze verrà aggiunta nello step successivo."
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
        if protocollo == "calibration":
            st.info("Avvia la webcam a sinistra, poi usa 'Avvia calibrazione'. Ogni punto va confermato con 'Acquisisci punto'.")
        else:
            st.info("Apri la webcam qui a sinistra. Se la preview si vede, la parte video è risolta.")

    with side_a:
        ctx = webrtc_streamer(
            key=f"gaze_v21_{protocollo}",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"video": True, "audio": False},
            video_processor_factory=VideoProcessor,
            async_processing=True,
        )

        if ctx.state.playing:
            st.success("Webcam attiva")
        else:
            st.warning("Premi START sulla preview per accendere la webcam")

    if protocollo == "calibration":
        st.markdown("### 🎯 Calibrazione guidata")
        cal_a, cal_b, cal_c = st.columns([1, 1, 1])

        with cal_a:
            if st.button("▶️ Avvia calibrazione", use_container_width=True, disabled=not ctx.state.playing):
                _start_calibration()
                st.rerun()

        with cal_b:
            if st.button("⏹️ Reset calibrazione", use_container_width=True):
                _reset_calibration()
                st.rerun()

        current = _current_target(targets)
        points_done = st.session_state.get("gaze_calibration_points_done", [])

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Punti completati", f"{len(points_done)}/9")
        with m2:
            stato = "completata" if st.session_state.get("gaze_calibration_completed") else ("in corso" if st.session_state.get("gaze_calibration_running") else "non avviata")
            st.metric("Stato calibrazione", stato)
        with m3:
            st.metric("Punto attivo", (st.session_state.get("gaze_calibration_index", 0) + 1) if current else "—")

        if current and st.session_state.get("gaze_calibration_running"):
            _render_target_box(current, screen_w, screen_h)
            st.caption("Chiedi al paziente di fissare il punto rosso, poi premi 'Acquisisci punto'.")
            with cal_c:
                if st.button("📍 Acquisisci punto", use_container_width=True):
                    _capture_calibration_point(current)
                    st.rerun()

        elif st.session_state.get("gaze_calibration_completed"):
            st.success("Calibrazione completata.")
            st.caption("I 9 punti sono stati marcati nella sessione. Ora puoi salvare i campioni e calcolare il report base.")
        else:
            st.caption("La calibrazione non è ancora iniziata.")

        if points_done:
            st.write("Punti acquisiti:", ", ".join(points_done))

    else:
        if ctx.state.playing and st.button("➕ Registra campione manuale", use_container_width=True):
            _capture_manual_sample()
            st.success("Campione aggiunto")

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
            if st.session_state.get("gaze_calibration_completed"):
                report["calibration_score"] = round((len(st.session_state.get("gaze_calibration_points_done", [])) / 9.0) * 100.0, 2)
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
