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
    base_url = st.query_params.get("base_url", "") or ""
    if isinstance(base_url, list):
        base_url = base_url[0] if base_url else ""
    if base_url:
        return str(base_url).rstrip("/")
    return "https://testgestionale.streamlit.app"


def _make_mobile_link(token: str) -> str:
    base_url = _base_url_guess()
    return f"{base_url}/?{urlencode({'photoref_token': token})}"


def _cursor(conn):
    return conn.cursor() if conn else None


def _safe_close(cur):
    try:
        cur.close()
    except Exception:
        pass


def _ensure_photoref_tables(conn) -> None:
    if not conn:
        return
    cur = _cursor(conn)
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS photoref_sessions (
            id BIGSERIAL PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            patient_id TEXT NULL,
            visit_id TEXT NULL,
            eye_side TEXT NULL,
            capture_type TEXT NULL,
            operator_user TEXT NULL,
            notes TEXT NULL,
            mode TEXT NULL,
            mobile_link TEXT NULL,
            status TEXT DEFAULT 'created',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ NULL
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token ON photoref_sessions(token);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_sessions_created_at ON photoref_sessions(created_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id ON photoref_captures(session_id);")
        conn.commit()
    finally:
        _safe_close(cur)


def _create_capture_session_db(conn, record: dict) -> dict:
    _ensure_photoref_tables(conn)
    cur = _cursor(conn)
    try:
        cur.execute(
            """
            INSERT INTO photoref_sessions (
                token, patient_id, visit_id, eye_side, capture_type,
                operator_user, notes, mode, mobile_link, status,
                created_at, expires_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (token) DO UPDATE SET
                patient_id = COALESCE(EXCLUDED.patient_id, photoref_sessions.patient_id),
                visit_id = COALESCE(EXCLUDED.visit_id, photoref_sessions.visit_id),
                eye_side = COALESCE(EXCLUDED.eye_side, photoref_sessions.eye_side),
                capture_type = COALESCE(EXCLUDED.capture_type, photoref_sessions.capture_type),
                operator_user = COALESCE(EXCLUDED.operator_user, photoref_sessions.operator_user),
                notes = COALESCE(EXCLUDED.notes, photoref_sessions.notes),
                mode = COALESCE(EXCLUDED.mode, photoref_sessions.mode),
                mobile_link = COALESCE(EXCLUDED.mobile_link, photoref_sessions.mobile_link),
                status = COALESCE(EXCLUDED.status, photoref_sessions.status),
                expires_at = COALESCE(EXCLUDED.expires_at, photoref_sessions.expires_at)
            RETURNING id
            """,
            (
                record.get("token"),
                record.get("patient_id"),
                record.get("visit_id"),
                record.get("eye_side"),
                record.get("capture_type"),
                record.get("operator_user"),
                record.get("notes"),
                record.get("eye_side"),
                record.get("mobile_link"),
                record.get("status", "created"),
                record.get("created_at"),
                record.get("expires_at"),
            ),
        )
        row = cur.fetchone()
        conn.commit()
        record["id"] = row[0] if row else None
        return record
    finally:
        _safe_close(cur)


def _load_recent_sessions_with_capture(conn, limit: int = 20):
    _ensure_photoref_tables(conn)
    cur = _cursor(conn)
    try:
        cur.execute(
            """
            SELECT
                s.id,
                s.token,
                s.patient_id,
                s.visit_id,
                COALESCE(s.eye_side, s.mode) AS eye_side,
                s.capture_type,
                s.operator_user,
                s.notes,
                s.mobile_link,
                s.status,
                s.created_at,
                s.expires_at,
                c.image_bytes,
                c.annotated_image_bytes,
                c.analysis_json,
                c.created_at AS capture_created_at
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
        analysis = r[14]
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
            "eye_side": r[4],
            "capture_type": r[5],
            "operator_user": r[6],
            "notes": r[7],
            "mobile_link": r[8],
            "status": r[9],
            "created_at": r[10].isoformat() if r[10] else None,
            "expires_at": r[11].isoformat() if r[11] else None,
            "image_bytes": r[12],
            "annotated_image_bytes": r[13],
            "analysis_json": analysis,
            "capture_created_at": r[15].isoformat() if r[15] else None,
        })
    return out


def _render_qr(link: str) -> None:
    if not qrcode:
        st.info("QR non disponibile: aggiungi qrcode[pil] a requirements.txt")
        st.code(link, language="text")
        return

    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(buf.getvalue(), width=240, caption="QR Photoref")
    with col2:
        st.write("Scansiona il QR oppure apri il link:")
        st.code(link, language="text")
        st.link_button("Apri su smartphone", link)


def _render_recent_sessions_db(conn, limit: int = 20):
    rows = _load_recent_sessions_with_capture(conn, limit=limit)
    if not rows:
        st.info("Nessuna sessione trovata")
        return

    st.markdown("**Storico sessioni recenti**")
    for row in rows:
        st.markdown(
            f"**{row.get('patient_id','')}** | visita **{row.get('visit_id','')}** | "
            f"{row.get('eye_side','')} | stato **{row.get('status','')}**"
        )

        if row.get("mobile_link"):
            st.code(row["mobile_link"], language="text")

        img = row.get("image_bytes")
        ann = row.get("annotated_image_bytes")
        analysis = row.get("analysis_json")

        if img:
            st.image(img, caption="Ultima foto acquisita", use_container_width=True)

        if ann:
            st.image(ann, caption="Immagine annotata", use_container_width=True)

        if analysis:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("Analisi presente:", "Sì")
            with c2:
                st.write("Quality score:", analysis.get("quality_score", "-"))
            with c3:
                st.write("Riflesso rilevato:", analysis.get("reflex_detected", False))
            if analysis.get("notes"):
                st.caption(f"Note: {analysis.get('notes')}")
            st.json(analysis)

        if row.get("capture_created_at"):
            st.caption(f"Ultima acquisizione: {row.get('capture_created_at')}")
        else:
            st.caption("Nessuna acquisizione ancora salvata per questa sessione.")

        st.divider()


def ui_photoref_session(conn=None, patient_id: str = "", visit_id: str = "", operator_user: str = ""):
    st.subheader("📱 Sessioni smartphone")
    if conn:
        st.caption("Modalità DB Neon attiva")
    else:
        st.caption("Modalità file locale attiva")

    with st.form("photoref_session_form"):
        c1, c2 = st.columns(2)
        patient_id = c1.text_input("Patient ID", value=patient_id)
        visit_id = c2.text_input("Visit ID", value=visit_id)
        c3, c4 = st.columns(2)
        eye_side = c3.selectbox("Lato", ["OD", "OS", "BINOCULAR"], index=2)
        capture_type = c4.selectbox("Tipo acquisizione", ["photoref", "standard_photo", "followup"], index=0)
        notes = st.text_area("Note sessione", value="")
        operator_user = st.text_input("Operatore", value=operator_user)
        submitted = st.form_submit_button("Genera sessione")

    if submitted:
        tok = create_capture_token(expire_minutes=30)
        link = _make_mobile_link(tok["token"])
        record = {
            "token": tok["token"],
            "created_at": tok["created_at"],
            "expires_at": tok["expires_at"],
            "status": "created",
            "patient_id": patient_id or None,
            "visit_id": visit_id or None,
            "eye_side": eye_side,
            "capture_type": capture_type,
            "operator_user": operator_user or None,
            "notes": notes or None,
            "mobile_link": link,
        }

        if conn:
            _create_capture_session_db(conn, record)
        else:
            create_capture_session(BASE_DIR, record)

        st.success("Sessione creata")
        _render_qr(link)
        st.session_state["last_photoref_link"] = link

    if st.session_state.get("last_photoref_link"):
        st.markdown("**Ultimo link generato**")
        st.code(st.session_state["last_photoref_link"], language="text")

    if conn:
        _render_recent_sessions_db(conn, limit=20)
    else:
        rows = list_recent_sessions(BASE_DIR, limit=20)
        if rows:
            st.markdown("**Storico sessioni recenti**")
            for row in rows:
                st.markdown(
                    f"**{row.get('patient_id','')}** | visita **{row.get('visit_id','')}** | "
                    f"{row.get('eye_side','')} | stato **{row.get('status','')}"
                )
                if row.get("mobile_link"):
                    st.code(row["mobile_link"], language="text")
                st.divider()
