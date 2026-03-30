import json


def get_photoref_session_by_token(conn, token):
    if not token:
        return None

    if not conn:
        return {"token": token, "id": None}

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, token, patient_id, visit_id, mode, status
            FROM photoref_sessions
            WHERE token=%s
            LIMIT 1
        """, (token,))
        row = cur.fetchone()

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
    if not conn:
        print("STATUS:", token, status)
        return

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE photoref_sessions
            SET status=%s,
                updated_at=NOW()
            WHERE token=%s
        """, (status, token))
    conn.commit()


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

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO photoref_captures
            (session_id, source, image_bytes, annotated_image_bytes, analysis_json, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
        """, (
            session["id"],
            source,
            image_bytes,
            annotated,
            json.dumps(result),
        ))
    conn.commit()
