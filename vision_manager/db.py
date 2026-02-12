import os
import sqlite3
import json
from typing import Any, Dict, List, Optional, Tuple


def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def get_conn():
    """Create a DB connection.

    - If DATABASE_URL is set -> PostgreSQL (psycopg2)
    - Otherwise -> SQLite (vision_manager.db)
    """
    db_url = _env("DATABASE_URL", "")
    if db_url:
        import psycopg2
        return psycopg2.connect(db_url)
    return sqlite3.connect("vision_manager.db", check_same_thread=False)


def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def init_db(conn):
    """Create base tables if missing.

    NOTE: In PostgreSQL we only create the base tables;
    versioning/soft-delete is managed by your DB migration/trigger scripts.
    """
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

        # soft migration for existing columns
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS formato TEXT;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS dati_json JSONB;")
        cur.execute("ALTER TABLE prescrizioni_occhiali ADD COLUMN IF NOT EXISTS pdf_bytes BYTEA;")

        conn.commit()
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


# =========================
# VISITE VISIVE – VERSIONING HELPERS (read-only)
# =========================


def list_visite_by_paziente(conn, paziente_id: int, include_deleted: bool = False):
    """Return visits list for a patient.

    Returns rows as tuples (sqlite) or tuples (pg cursor default).
    """
    cur = conn.cursor()
    if _is_pg(conn):
        if include_deleted:
            cur.execute(
                """
                SELECT id, data_visita, COALESCE(current_version, 1) AS current_version, COALESCE(is_deleted, FALSE) AS is_deleted
                FROM visite_visive
                WHERE paziente_id = %s
                ORDER BY data_visita DESC NULLS LAST, id DESC;
                """,
                (paziente_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, data_visita, COALESCE(current_version, 1) AS current_version, COALESCE(is_deleted, FALSE) AS is_deleted
                FROM visite_visive
                WHERE paziente_id = %s AND COALESCE(is_deleted, FALSE) = FALSE
                ORDER BY data_visita DESC NULLS LAST, id DESC;
                """,
                (paziente_id,),
            )
        return cur.fetchall()

    # sqlite
    if include_deleted:
        cur.execute(
            """
            SELECT id, data_visita, 1 as current_version, 0 as is_deleted
            FROM visite_visive
            WHERE paziente_id = ?
            ORDER BY data_visita DESC, id DESC;
            """,
            (paziente_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, data_visita, 1 as current_version, 0 as is_deleted
            FROM visite_visive
            WHERE paziente_id = ?
            ORDER BY data_visita DESC, id DESC;
            """,
            (paziente_id,),
        )
    return cur.fetchall()


def get_visita_corrente_pg(conn, visita_id: int):
    """Load current version payload from PostgreSQL (dati_json + pdf_bytes)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.id, v.paziente_id, v.data_visita, v.current_version,
               vv.version_no, vv.dati_json, vv.pdf_bytes, vv.created_at, vv.created_by, vv.note_modifica
        FROM visite_visive v
        JOIN visite_visive_versioni vv
          ON vv.visita_id = v.id AND vv.version_no = v.current_version
        WHERE v.id = %s AND COALESCE(v.is_deleted, FALSE) = FALSE;
        """,
        (visita_id,),
    )
    return cur.fetchone()


def list_versioni_pg(conn, visita_id: int):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT version_no, created_at, created_by, note_modifica
        FROM visite_visive_versioni
        WHERE visita_id = %s
        ORDER BY version_no DESC;
        """,
        (visita_id,),
    )
    return cur.fetchall()


def load_version_pg(conn, visita_id: int, version_no: int):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT v.id, v.paziente_id, v.data_visita,
               vv.version_no, vv.dati_json, vv.pdf_bytes, vv.created_at, vv.created_by, vv.note_modifica
        FROM visite_visive v
        JOIN visite_visive_versioni vv
          ON vv.visita_id = v.id
        WHERE v.id = %s AND vv.version_no = %s AND COALESCE(v.is_deleted, FALSE) = FALSE;
        """,
        (visita_id, version_no),
    )
    return cur.fetchone()


def delete_visita(conn, visita_id: int):
    """Delete visit.

    In PostgreSQL, your DB triggers will convert this to soft-delete.
    In SQLite, this will be a physical delete (acceptable for local test).
    """
    cur = conn.cursor()
    if _is_pg(conn):
        cur.execute("DELETE FROM visite_visive WHERE id = %s", (visita_id,))
    else:
        cur.execute("DELETE FROM visite_visive WHERE id = ?", (visita_id,))
    conn.commit()
