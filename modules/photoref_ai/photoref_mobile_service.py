import json
from typing import Optional


def _cursor(conn):
    return conn.cursor() if conn else None


def ensure_photoref_tables(conn) -> None:
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
            expires_at TIMESTAMPTZ NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS photoref_captures (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NULL REFERENCES photoref_sessions(id) ON DELETE SET NULL,
            token TEXT NULL,
            source TEXT,
            image_bytes BYTEA,
            annotated_image_bytes BYTEA,
            analysis_json JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token ON photoref_sessions(token);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id ON photoref_captures(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_captures_token ON photoref_captures(token);")
        conn.commit()
    finally:
        cur.close()


def get_photoref_session_by_token(conn, token):
    if not token:
        return None

    if not conn:
        return {
            "id": None,
            "token": token,
            "patient_id": None,
            "visit_id": None,
            "eye_side": "BINOCULAR",
            "capture_type": "photoref",
            "operator_user": None,
            "notes": None,
            "mode": "BINOCULAR",
            "mobile_link": None,
            "status": "created",
        }

    ensure_photoref_tables(conn)
    cur = _cursor(conn)
    try:
        cur.execute(
            """
            SELECT id, token, patient_id, visit_id, eye_side, capture_type,
                   operator_user, notes, mode, mobile_link, status, created_at, expires_at
            FROM photoref_sessions
            WHERE token = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (token,),
        )
        row = cur.fetchone()
    finally:
        cur.close()

    if not row:
        return None

    return {
        "id": row[0],
        "token": row[1],
        "patient_id": row[2],
        "visit_id": row[3],
        "eye_side": row[4],
        "capture_type": row[5],
        "operator_user": row[6],
        "notes": row[7],
        "mode": row[8] or row[4] or "BINOCULAR",
        "mobile_link": row[9],
        "status": row[10],
        "created_at": row[11].isoformat() if row[11] else None,
        "expires_at": row[12].isoformat() if row[12] else None,
    }


def update_photoref_session_status(conn, token, status):
    if not token:
        return

    if not conn:
        print("STATUS:", token, status)
        return

    ensure_photoref_tables(conn)
    cur = _cursor(conn)
    try:
        cur.execute(
            """
            UPDATE photoref_sessions
            SET status = %s,
                updated_at = NOW()
            WHERE token = %s
            """,
            (status, token),
        )
        conn.commit()
    finally:
        cur.close()


def run_photoref_analysis(conn, image, image_bytes, session):
    width, height = image.size
    ratio = round(min(width, height) / max(width, height), 3) if max(width, height) else 0
    return {
        "ok": True,
        "quality_score": ratio,
        "eye_detected": True,
        "reflex_detected": True,
        "anisometropia_suspect": False,
        "notes": "demo",
        "annotated_image_bytes": None,
    }


def save_photoref_capture(conn, session, image_bytes, annotated, result, source):
    if not conn:
        print("SAVE:", result)
        return

    ensure_photoref_tables(conn)
    clean_result = dict(result or {})
    if isinstance(clean_result.get("annotated_image_bytes"), (bytes, bytearray)):
        clean_result["annotated_image_bytes"] = None

    cur = _cursor(conn)
    try:
        cur.execute(
            """
            INSERT INTO photoref_captures
            (session_id, token, source, image_bytes, annotated_image_bytes, analysis_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
            """,
            (
                session.get("id"),
                session.get("token"),
                source,
                image_bytes,
                annotated,
                json.dumps(clean_result),
            ),
        )
        conn.commit()
    finally:
        cur.close()
