from __future__ import annotations
import json

DB_GAZE_VERSION = "FIX_NO_CONTEXT_MANAGER_V2"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gaze_sessions (
    id BIGSERIAL PRIMARY KEY,
    paziente_id BIGINT NOT NULL,
    operatore TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    protocollo TEXT NOT NULL,
    camera_type TEXT,
    screen_width INT,
    screen_height INT,
    distance_cm NUMERIC(6,2),
    distance_mode TEXT DEFAULT 'free',
    distance_target_min_cm NUMERIC(6,2),
    distance_target_max_cm NUMERIC(6,2),
    calibration_points INT DEFAULT 9,
    calibration_score NUMERIC(6,3),
    status TEXT DEFAULT 'draft',
    note TEXT
);

CREATE TABLE IF NOT EXISTS gaze_samples (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES gaze_sessions(id) ON DELETE CASCADE,
    ts_ms BIGINT NOT NULL,
    gaze_x NUMERIC(8,3),
    gaze_y NUMERIC(8,3),
    confidence NUMERIC(6,3),
    tracking_ok BOOLEAN DEFAULT TRUE,
    distance_cm_est NUMERIC(8,3),
    distance_zone TEXT,
    target_x NUMERIC(8,3),
    target_y NUMERIC(8,3),
    target_label TEXT
);

CREATE TABLE IF NOT EXISTS gaze_reports (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL UNIQUE REFERENCES gaze_sessions(id) ON DELETE CASCADE,
    fixation_total_ms BIGINT,
    mean_fixation_ms NUMERIC(10,2),
    saccade_count INT,
    target_hit_rate NUMERIC(6,3),
    tracking_loss_pct NUMERIC(6,3),
    center_bias_pct NUMERIC(6,3),
    calibration_score NUMERIC(6,3),
    distance_mean_cm NUMERIC(8,3),
    distance_min_cm NUMERIC(8,3),
    distance_max_cm NUMERIC(8,3),
    distance_std_cm NUMERIC(8,3),
    time_near_pct NUMERIC(6,3),
    time_mid_pct NUMERIC(6,3),
    time_far_pct NUMERIC(6,3),
    summary_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gaze_samples_session_ts
    ON gaze_samples(session_id, ts_ms);
"""


def _close_cursor_safely(cur) -> None:
    try:
        if cur is not None:
            close_fn = getattr(cur, "close", None)
            if callable(close_fn):
                close_fn()
    except Exception:
        pass


def ensure_schema(conn) -> None:
    if conn is None:
        raise RuntimeError("Connessione DB assente")
    if not hasattr(conn, "cursor"):
        raise TypeError(f"Connessione DB non valida: {type(conn)}")

    cur = conn.cursor()
    try:
        cur.execute(SCHEMA_SQL)
        conn.commit()
    finally:
        _close_cursor_safely(cur)


def create_gaze_session(conn, payload: dict) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO gaze_sessions (
                paziente_id,
                operatore,
                protocollo,
                camera_type,
                screen_width,
                screen_height,
                distance_cm,
                distance_mode,
                distance_target_min_cm,
                distance_target_max_cm,
                calibration_points,
                calibration_score,
                status,
                note
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                payload["paziente_id"],
                payload.get("operatore"),
                payload["protocollo"],
                payload.get("camera_type"),
                payload.get("screen_width"),
                payload.get("screen_height"),
                payload.get("distance_cm"),
                payload.get("distance_mode", "free"),
                payload.get("distance_target_min_cm"),
                payload.get("distance_target_max_cm"),
                payload.get("calibration_points", 9),
                payload.get("calibration_score"),
                payload.get("status", "draft"),
                payload.get("note"),
            ),
        )
        row = cur.fetchone()
        conn.commit()

        if not row:
            raise RuntimeError("Creazione sessione fallita: nessun ID restituito")

        return int(row[0])
    finally:
        _close_cursor_safely(cur)


def insert_gaze_samples(conn, session_id: int, samples: list[dict]) -> int:
    cur = conn.cursor()
    inserted = 0
    try:
        for s in samples:
            cur.execute(
                """
                INSERT INTO gaze_samples (
                    session_id,
                    ts_ms,
                    gaze_x,
                    gaze_y,
                    confidence,
                    tracking_ok,
                    distance_cm_est,
                    distance_zone,
                    target_x,
                    target_y,
                    target_label
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    s["ts_ms"],
                    s.get("gaze_x"),
                    s.get("gaze_y"),
                    s.get("confidence"),
                    s.get("tracking_ok", True),
                    s.get("distance_cm_est"),
                    s.get("distance_zone"),
                    s.get("target_x"),
                    s.get("target_y"),
                    s.get("target_label"),
                ),
            )
            inserted += 1

        conn.commit()
        return inserted
    finally:
        _close_cursor_safely(cur)


def save_gaze_report(conn, session_id: int, report: dict) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO gaze_reports (
                session_id,
                fixation_total_ms,
                mean_fixation_ms,
                saccade_count,
                target_hit_rate,
                tracking_loss_pct,
                center_bias_pct,
                calibration_score,
                distance_mean_cm,
                distance_min_cm,
                distance_max_cm,
                distance_std_cm,
                time_near_pct,
                time_mid_pct,
                time_far_pct,
                summary_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                fixation_total_ms = EXCLUDED.fixation_total_ms,
                mean_fixation_ms = EXCLUDED.mean_fixation_ms,
                saccade_count = EXCLUDED.saccade_count,
                target_hit_rate = EXCLUDED.target_hit_rate,
                tracking_loss_pct = EXCLUDED.tracking_loss_pct,
                center_bias_pct = EXCLUDED.center_bias_pct,
                calibration_score = EXCLUDED.calibration_score,
                distance_mean_cm = EXCLUDED.distance_mean_cm,
                distance_min_cm = EXCLUDED.distance_min_cm,
                distance_max_cm = EXCLUDED.distance_max_cm,
                distance_std_cm = EXCLUDED.distance_std_cm,
                time_near_pct = EXCLUDED.time_near_pct,
                time_mid_pct = EXCLUDED.time_mid_pct,
                time_far_pct = EXCLUDED.time_far_pct,
                summary_json = EXCLUDED.summary_json
            """,
            (
                session_id,
                report.get("fixation_total_ms"),
                report.get("mean_fixation_ms"),
                report.get("saccade_count"),
                report.get("target_hit_rate"),
                report.get("tracking_loss_pct"),
                report.get("center_bias_pct"),
                report.get("calibration_score"),
                report.get("distance_mean_cm"),
                report.get("distance_min_cm"),
                report.get("distance_max_cm"),
                report.get("distance_std_cm"),
                report.get("time_near_pct"),
                report.get("time_mid_pct"),
                report.get("time_far_pct"),
                json.dumps(report, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        _close_cursor_safely(cur)


def list_sessions(conn, paziente_id: int):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                id,
                created_at,
                protocollo,
                distance_mode,
                calibration_score,
                status
            FROM gaze_sessions
            WHERE paziente_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (paziente_id,),
        )
        return cur.fetchall()
    finally:
        _close_cursor_safely(cur)
