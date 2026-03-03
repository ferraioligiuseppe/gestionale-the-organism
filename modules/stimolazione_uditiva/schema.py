# modules/stimolazione_uditiva/schema.py
from __future__ import annotations

def _is_postgres(conn) -> bool:
    mod = getattr(conn.__class__, "__module__", "") or ""
    return "psycopg2" in mod or "pg8000" in mod or "psycopg" in mod

def ensure_audio_schema(conn) -> None:
    """
    Crea tabelle minime per:
      - esami ORL (soglie tonali)
      - soglie per frequenza e orecchio
      - profili EQ baseline salvati
    Compatibile con PostgreSQL (Neon) e fallback SQLite.
    """
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orl_esami (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    paziente_id BIGINT NOT NULL,
                    data_esame DATE,
                    fonte TEXT,
                    note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orl_soglie (
                    id BIGSERIAL PRIMARY KEY,
                    esame_id BIGINT NOT NULL REFERENCES orl_esami(id) ON DELETE CASCADE,
                    ear TEXT NOT NULL CHECK (ear IN ('DX','SX')),
                    freq_hz INT NOT NULL,
                    db_hl DOUBLE PRECISION,
                    UNIQUE(esame_id, ear, freq_hz)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eq_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    paziente_id BIGINT NOT NULL,
                    esame_id BIGINT REFERENCES orl_esami(id) ON DELETE SET NULL,
                    nome TEXT NOT NULL,
                    params_json JSONB NOT NULL,
                    gain_dx_json JSONB NOT NULL,
                    gain_sx_json JSONB NOT NULL
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_orl_esami_paziente ON orl_esami(paziente_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_eq_profiles_paziente ON eq_profiles(paziente_id);")
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orl_esami (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    paziente_id INTEGER NOT NULL,
                    data_esame TEXT,
                    fonte TEXT,
                    note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orl_soglie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    esame_id INTEGER NOT NULL,
                    ear TEXT NOT NULL,
                    freq_hz INTEGER NOT NULL,
                    db_hl REAL,
                    UNIQUE(esame_id, ear, freq_hz)
                );
            """)
            cur.execute("""
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
    finally:
        try: cur.close()
        except Exception: pass
