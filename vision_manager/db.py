"""
vision_manager/db.py — Connessione DB con auto-reconnect.

Risolve il problema "SSL connection has been closed unexpectedly":
PostgreSQL chiude le connessioni inattive dopo qualche minuto, ma `@st.cache_resource`
le tiene in memoria a lungo. Il vecchio codice riutilizzava una connessione morta.

La soluzione e' un health check (`SELECT 1`) prima di restituire la connessione
cached. Se la verifica fallisce, invalidiamo la cache e creiamo una connessione
nuova in modo trasparente per il chiamante.

Note di compatibilita':
- L'API pubblica resta invariata: `get_conn()`, `init_db(conn)`, `_is_pg(conn)`.
- Il codice chiamante non ha bisogno di modifiche.
- Il tempo aggiunto per il health check e' trascurabile (~1ms su rete locale).
"""

import streamlit as st
import os
import sqlite3


# =============================================================================
#  Helper interni
# =============================================================================

def _env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v not in (None, "") else default


def _is_pg(conn) -> bool:
    """True se la connessione e' verso PostgreSQL (psycopg2), False se SQLite."""
    return conn.__class__.__module__.startswith("psycopg2")


def _create_connection():
    """Crea una nuova connessione (PostgreSQL via DATABASE_URL, oppure SQLite locale)."""
    db_url = _env("DATABASE_URL", "")
    if db_url:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(
            db_url,
            cursor_factory=RealDictCursor,
            connect_timeout=8,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
    return sqlite3.connect("vision_manager.db", check_same_thread=False)


def _is_alive(conn) -> bool:
    """Verifica se la connessione e' ancora utilizzabile.

    Per Postgres: SELECT 1. Se la connessione e' morta o in stato aborted,
    psycopg2 solleva eccezione e ritorniamo False.

    Per SQLite: la connessione e' locale al filesystem, vive sempre.
    """
    if conn is None:
        return False
    try:
        if _is_pg(conn):
            # Se la transazione e' in stato aborted, prima la rilascio.
            # Senza questo, ogni query (anche SELECT 1) fallisce.
            try:
                if hasattr(conn, "status"):
                    # psycopg2.extensions.STATUS_IN_TRANSACTION = 2
                    # psycopg2.extensions.STATUS_BEGIN = 3 (in alcune versioni)
                    pass  # gestiamo via rollback try/except sotto
                conn.rollback()
            except Exception:
                # Se il rollback fallisce, la connessione e' davvero morta
                return False
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return True
        else:
            # SQLite
            conn.execute("SELECT 1").fetchone()
            return True
    except Exception:
        return False


# =============================================================================
#  API pubblica
# =============================================================================

@st.cache_resource
def _get_cached_connection():
    """Connessione cached (creata una sola volta per sessione utente).
    NB: usiamo _get_cached_connection in privato; il pubblico e' get_conn()
    che aggiunge il health check.
    """
    return _create_connection()


def get_conn():
    """Restituisce una connessione DB viva.

    Se la connessione cached e' morta (timeout, SSL closed, eccetera),
    invalida la cache e crea una nuova connessione automaticamente.
    """
    conn = _get_cached_connection()
    if not _is_alive(conn):
        # La connessione cached e' morta: invalido e ricreo
        try:
            conn.close()
        except Exception:
            pass
        # st.cache_resource.clear() svuota la cache di tutte le funzioni cached_resource
        # Per essere chirurgici useremmo _get_cached_connection.clear() ma in alcune
        # versioni di Streamlit non e' disponibile. clear() globale e' sicuro qui
        # perche' get_conn e' l'unica funzione cached in questo modulo.
        try:
            _get_cached_connection.clear()
        except Exception:
            try:
                st.cache_resource.clear()
            except Exception:
                pass
        conn = _get_cached_connection()
    return conn


# =============================================================================
#  init_db (schema check)
# =============================================================================

def _add_col_if_missing(conn, table: str, col: str, ddl: str):
    cur = conn.cursor()
    try:
        if _is_pg(conn):
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


def init_db(conn):
    if conn is None:
        raise RuntimeError("init_db(conn): conn è None. Verifica get_conn() e DATABASE_URL.")
    if not hasattr(conn, "cursor"):
        raise TypeError(f"init_db(conn): oggetto non valido ({type(conn)}), manca .cursor().")

    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS visite_visive (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    paziente_id BIGINT NOT NULL REFERENCES pazienti(id) ON DELETE CASCADE,
                    data_visita TEXT,
                    dati_json JSONB,
                    pdf_bytes BYTEA,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP NULL
                );
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS prescrizioni_occhiali (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    paziente_id BIGINT NOT NULL REFERENCES pazienti(id) ON DELETE CASCADE,
                    data_prescrizione TEXT,
                    formato TEXT,
                    dati_json JSONB,
                    pdf_bytes BYTEA
                );
                """
            )

            _add_col_if_missing(conn, "visite_visive", "is_deleted", "is_deleted INTEGER DEFAULT 0")
            _add_col_if_missing(conn, "visite_visive", "deleted_at", "deleted_at TIMESTAMP NULL")
            conn.commit()
            return

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Pazienti (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Cognome TEXT,
                Nome TEXT,
                Data_Nascita TEXT,
                Note TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS visite_visive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paziente_id INTEGER,
                data_visita TEXT,
                dati_json TEXT,
                pdf_bytes BLOB,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            );
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
            );
            """
        )

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
