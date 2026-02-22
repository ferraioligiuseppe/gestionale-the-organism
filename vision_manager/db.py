import os
import sqlite3

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default

def get_conn():
    """Return a DB connection (Postgres if DATABASE_URL set, else local SQLite)."""
    db_url = _env("DATABASE_URL", "")
    if db_url:
        import psycopg2
        # psycopg2 supports connection URIs; keep errors explicit
        return psycopg2.connect(db_url)
    return sqlite3.connect("vision_manager.db", check_same_thread=False)

def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")

def init_db(conn):
    """Initialize schema.

    Defensive: if the caller accidentally passes the function get_conn instead of get_conn(),
    we recover by calling it here.
    """
    if conn is None:
        raise RuntimeError("init_db(conn): conn è None. Verifica get_conn() e DATABASE_URL.")
    if callable(conn):
        conn = conn()

    # Some frameworks pass objects wrapping the connection; ensure cursor exists
    if not hasattr(conn, "cursor"):
        raise TypeError(f"init_db(conn): oggetto non valido ({type(conn)}), manca .cursor().")

    cur = conn.cursor()

    if _is_pg(conn):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pazienti_visivi (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            cognome TEXT,
            data_nascita TEXT,
            note TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS visite_visive (
            id SERIAL PRIMARY KEY,
            paziente_id INTEGER REFERENCES pazienti_visivi(id),
            data_visita TEXT,
            dati_json JSONB,
            pdf_bytes BYTEA
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
            id SERIAL PRIMARY KEY,
            paziente_id INTEGER REFERENCES pazienti_visivi(id),
            data_prescrizione TEXT
        );
        """)

        # --- MIGRAZIONE SOFT (evita UndefinedColumn) ---
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS formato TEXT;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS dati_json JSONB;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS pdf_bytes BYTEA;")

        conn.commit()
        return

    # SQLite
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pazienti_visivi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cognome TEXT,
        data_nascita TEXT,
        note TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS visite_visive (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paziente_id INTEGER,
        data_visita TEXT,
        dati_json TEXT,
        pdf_bytes BLOB
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paziente_id INTEGER,
        data_prescrizione TEXT,
        formato TEXT,
        dati_json TEXT,
        pdf_bytes BLOB
    )
    """)
    conn.commit()
