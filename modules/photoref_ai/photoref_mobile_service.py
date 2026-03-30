import json


def _safe_close(cur):
    try:
        cur.close()
    except Exception:
        pass


def ensure_photoref_tables(conn):
    """
    Crea le tabelle base senza assumere colonne extra.
    Versione safe: non crea indici su colonne che potrebbero non esistere.
    """
    if conn is None:
        return

    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS photoref_sessions (
                id SERIAL PRIMARY KEY,
                token TEXT UNIQUE,
                patient_id INTEGER,
                visit_id INTEGER,
                mode TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS photoref_captures (
                id SERIAL PRIMARY KEY,
                session_id INTEGER,
                source TEXT,
                image_bytes BYTEA,
                annotated_image_bytes BYTEA,
                analysis_json JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token
            ON photoref_sessions(token);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id
            ON photoref_captures(session_id);
        """)

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
        }

    ensure_photoref_tables(conn)

    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, token, patient_id, visit_id, mode, status
            FROM photoref_sessions
            WHERE token = %s
            LIMIT 1
        """, (token,))
        row = cur.fetchone()
    finally:
        _safe_close(cur)

    if not row:
        # Fallback test-safe: crea al volo la sessione se non esiste ancora
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO photoref_sessions (token, patient_id, visit_id, mode, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, token, patient_id, visit_id, mode, status
            """, (token, None, None, "BINOCULAR", "created"))
            row = cur.fetchone()
            conn.commit()
        finally:
            _safe_close(cur)

    return {
        "id": row[0],
        "token": row[1],
        "patient_id": row[2],
        "visit_id": row[3],
        "mode": row[4],
        "status": row[5],
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
            SET status = %s,
                updated_at = NOW()
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
        print("SAVE:", result)
        return

    ensure_photoref_tables(conn)

    session_id = session.get("id")

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO photoref_captures
            (session_id, source, image_bytes, annotated_image_bytes, analysis_json)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session_id,
            source,
            image_bytes,
            annotated,
            json.dumps(result),
        ))
        conn.commit()
    finally:
        _safe_close(cur)
