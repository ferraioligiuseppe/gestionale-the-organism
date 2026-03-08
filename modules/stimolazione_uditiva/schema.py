# modules/stimolazione_uditiva/schema.py
from __future__ import annotations

def _is_postgres(conn) -> bool:
    """
    Rilevazione robusta:
    - se è sqlite3 -> False
    - altrimenti (Neon/psycopg2/wrapper custom) -> True
    """
    mod = (getattr(conn.__class__, "__module__", "") or "").lower()
    name = (getattr(conn.__class__, "__name__", "") or "").lower()

    # casi SQLite
    if "sqlite3" in mod or "sqlite" in mod or "sqlite" in name:
        return False

    # casi Postgres (anche con wrapper)
    # molti wrapper non espongono "psycopg2" nel __module__,
    # quindi qui assumiamo Postgres se non è chiaramente sqlite.
    return True

def ensure_audio_schema(conn):
    """
    NON lancia eccezioni: ritorna (ok: bool, message: str)
    Se fallisce, message contiene errore + SQL dell’ultimo statement.
    """
    cur = conn.cursor()
    last_sql = ""
    try:
        if _is_postgres(conn):
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS orl_esami (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    paziente_id BIGINT NOT NULL,
                    data_esame DATE,
                    fonte TEXT,
                    note TEXT
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS orl_soglie (
                    id BIGSERIAL PRIMARY KEY,
                    esame_id BIGINT NOT NULL REFERENCES orl_esami(id) ON DELETE CASCADE,
                    ear TEXT NOT NULL,
                    freq_hz INT NOT NULL,
                    db_hl REAL,
                    UNIQUE(esame_id, ear, freq_hz)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS eq_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    paziente_id BIGINT NOT NULL,
                    esame_id BIGINT REFERENCES orl_esami(id) ON DELETE SET NULL,
                    nome TEXT NOT NULL,
                    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    gain_dx_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    gain_sx_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );
                """,
            ]
            for s in stmts:
                last_sql = s
                cur.execute(s)

            # indici (se falliscono non bloccare)
            try:
                last_sql = "CREATE INDEX IF NOT EXISTS idx_orl_esami_paziente ON orl_esami(paziente_id);"
                cur.execute(last_sql)
            except Exception:
                pass
            try:
                last_sql = "CREATE INDEX IF NOT EXISTS idx_eq_profiles_paziente ON eq_profiles(paziente_id);"
                cur.execute(last_sql)
            except Exception:
                pass

        else:
            # SQLite fallback
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS orl_esami (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    paziente_id INTEGER NOT NULL,
                    data_esame TEXT,
                    fonte TEXT,
                    note TEXT
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS orl_soglie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    esame_id INTEGER NOT NULL,
                    ear TEXT NOT NULL,
                    freq_hz INTEGER NOT NULL,
                    db_hl REAL,
                    UNIQUE(esame_id, ear, freq_hz)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS eq_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    paziente_id INTEGER NOT NULL,
                    esame_id INTEGER,
                    nome TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    gain_dx_json TEXT NOT NULL,
                    gain_sx_json TEXT NOT NULL
                );
                """,
            ]
            for s in stmts:
                last_sql = s
                cur.execute(s)

        conn.commit()
        return True, "OK"

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        msg = f"{type(e).__name__}: {e}\n\n--- SQL (last) ---\n{last_sql.strip()}\n"
        return False, msg

    finally:
        try:
            cur.close()
        except Exception:
            pass
