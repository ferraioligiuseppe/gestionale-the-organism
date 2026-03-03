# modules/stimolazione_uditiva/schema.py
from __future__ import annotations

def _is_postgres(conn) -> bool:
    mod = getattr(conn.__class__, "__module__", "") or ""
    return "psycopg2" in mod or "pg8000" in mod or "psycopg" in mod

def _exec(cur, sql: str):
    # esegui statement singolo e ritorna
    cur.execute(sql)

def ensure_audio_schema(conn) -> None:
    """
    Versione ultra-compatibile (Postgres Neon):
    - sintassi identica a quella già presente nel tuo app.py (BIGSERIAL, NOW(), JSONB)
    - statement separati + semicoloni
    - se fallisce, fa rollback e rilancia errore con SQL abbreviato (così capiamo dov'è)
    """
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS public.orl_esami (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    paziente_id BIGINT NOT NULL,
                    data_esame DATE,
                    fonte TEXT,
                    note TEXT
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS public.orl_soglie (
                    id BIGSERIAL PRIMARY KEY,
                    esame_id BIGINT NOT NULL REFERENCES public.orl_esami(id) ON DELETE CASCADE,
                    ear TEXT NOT NULL,
                    freq_hz INT NOT NULL,
                    db_hl REAL,
                    UNIQUE(esame_id, ear, freq_hz)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS public.eq_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    paziente_id BIGINT NOT NULL,
                    esame_id BIGINT REFERENCES public.orl_esami(id) ON DELETE SET NULL,
                    nome TEXT NOT NULL,
                    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    gain_dx_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    gain_sx_json JSONB NOT NULL DEFAULT '{}'::jsonb
                );
                """,
            ]
            for s in stmts:
                _exec(cur, s)
            try:
                _exec(cur, "CREATE INDEX IF NOT EXISTS idx_orl_esami_paziente ON public.orl_esami(paziente_id);")
                _exec(cur, "CREATE INDEX IF NOT EXISTS idx_eq_profiles_paziente ON public.eq_profiles(paziente_id);")
            except Exception:
                pass
        else:
            # SQLite fallback
            _exec(cur, """
                CREATE TABLE IF NOT EXISTS orl_esami (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    paziente_id INTEGER NOT NULL,
                    data_esame TEXT,
                    fonte TEXT,
                    note TEXT
                );
            """)
            _exec(cur, """
                CREATE TABLE IF NOT EXISTS orl_soglie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    esame_id INTEGER NOT NULL,
                    ear TEXT NOT NULL,
                    freq_hz INTEGER NOT NULL,
                    db_hl REAL,
                    UNIQUE(esame_id, ear, freq_hz)
                );
            """)
            _exec(cur, """
                CREATE TABLE IF NOT EXISTS eq_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    paziente_id INTEGER NOT NULL,
                    esame_id INTEGER,
                    nome TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    gain_dx_json TEXT NOT NULL,
                    gain_sx_json TEXT NOT NULL
                );
            """)

        conn.commit()

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        # rilancia con un messaggio "leggibile" (non contiene segreti)
        raise RuntimeError(f"ensure_audio_schema failed: {type(e).__name__}: {e}") from e

    finally:
        try:
            cur.close()
        except Exception:
            pass
