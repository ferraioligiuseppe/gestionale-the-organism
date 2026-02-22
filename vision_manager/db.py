import os
import sqlite3

def _add_col_if_missing(conn, table: str, col: str, ddl: str):
    cur = conn.cursor()
    try:
        if conn.__class__.__module__.startswith("psycopg2"):
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s AND column_name=%s
                """,
                (table, col),
            )
            if cur.fetchone() is None:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
                conn.commit()
        else:
            cur.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            if col not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
                conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def get_conn():
    """Return a DB connection (Postgres if DATABASE_URL set, else local SQLite)."""
    db_url = _env("DATABASE_URL", "")
    if db_url:
        import psycopg2
        return psycopg2.connect(db_url)
    return sqlite3.connect("vision_manager.db", check_same_thread=False)


def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def init_db(conn):
    """Initialize schema (works for Postgres + SQLite)."""
    if conn is None:
        raise RuntimeError("init_db(conn): conn è None. Verifica get_conn() e DATABASE_URL.")
    if callable(conn):
        conn = conn()
    if not hasattr(conn, "cursor"):
        raise TypeError(f"init_db(conn): oggetto non valido ({type(conn)}), manca .cursor().")

    cur = conn.cursor()

    if _is_pg(conn):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pazienti_visivi (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                cognome TEXT,
                data_nascita TEXT,
                note TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS visite_visive (
                id SERIAL PRIMARY KEY,
                paziente_id INTEGER REFERENCES pazienti_visivi(id),
                data_visita TEXT,
                dati_json JSONB,
                pdf_bytes BYTEA
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
                id SERIAL PRIMARY KEY,
                paziente_id INTEGER REFERENCES pazienti_visivi(id),
                data_prescrizione TEXT
            );
            """
        )

        # colonne nuove (compatibili)
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS formato TEXT;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS dati_json JSONB;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS pdf_bytes BYTEA;")
        conn.commit()

        # soft-delete (meglio BOOLEAN ma teniamo INTEGER per compatibilità)
        _add_col_if_missing(conn, "visite_visive", "is_deleted", "is_deleted INTEGER DEFAULT 0")
        _add_col_if_missing(conn, "visite_visive", "deleted_at", "deleted_at TEXT")
        return

    # SQLite
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pazienti_visivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cognome TEXT,
            data_nascita TEXT,
            note TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS visite_visive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER,
            data_visita TEXT,
            dati_json TEXT,
            pdf_bytes BLOB
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER,
            data_prescrizione TEXT,
            formato TEXT,
            dati_json TEXT,
            pdf_bytes BLOB
        )
        """
    )
    conn.commit()
