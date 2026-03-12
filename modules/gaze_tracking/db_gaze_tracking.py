from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json


def _row_to_dict(cols: List[str], row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {cols[i]: row[i] for i in range(len(cols))}


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_sessions (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL REFERENCES Pazienti(id) ON DELETE CASCADE,
                operatore TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                protocollo TEXT NOT NULL,
                camera_type TEXT,
                screen_width INT,
                screen_height INT,
                distance_cm NUMERIC(6,2),
                calibration_points INT DEFAULT 9,
                calibration_score NUMERIC(6,3),
                status TEXT DEFAULT 'draft',
                note TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_samples (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                ts_ms BIGINT NOT NULL,
                gaze_x NUMERIC(8,3),
                gaze_y NUMERIC(8,3),
                confidence NUMERIC(6,3),
                target_label TEXT,
                tracking_ok BOOLEAN DEFAULT TRUE
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_reports (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL UNIQUE REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                fixation_total_ms BIGINT,
                mean_fixation_ms NUMERIC(10,2),
                saccade_count INT,
                target_hit_rate NUMERIC(6,3),
                tracking_loss_pct NUMERIC(6,3),
                center_bias_pct NUMERIC(6,3),
                sample_count INT,
                summary_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_samples_session_ts ON gaze_samples(session_id, ts_ms);")
    finally:
        try:
            cur.close()
        except Exception:
            pass
    conn.commit()


def create_gaze_session(conn, payload: dict) -> int:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO gaze_sessions (
                paziente_id, operatore, protocollo, camera_type, screen_width,
                screen_height, distance_cm, calibration_points, calibration_score, status, note
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                payload.get("calibration_points", 9),
                payload.get("calibration_score"),
                payload.get("status", "draft"),
                payload.get("note"),
            ),
        )
        session_id = int(cur.fetchone()[0])
    finally:
        try:
            cur.close()
        except Exception:
            pass
    conn.commit()
    return session_id


def insert_gaze_samples(conn, session_id: int, samples: list[dict]) -> int:
    if not samples:
        return 0
    cur = conn.cursor()
    inserted = 0
    try:
        for s in samples:
            cur.execute(
                """
                INSERT INTO gaze_samples (
                    session_id, ts_ms, gaze_x, gaze_y, confidence, target_label, tracking_ok
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    session_id,
                    int(s["ts_ms"]),
                    s.get("gaze_x"),
                    s.get("gaze_y"),
                    s.get("confidence"),
                    s.get("target_label"),
                    bool(s.get("tracking_ok", True)),
                ),
            )
            inserted += 1
    finally:
        try:
            cur.close()
        except Exception:
            pass
    conn.commit()
    return inserted


def save_gaze_report(conn, session_id: int, report: dict) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO gaze_reports (
                session_id, fixation_total_ms, mean_fixation_ms, saccade_count,
                target_hit_rate, tracking_loss_pct, center_bias_pct, sample_count, summary_json
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_id) DO UPDATE SET
                fixation_total_ms = EXCLUDED.fixation_total_ms,
                mean_fixation_ms = EXCLUDED.mean_fixation_ms,
                saccade_count = EXCLUDED.saccade_count,
                target_hit_rate = EXCLUDED.target_hit_rate,
                tracking_loss_pct = EXCLUDED.tracking_loss_pct,
                center_bias_pct = EXCLUDED.center_bias_pct,
                sample_count = EXCLUDED.sample_count,
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
                report.get("sample_count"),
                json.dumps(report, ensure_ascii=False),
            ),
        )
    finally:
        try:
            cur.close()
        except Exception:
            pass
    conn.commit()


def list_sessions(conn, paziente_id: int) -> list[dict]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.id, s.created_at, s.protocollo, s.camera_type, s.calibration_score,
                   r.sample_count, r.target_hit_rate, r.tracking_loss_pct
            FROM gaze_sessions s
            LEFT JOIN gaze_reports r ON r.session_id = s.id
            WHERE s.paziente_id = %s
            ORDER BY s.created_at DESC, s.id DESC
            """,
            (paziente_id,),
        )
        rows = cur.fetchall() or []
        cols = [d[0] for d in cur.description]
    finally:
        try:
            cur.close()
        except Exception:
            pass
    return [_row_to_dict(cols, r) for r in rows]
