from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from .db_gaze_tracking import init_gaze_tracking_db, list_browser_gaze_sessions, save_browser_gaze_session
from .webcam_browser_v3_embed import get_webcam_browser_v3_html


def _extract_payload_from_upload(uploaded_file):
    if uploaded_file is None:
        return None
    raw = uploaded_file.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def _session_summary(payload: dict) -> dict:
    metrics = payload.get("metrics") or {}
    timeline = payload.get("timeline") or []
    return {
        "Campioni timeline": len(timeline),
        "Gaze": metrics.get("gaze_direction"),
        "Tilt": metrics.get("head_tilt_deg"),
        "Blink": metrics.get("blink_index"),
        "Mouth": metrics.get("mouth_open_ratio"),
    }


def ui_webcam_browser_v3(paziente_id=None, paziente_label="", get_conn=None, **kwargs):
    st.subheader("Eye Tracking / Webcam AI")
    st.caption(
        "La sessione live resta browser-based. Per salvare davvero la sequenza temporale, "
        "esporta il JSON completo dalla webcam e salvalo qui sotto nel database."
    )

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )
    components.html(html, height=1380, scrolling=True)

    st.markdown("### 💾 Salvataggio sessione browser")
    uploaded = st.file_uploader(
        "Carica il JSON esportato dal modulo live (contiene anche la timeline della sessione)",
        type=["json"],
        key=f"gaze_browser_json_{paziente_id}",
    )
    notes = st.text_area("Note sessione", key=f"gaze_browser_notes_{paziente_id}")

    payload = None
    if uploaded is not None:
        try:
            payload = _extract_payload_from_upload(uploaded)
            st.success("JSON sessione letto correttamente.")
            st.json(_session_summary(payload), expanded=False)
        except Exception as e:
            st.error(f"JSON non valido: {e}")

    if st.button("Salva sessione nel DB", key=f"gaze_save_db_{paziente_id}"):
        if payload is None:
            st.warning("Carica prima il JSON esportato dal modulo live.")
        elif get_conn is None:
            st.error("Connessione DB non disponibile nel modulo Eye Tracking.")
        else:
            conn = get_conn()
            try:
                init_gaze_tracking_db(conn)
                sid = save_browser_gaze_session(conn, int(paziente_id), str(paziente_label or ""), payload, notes=notes)
                st.success(f"Sessione salvata con ID {sid}.")
            except Exception as e:
                st.error(f"Errore salvataggio DB: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    if get_conn is not None and paziente_id is not None:
        st.markdown("### 🗂️ Sessioni salvate")
        conn = get_conn()
        try:
            init_gaze_tracking_db(conn)
            rows = list_browser_gaze_sessions(conn, int(paziente_id), limit=20)
        except Exception as e:
            rows = []
            st.error(f"Errore lettura storico sessioni: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not rows:
            st.info("Nessuna sessione salvata per questo paziente.")
        else:
            for row in rows:
                payload_row = row.get("payload_json") or {}
                metrics = row.get("metrics_json") or {}
                if isinstance(payload_row, str):
                    try:
                        payload_row = json.loads(payload_row)
                    except Exception:
                        payload_row = {}
                if isinstance(metrics, str):
                    try:
                        metrics = json.loads(metrics)
                    except Exception:
                        metrics = {}
                title = f"Sessione #{row.get('id')} • {row.get('created_at')}"
                with st.expander(title, expanded=False):
                    st.write({
                        "note": row.get("notes"),
                        "campioni_timeline": len((payload_row or {}).get("timeline") or []),
                        "gaze_direction": metrics.get("gaze_direction"),
                        "head_tilt_deg": metrics.get("head_tilt_deg"),
                        "blink_index": metrics.get("blink_index"),
                    })
                    st.json(payload_row, expanded=False)
                    st.download_button(
                        label="Scarica JSON sessione",
                        data=json.dumps(payload_row, ensure_ascii=False, indent=2),
                        file_name=f"gaze_session_{row.get('id')}.json",
                        mime="application/json",
                        key=f"gaze_dl_{row.get('id')}",
                    )
