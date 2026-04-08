import json
from typing import Optional


def ensure_slap_tap_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS slap_tap_sessions (
            id BIGSERIAL PRIMARY KEY,
            patient_id BIGINT NULL,
            visit_id BIGINT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            operator_name TEXT NULL,
            bpm INTEGER NOT NULL DEFAULT 60,
            mode TEXT NOT NULL DEFAULT '1:1',
            sequence_length INTEGER NOT NULL DEFAULT 4,
            sequence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            response_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            response_times_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            symbol_accuracy NUMERIC(6,2) NULL,
            timing_accuracy NUMERIC(6,2) NULL,
            notes TEXT NULL
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS slap_tap_trials (
            id BIGSERIAL PRIMARY KEY,
            session_id BIGINT NOT NULL REFERENCES slap_tap_sessions(id) ON DELETE CASCADE,
            trial_index INTEGER NOT NULL,
            expected_symbol TEXT NOT NULL,
            actual_symbol TEXT NULL,
            is_correct BOOLEAN NOT NULL DEFAULT FALSE,
            error_type TEXT NULL,
            expected_time TIMESTAMPTZ NULL,
            actual_time TIMESTAMPTZ NULL,
            delta_ms INTEGER NULL,
            timing_label TEXT NULL,
            in_tolerance BOOLEAN NULL,
            meta_json JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """)
    conn.commit()


def save_slap_tap_session(
    conn,
    patient_id: Optional[int],
    visit_id: Optional[int],
    operator_name: Optional[str],
    bpm: int,
    mode: str,
    sequence: list[str],
    response: list[str],
    response_times: list[float],
    scoring: dict,
    notes: Optional[str] = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO slap_tap_sessions (
            patient_id, visit_id, operator_name, bpm, mode, sequence_length,
            sequence_json, response_json, response_times_json,
            symbol_accuracy, timing_accuracy, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
        RETURNING id;
        """, (
            patient_id,
            visit_id,
            operator_name,
            bpm,
            mode,
            len(sequence),
            json.dumps(sequence),
            json.dumps(response),
            json.dumps(response_times),
            scoring.get("symbol_accuracy"),
            scoring.get("timing_accuracy"),
            notes,
        ))
        session_id = cur.fetchone()[0]

        rows = scoring.get("rows", [])
        for row in rows:
            cur.execute("""
            INSERT INTO slap_tap_trials (
                session_id, trial_index, expected_symbol, actual_symbol,
                is_correct, error_type, delta_ms, timing_label, in_tolerance, meta_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            """, (
                session_id,
                row["index"],
                row["expected"],
                row.get("actual"),
                row["correct"],
                row.get("error_type") or None,
                row.get("delta_ms"),
                row.get("timing_label") or None,
                row.get("in_tolerance"),
                json.dumps({
                    "expected_label": row.get("expected"),
                    "actual_label": row.get("actual"),
                }),
            ))

    conn.commit()
    return session_id
