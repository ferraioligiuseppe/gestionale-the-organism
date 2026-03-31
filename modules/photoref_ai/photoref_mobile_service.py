import json


def _safe_close(cur):
    try:
        cur.close()
    except Exception:
        pass


def ensure_photoref_tables(conn):
    if conn is None:
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token ON photoref_sessions(token);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id ON photoref_captures(session_id);")
        conn.commit()
    finally:
        _safe_close(cur)


def get_photoref_session_by_token(conn, token):
    if not token:
        return None

    if conn is None:
        return {
            "id": None,
            "token": token,
            "patient_id": None,
            "visit_id": None,
            "mode": "BINOCULAR",
            "status": "created",
            "mobile_link": None,
        }

    ensure_photoref_tables(conn)

    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, token, patient_id, visit_id, mode, status, mobile_link
            FROM photoref_sessions
            WHERE token = %s
            LIMIT 1
        """, (token,))
        row = cur.fetchone()
    finally:
        _safe_close(cur)

    if not row:
        return None

    return {
        "id": row[0],
        "token": row[1],
        "patient_id": row[2],
        "visit_id": row[3],
        "mode": row[4],
        "status": row[5],
        "mobile_link": row[6],
    }


def update_photoref_session_status(conn, token, status):
    if not token:
        return

    if conn is None:
        print("STATUS:", token, status)
        return

    ensure_photoref_tables(conn)

    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE photoref_sessions
            SET status = %s
            WHERE token = %s
        """, (status, token))
        conn.commit()
    finally:
        _safe_close(cur)


def run_photoref_analysis(conn, image, image_bytes, session):
    return {
        "ok": True,
        "quality_score": 0.9,
        "eye_detected": True,
        "reflex_detected": True,
        "anisometropia_suspect": False,
        "notes": "demo",
        "annotated_image_bytes": None,
    }


def save_photoref_capture(conn, session, image_bytes, annotated, result, source):
    if conn is None:
        info = {
            "capture_id": None,
            "session_id": session.get("id") if session else None,
            "image_bytes_len": len(image_bytes) if image_bytes else 0,
            "source": source,
        }
        print("SAVE:", info)
        return info

    ensure_photoref_tables(conn)

    session_id = session.get("id") if session else None
    if not session_id:
        raise ValueError("Sessione Photoref senza id: impossibile salvare la cattura.")

    annotated_bytes = annotated if isinstance(annotated, (bytes, bytearray, memoryview)) else None
    clean_result = dict(result or {})
    if "annotated_image_bytes" in clean_result:
        clean_result["annotated_image_bytes"] = None

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO photoref_captures
            (session_id, source, image_bytes, annotated_image_bytes, analysis_json)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            session_id,
            source,
            bytes(image_bytes) if image_bytes is not None else None,
            bytes(annotated_bytes) if annotated_bytes is not None else None,
            json.dumps(clean_result),
        ))
        row = cur.fetchone()
        conn.commit()
        return {
            "capture_id": row[0] if row else None,
            "session_id": session_id,
            "image_bytes_len": len(image_bytes) if image_bytes else 0,
            "source": source,
        }
    finally:
        _safe_close(cur)
