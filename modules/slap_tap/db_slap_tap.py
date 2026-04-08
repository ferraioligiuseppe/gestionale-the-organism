def ensure_slap_tap_tables(conn):
    if conn is None:
        return

    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS slap_tap_sessions (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            sequence_json JSONB,
            response_json JSONB,
            accuracy NUMERIC
        )
        """)
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
