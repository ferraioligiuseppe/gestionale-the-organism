
import os
import sqlite3

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default

def get_conn():
    db_url = _env("DATABASE_URL", "")
    if db_url:
        import psycopg2
        return psycopg2.connect(db_url)
    return sqlite3.connect("vision_manager.db", check_same_thread=False)

def init_db(conn):
    cur = conn.cursor()
    is_pg = conn.__class__.__module__.startswith("psycopg2")

    if is_pg:
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
        CREATE TABLE IF NOT EXISTS valutazioni_visive (
            id SERIAL PRIMARY KEY,
            paziente_id INTEGER REFERENCES pazienti_visivi(id),
            data_valutazione TEXT,
            acuita_visiva TEXT,
            motilita_oculare TEXT,
            stereopsi TEXT,
            conclusioni TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
            id SERIAL PRIMARY KEY,
            paziente_id INTEGER REFERENCES pazienti_visivi(id),
            data_prescrizione TEXT,
            formato TEXT,
            with_cirillo BOOLEAN,
            od_sfera TEXT, od_cil TEXT, od_asse TEXT,
            os_sfera TEXT, os_cil TEXT, os_asse TEXT,
            pdf_bytes BYTEA
        );
        """)
    else:
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
        CREATE TABLE IF NOT EXISTS valutazioni_visive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER,
            data_valutazione TEXT,
            acuita_visiva TEXT,
            motilita_oculare TEXT,
            stereopsi TEXT,
            conclusioni TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER,
            data_prescrizione TEXT,
            formato TEXT,
            with_cirillo INTEGER,
            od_sfera TEXT, od_cil TEXT, od_asse TEXT,
            os_sfera TEXT, os_cil TEXT, os_asse TEXT,
            pdf_bytes BLOB
        )
        """)

    conn.commit()
