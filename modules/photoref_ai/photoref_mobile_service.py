import json


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
        cur.close()

    if not row:
        return None

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

    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE photoref_sessions
            SET status = %s
            WHERE token = %s
        """, (status, token))
        conn.commit()
    finally:
        cur.close()


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
        cur.close()
