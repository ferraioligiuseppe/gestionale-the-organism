from __future__ import annotations
from pathlib import Path
from urllib.parse import urlencode
import io
import json
import streamlit as st

try:
    import qrcode
except Exception:
    qrcode = None

from .photoref_tokens import create_capture_token
from .photoref_db import create_capture_session, list_recent_sessions

BASE_DIR = str(Path(__file__).resolve().parent)

def _base_url_guess() -> str:
    return "https://testgestionale.streamlit.app"

def _make_mobile_link(token: str) -> str:
    return f"{_base_url_guess()}/?{urlencode({'photoref_token': token})}"

def _safe_close(cur):
    try:
        cur.close()
    except Exception:
        pass

def _ensure_tables(conn):
    if not conn:
        return
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS photoref_sessions (
            id BIGSERIAL PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            patient_id TEXT NULL,
            visit_id TEXT NULL,
            mode TEXT NULL,
            status TEXT DEFAULT 'created',
            mobile_link TEXT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS photoref_captures (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NULL,
            source TEXT NULL,
            image_bytes BYTEA NULL,
            annotated_image_bytes BYTEA NULL,
            analysis_json JSONB NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        conn.commit()
    finally:
        _safe_close(cur)

def _create_session_db(conn, record: dict):
    _ensure_tables(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO photoref_sessions (token, patient_id, visit_id, mode, status, mobile_link)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (token) DO UPDATE SET
                patient_id = COALESCE(EXCLUDED.patient_id, photoref_sessions.patient_id),
                visit_id = COALESCE(EXCLUDED.visit_id, photoref_sessions.visit_id),
                mode = COALESCE(EXCLUDED.mode, photoref_sessions.mode),
                status = COALESCE(EXCLUDED.status, photoref_sessions.status),
                mobile_link = COALESCE(EXCLUDED.mobile_link, photoref_sessions.mobile_link)
            RETURNING id
            """,
            (
                record.get("token"),
                record.get("patient_id"),
                record.get("visit_id"),
                record.get("mode"),
                record.get("status", "created"),
                record.get("mobile_link"),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    finally:
        _safe_close(cur)

def _load_recent(conn, limit: int = 20):
    _ensure_tables(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                s.id,
                s.token,
                s.patient_id,
                s.visit_id,
                s.mode,
                s.status,
                s.mobile_link,
                s.created_at,
                c.image_bytes,
                c.annotated_image_bytes,
                c.analysis_json,
                c.created_at
            FROM photoref_sessions s
            LEFT JOIN LATERAL (
                SELECT image_bytes, annotated_image_bytes, analysis_json, created_at
                FROM photoref_captures c
                WHERE c.session_id = s.id
                ORDER BY c.created_at DESC
                LIMIT 1
            ) c ON TRUE
            ORDER BY s.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall() or []
    finally:
        _safe_close(cur)

    out = []
    for r in rows:
        analysis = r[10]
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except Exception:
                pass
        out.append({
            "id": r[0],
            "token": r[1],
            "patient_id": r[2],
            "visit_id": r[3],
            "mode": r[4],
            "status": r[5],
            "mobile_link": r[6],
            "created_at": r[7],
            "image_bytes": r[8],
            "annotated_image_bytes": r[9],
            "analysis_json": analysis,
            "capture_created_at": r[11],
        })
    return out

def _render_qr(link: str):
    if not qrcode:
        st.code(link, language="text")
        return
    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    c1, c2 = st.columns([1,1])
    with c1:
        st.image(buf.getvalue(), width=240, caption="QR Photoref")
    with c2:
        st.code(link, language="text")
        st.link_button("Apri su smartphone", link)

def ui_photoref_session(conn=None, patient_id: str = "", visit_id: str = "", operator_user: str = ""):
    st.subheader("📱 Sessioni smartphone")

    with st.form("photoref_session_form"):
        c1, c2 = st.columns(2)
        patient_id = c1.text_input("Patient ID", value=patient_id)
        visit_id = c2.text_input("Visit ID", value=visit_id)
        mode = st.selectbox("Lato", ["OD", "OS", "BINOCULAR"], index=2)
        submitted = st.form_submit_button("Genera sessione")

    if submitted:
        tok = create_capture_token(expire_minutes=30)
        link = _make_mobile_link(tok["token"])
        record = {
            "token": tok["token"],
            "patient_id": patient_id or None,
            "visit_id": visit_id or None,
            "mode": mode,
            "status": "created",
            "mobile_link": link,
        }
        if conn:
            _create_session_db(conn, record)
        else:
            create_capture_session(BASE_DIR, record)
        st.success("Sessione creata")
        _render_qr(link)
        st.session_state["last_photoref_link"] = link

    if st.session_state.get("last_photoref_link"):
        st.markdown("**Ultimo link generato**")
        st.code(st.session_state["last_photoref_link"], language="text")

    st.button("🔄 Aggiorna elenco")

    if conn:
        rows = _load_recent(conn, limit=20)
        if not rows:
            st.info("Nessuna sessione trovata")
            return
        st.markdown("**Storico sessioni recenti**")
        for row in rows:
            st.markdown(
                f"**{row.get('patient_id','')}** | visita **{row.get('visit_id','')}** | "
                f"{row.get('mode','')} | stato **{row.get('status','')}**"
            )
            if row.get("mobile_link"):
                st.code(row["mobile_link"], language="text")
            if row.get("image_bytes"):
                st.image(row["image_bytes"], caption="Ultima foto acquisita", use_container_width=True)
            if row.get("annotated_image_bytes"):
                st.image(row["annotated_image_bytes"], caption="Immagine annotata", use_container_width=True)
            analysis = row.get("analysis_json")
            if analysis:
                c1, c2, c3 = st.columns(3)
                c1.write("Analisi presente:", "Sì")
                c2.write("Quality score:", analysis.get("quality_score", "-"))
                c3.write("Riflesso rilevato:", analysis.get("reflex_detected", False))
                if analysis.get("notes"):
                    st.caption(f"Note: {analysis.get('notes')}")
            if row.get("capture_created_at"):
                st.caption(f"Ultima acquisizione: {row.get('capture_created_at')}")
            else:
                st.caption("Nessuna acquisizione ancora salvata per questa sessione.")
            st.divider()
    else:
        rows = list_recent_sessions(BASE_DIR, limit=20)
        if rows:
            st.markdown("**Storico sessioni recenti**")
            for row in rows:
                st.write(row)
