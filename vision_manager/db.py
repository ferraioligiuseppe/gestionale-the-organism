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

# =========================
# VISITE VISIVE – VERSIONING (Neon PG)
# =========================

def get_visita_corrente(conn, visita_id: int):
    """Ritorna la versione corrente (join su visite_visive_versioni) se presente, altrimenti fallback su visite_visive."""
    cur = conn.cursor()
    if _is_pg(conn):
        try:
            cur.execute(
                """
                SELECT
                  v.id AS visita_id,
                  v.paziente_id,
                  v.data_visita,
                  v.current_version,
                  vv.dati_json,
                  vv.pdf_bytes,
                  vv.created_at AS version_created_at,
                  vv.created_by,
                  vv.note_modifica
                FROM visite_visive v
                JOIN visite_visive_versioni vv
                  ON vv.visita_id = v.id
                 AND vv.version_no = v.current_version
                WHERE v.id = %s
                  AND COALESCE(v.is_deleted, FALSE) = FALSE;
                """,
                (visita_id,),
            )
            return cur.fetchone()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.execute(
                """SELECT id, paziente_id, data_visita, NULL, dati_json, pdf_bytes, NULL, NULL, NULL
                     FROM visite_visive WHERE id = %s""",
                (visita_id,),
            )
            return cur.fetchone()

    # SQLite / fallback
    cur.execute(
        """SELECT id, paziente_id, data_visita, NULL, dati_json, pdf_bytes, NULL, NULL, NULL
             FROM visite_visive WHERE id = ?""",
        (visita_id,),
    )
    return cur.fetchone()


def get_versioni_visita(conn, visita_id: int):
    """Lista versioni di una visita (version_no DESC)."""
    cur = conn.cursor()
    if _is_pg(conn):
        try:
            cur.execute(
                """
                SELECT version_no, created_at, created_by, note_modifica
                FROM visite_visive_versioni
                WHERE visita_id = %s
                ORDER BY version_no DESC
                """,
                (visita_id,),
            )
            return cur.fetchall()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return []
    return []


def get_visita_versione(conn, visita_id: int, version_no: int):
    """Ritorna una versione specifica."""
    cur = conn.cursor()
    if _is_pg(conn):
        try:
            cur.execute(
                """
                SELECT
                  v.id AS visita_id,
                  v.paziente_id,
                  v.data_visita,
                  vv.version_no,
                  vv.dati_json,
                  vv.pdf_bytes,
                  vv.created_at,
                  vv.created_by,
                  vv.note_modifica
                FROM visite_visive v
                JOIN visite_visive_versioni vv
                  ON vv.visita_id = v.id
                WHERE v.id = %s
                  AND vv.version_no = %s
                  AND COALESCE(v.is_deleted, FALSE) = FALSE;
                """,
                (visita_id, version_no),
            )
            return cur.fetchone()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return None
    return None


def list_visite_visive(conn, paziente_id: int):
    """Lista visite (solo non eliminate se colonna presente)."""
    cur = conn.cursor()
    if _is_pg(conn):
        try:
            cur.execute(
                """
                SELECT id, data_visita, current_version, updated_at
                FROM visite_visive
                WHERE paziente_id = %s AND COALESCE(is_deleted, FALSE) = FALSE
                ORDER BY data_visita DESC NULLS LAST, id DESC
                """,
                (paziente_id,),
            )
            return cur.fetchall()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            cur.execute(
                """SELECT id, data_visita, NULL, NULL
                     FROM visite_visive WHERE paziente_id = %s ORDER BY data_visita DESC NULLS LAST, id DESC""",
                (paziente_id,),
            )
            return cur.fetchall()

    # SQLite
    cur.execute(
        """SELECT id, data_visita, NULL, NULL
             FROM visite_visive WHERE paziente_id = ? ORDER BY data_visita DESC, id DESC""",
        (paziente_id,),
    )
    return cur.fetchall()


def soft_delete_visita(conn, visita_id: int):
    """Elimina visita: su PG diventa soft delete via trigger; su SQLite delete fisica."""
    cur = conn.cursor()
    if _is_pg(conn):
        cur.execute("DELETE FROM visite_visive WHERE id = %s", (visita_id,))
    else:
        cur.execute("DELETE FROM visite_visive WHERE id = ?", (visita_id,))
    conn.commit()
