# modules/stimolazione_uditiva/db_jobs.py
from __future__ import annotations

import json
from typing import Any, Dict

def ensure_jobs_schema(conn) -> None:
    """
    Crea tabelle:
      - tomatis_presets (preset gating)
      - render_jobs (coda job)
    Pensato per PostgreSQL (Neon).
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tomatis_presets (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL DEFAULT 'tomatis_pnev_v1',
                params_json JSONB NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS render_jobs (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                paziente_id BIGINT NOT NULL,
                eq_profile_id BIGINT,
                preset_id BIGINT,
                input_kind TEXT NOT NULL,                 -- 'upload' | 'dropbox_path'
                input_ref TEXT NOT NULL,                  -- filename o dropbox path
                status TEXT NOT NULL DEFAULT 'queued',     -- queued|running|done|error
                progress NUMERIC(5,2) DEFAULT 0,
                output_ref TEXT,
                error_message TEXT,
                params_json JSONB NOT NULL DEFAULT '{}'::jsonb
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_render_jobs_paz ON render_jobs(paziente_id, created_at DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_render_jobs_status ON render_jobs(status, created_at DESC);")
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


def seed_tomatis_presets(conn) -> None:
    """Inserisce SOFT/STANDARD/FORTE+ se mancanti."""
    presets = [
        ("SOFT", {
            "version": "tomatis_pnev_v1",
            "lambda_events_per_sec": 3.0,
            "bands": {"low":{"min_hz":400,"max_hz":700,"weight":0.20},
                      "mid":{"min_hz":1000,"max_hz":3000,"weight":0.50},
                      "high":{"min_hz":4000,"max_hz":6500,"weight":0.30}},
            "open_state": {"duration_ms":{"min":10,"max":400},"attack_ms":{"min":5,"max":20},"q":{"min":0.8,"max":1.2}},
            "closed_state":{"refractory_ms":{"min":20,"max":80},"attack_ms":{"min":5,"max":20},"q":{"value":2.8},"center_hz":{"value":1000}},
            "mix":{"wet_mix":0.80,"closed_wet_attenuation_db":-6.0},
            "lateral_bias":{"mode":"fixed","dominant_side":"DX","ratio":0.60,"alternate_minutes":2.5},
            "safety":{"limiter_peak_dbfs":-1.0}
        }),
        ("STANDARD", {
            "version": "tomatis_pnev_v1",
            "lambda_events_per_sec": 5.0,
            "bands": {"low":{"min_hz":400,"max_hz":700,"weight":0.20},
                      "mid":{"min_hz":1000,"max_hz":3000,"weight":0.50},
                      "high":{"min_hz":4000,"max_hz":6500,"weight":0.30}},
            "open_state": {"duration_ms":{"min":10,"max":400},"attack_ms":{"min":5,"max":20},"q":{"min":0.8,"max":1.2}},
            "closed_state":{"refractory_ms":{"min":20,"max":80},"attack_ms":{"min":5,"max":20},"q":{"value":2.8},"center_hz":{"value":1000}},
            "mix":{"wet_mix":0.90,"closed_wet_attenuation_db":-10.0},
            "lateral_bias":{"mode":"fixed","dominant_side":"DX","ratio":0.70,"alternate_minutes":2.5},
            "safety":{"limiter_peak_dbfs":-1.0}
        }),
        ("FORTE+", {
            "version": "tomatis_pnev_v1",
            "lambda_events_per_sec": 7.0,
            "bands": {"low":{"min_hz":400,"max_hz":700,"weight":0.20},
                      "mid":{"min_hz":1000,"max_hz":3000,"weight":0.50},
                      "high":{"min_hz":4000,"max_hz":6500,"weight":0.30}},
            "open_state": {"duration_ms":{"min":10,"max":400},"attack_ms":{"min":5,"max":20},"q":{"min":0.8,"max":1.2}},
            "closed_state":{"refractory_ms":{"min":20,"max":80},"attack_ms":{"min":5,"max":20},"q":{"value":2.8},"center_hz":{"value":1000}},
            "mix":{"wet_mix":0.95,"closed_wet_attenuation_db":-14.0},
            "lateral_bias":{"mode":"fixed","dominant_side":"DX","ratio":0.70,"alternate_minutes":2.5},
            "safety":{"limiter_peak_dbfs":-1.0}
        }),
    ]
    cur = conn.cursor()
    try:
        for name, params in presets:
            cur.execute(
                """
                INSERT INTO tomatis_presets(name, params_json)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (name) DO NOTHING
                """,
                (name, json.dumps(params)),
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


def list_tomatis_presets(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, created_at::text FROM tomatis_presets ORDER BY id ASC;")
        return cur.fetchall() or []
    finally:
        try:
            cur.close()
        except Exception:
            pass


def create_render_job(
    conn,
    paziente_id: int,
    eq_profile_id: int,
    preset_id: int,
    input_kind: str,
    input_ref: str,
    params: Dict[str, Any],
) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO render_jobs(paziente_id, eq_profile_id, preset_id, input_kind, input_ref, params_json)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)
            RETURNING id
            """,
            (int(paziente_id), int(eq_profile_id), int(preset_id), str(input_kind), str(input_ref), json.dumps(params)),
        )
        jid = int(cur.fetchone()[0])
        conn.commit()
        return jid
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


def list_render_jobs(conn, paziente_id: int, limit: int = 50):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, created_at::text, status, progress, input_kind, input_ref, output_ref, error_message
            FROM render_jobs
            WHERE paziente_id=%s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (int(paziente_id), int(limit)),
        )
        return cur.fetchall() or []
    finally:
        try:
            cur.close()
        except Exception:
            pass
