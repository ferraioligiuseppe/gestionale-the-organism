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

def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")

def init_db(conn):
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

        # se in passato avevi tipo_occhiale, non lo tocchiamo: resta compatibile
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
import json
from datetime import datetime

def create_visita(conn, paziente_id: int, data_visita: str, dati_json: dict, pdf_bytes: bytes):
    """Crea nuova visita + versione 1"""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO visite_visive (paziente_id, data_visita, dati_json, pdf_bytes, current_version, created_at, updated_at, is_deleted)
            VALUES (%s, %s, %s::jsonb, %s, 1, NOW(), NOW(), FALSE)
            RETURNING id
        """, (paziente_id, data_visita, json.dumps(dati_json), psycopg2.Binary(pdf_bytes)))
        visita_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO visite_visive_versioni (visita_id, version_no, dati_json, pdf_bytes, note_modifica, created_at)
            VALUES (%s, 1, %s::jsonb, %s, %s, NOW())
        """, (visita_id, json.dumps(dati_json), psycopg2.Binary(pdf_bytes), "creazione visita"))

    conn.commit()
    return visita_id

def update_visita_new_version(conn, visita_id: int, data_visita: str, dati_json: dict, pdf_bytes: bytes, note: str = "modifica visita"):
    """Non sovrascrive: crea nuova versione e aggiorna la visita 'testa'."""
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(current_version, 1) FROM visite_visive WHERE id=%s", (visita_id,))
        current_version = cur.fetchone()[0] or 1
        new_version = int(current_version) + 1

        # aggiorna "testa"
        cur.execute("""
            UPDATE visite_visive
            SET data_visita=%s,
                dati_json=%s::jsonb,
                pdf_bytes=%s,
                current_version=%s,
                updated_at=NOW()
            WHERE id=%s
        """, (data_visita, json.dumps(dati_json), psycopg2.Binary(pdf_bytes), new_version, visita_id))

        # inserisce versione
        cur.execute("""
            INSERT INTO visite_visive_versioni (visita_id, version_no, dati_json, pdf_bytes, note_modifica, created_at)
            VALUES (%s, %s, %s::jsonb, %s, %s, NOW())
        """, (visita_id, new_version, json.dumps(dati_json), psycopg2.Binary(pdf_bytes), note))

    conn.commit()
    return new_version

def soft_delete_visita(conn, visita_id: int, reason: str = ""):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE visite_visive
            SET is_deleted=TRUE, deleted_at=NOW(), updated_at=NOW()
            WHERE id=%s
        """, (visita_id,))
    conn.commit()

def list_visite_by_paziente(conn, paziente_id: int, include_deleted: bool=False):
    with conn.cursor() as cur:
        if include_deleted:
            cur.execute("""
                SELECT id, data_visita, current_version, is_deleted
                FROM visite_visive
                WHERE paziente_id=%s
                ORDER BY data_visita DESC
            """, (paziente_id,))
        else:
            cur.execute("""
                SELECT id, data_visita, current_version, is_deleted
                FROM visite_visive
                WHERE paziente_id=%s AND is_deleted=FALSE
                ORDER BY data_visita DESC
            """, (paziente_id,))
        return cur.fetchall()

def list_versioni(conn, visita_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, version_no, created_at, note_modifica
            FROM visite_visive_versioni
            WHERE visita_id=%s
            ORDER BY version_no DESC
        """, (visita_id,))
        return cur.fetchall()

def load_version(conn, versione_row_id: int):
    """Carica una versione specifica (per preview / ripristino / export)"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT visita_id, version_no, dati_json, pdf_bytes
            FROM visite_visive_versioni
            WHERE id=%s
        """, (versione_row_id,))
        return cur.fetchone()
