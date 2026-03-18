from __future__ import annotations

import base64
import json

import streamlit as st
import streamlit.components.v1 as components

from .db_gaze_tracking import list_gaze_sessions_for_patient, save_browser_gaze_payload
from .webcam_browser_v3_embed import get_webcam_browser_v3_html


def _decode_payload(token: str) -> dict:
    token = (token or '').strip()
    if not token:
        return {}
    pad = '=' * ((4 - len(token) % 4) % 4)
    raw = base64.urlsafe_b64decode((token + pad).encode('utf-8'))
    return json.loads(raw.decode('utf-8'))


def _delete_query_param(key: str):
    try:
        qp = st.query_params
        if key in qp:
            del qp[key]
    except Exception:
        pass


def _maybe_handle_direct_save(paziente_id=None, paziente_label='', get_conn=None):
    try:
        qp = st.query_params
        payload_token = qp.get('gaze_save', '')
    except Exception:
        payload_token = ''

    if not payload_token or not get_conn:
        return

    try:
        payload = _decode_payload(str(payload_token))
        payload_pid = payload.get('patient_id') or payload.get('paziente_id')
        if paziente_id is not None and payload_pid is not None and int(payload_pid) != int(paziente_id):
            raise ValueError(f'Payload paziente non coerente: {payload_pid} != {paziente_id}')

        conn = get_conn()
        try:
            session_id = save_browser_gaze_payload(conn, payload)
        finally:
            try:
                conn.close()
            except Exception:
                pass

        st.session_state['gaze_save_result'] = f'✅ Sessione salvata nel DB con ID {session_id}'
    except Exception as e:
        st.session_state['gaze_save_result'] = f'❌ Errore salvataggio diretto: {e}'
    finally:
        _delete_query_param('gaze_save')
        _delete_query_param('gaze_nonce')
        st.rerun()


def _render_recent_sessions(paziente_id, get_conn=None):
    if not paziente_id or not get_conn:
        return
    try:
        conn = get_conn()
        try:
            rows = list_gaze_sessions_for_patient(conn, int(paziente_id), limit=10)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception as e:
        st.caption(f'Storico non disponibile: {e}')
        return

    if not rows:
        st.caption('Nessuna sessione salvata ancora per questo paziente.')
        return

    st.markdown('### Storico sessioni salvate')
    for r in rows:
        if isinstance(r, dict):
            sid = r.get('id')
            created_at = r.get('created_at')
            protocol_name = r.get('protocol_name')
            operator_name = r.get('operator_name')
            metrics = r.get('metrics_json') or {}
            indexes = r.get('clinical_indexes_json') or {}
        else:
            sid, created_at, protocol_name, operator_name, metrics, indexes = r
        with st.expander(f'Sessione #{sid} • {created_at}', expanded=False):
            st.write({
                'protocol_name': protocol_name,
                'operator_name': operator_name,
                'metrics': metrics or {},
                'pnev_indexes': indexes or {},
            })


def ui_webcam_browser_v3(paziente_id=None, paziente_label='', get_conn=None, **kwargs):
    _maybe_handle_direct_save(paziente_id=paziente_id, paziente_label=paziente_label, get_conn=get_conn)

    st.subheader('Eye Tracking / Webcam AI')
    res = st.session_state.pop('gaze_save_result', None)
    if res:
        if res.startswith('✅'):
            st.success(res)
        else:
            st.error(res)

    st.caption('Usa “Salva su DB” per registrare direttamente la sessione attuale senza passare dall’export JSON.')

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )

    components.html(html, height=1320, scrolling=True)
    _render_recent_sessions(paziente_id=paziente_id, get_conn=get_conn)
