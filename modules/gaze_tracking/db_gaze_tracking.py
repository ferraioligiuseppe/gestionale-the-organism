from __future__ import annotations

import json
from typing import Any

import pandas as pd


def init_gaze_tracking_db(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_sessions (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                paziente_label TEXT,
                protocol_name TEXT NOT NULL,
                source_vendor TEXT,
                source_format TEXT,
                source_filename TEXT,
                operator_name TEXT,
                session_notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_samples (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                sample_index BIGINT NOT NULL,
                ts_ms DOUBLE PRECISION,
                gaze_x DOUBLE PRECISION,
                gaze_y DOUBLE PRECISION,
                confidence DOUBLE PRECISION,
                fixation_flag BOOLEAN,
                saccade_flag BOOLEAN,
                blink_flag BOOLEAN,
                eye_left_x DOUBLE PRECISION,
                eye_left_y DOUBLE PRECISION,
                eye_right_x DOUBLE PRECISION,
                eye_right_y DOUBLE PRECISION,
                pupil_size DOUBLE PRECISION,
                distance_cm_est DOUBLE PRECISION,
                target_x DOUBLE PRECISION,
                target_y DOUBLE PRECISION,
                target_label TEXT,
                source_vendor TEXT,
                source_format TEXT,
                source_filename TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_reports (
                id BIGSERIAL PRIMARY KEY,
                session_id BIGINT NOT NULL UNIQUE REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                report_version TEXT,
                analytics_version TEXT,
                metrics_json JSONB,
                clinical_indexes_json JSONB,
                distance_metrics_json JSONB,
                summary_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gaze_browser_sessions (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                paziente_label TEXT,
                session_type TEXT NOT NULL DEFAULT 'browser_facemesh',
                metrics_json JSONB,
                timeline_json JSONB,
                payload_json JSONB,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_sessions_paziente_id ON gaze_sessions(paziente_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_samples_session_id ON gaze_samples(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_reports_session_id ON gaze_reports(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_browser_sessions_paziente_id ON gaze_browser_sessions(paziente_id);")
    conn.commit()


def save_browser_gaze_session(conn, paziente_id: int, paziente_label: str, payload: dict[str, Any], notes: str = "") -> int:
    metrics = payload.get("metrics") or {}
    timeline = payload.get("timeline") or []
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO gaze_browser_sessions (
                paziente_id, paziente_label, metrics_json, timeline_json, payload_json, notes
            ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
            RETURNING id;
            """,
            (
                int(paziente_id),
                paziente_label,
                json.dumps(metrics, ensure_ascii=False),
                json.dumps(timeline, ensure_ascii=False),
                json.dumps(payload, ensure_ascii=False),
                notes,
            ),
        )
        sid = cur.fetchone()[0]
    conn.commit()
    return int(sid)


def list_browser_gaze_sessions(conn, paziente_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, paziente_id, paziente_label, metrics_json, timeline_json, payload_json, notes, created_at
            FROM gaze_browser_sessions
            WHERE paziente_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s;
            """,
            (int(paziente_id), int(limit)),
        )
        rows = cur.fetchall() or []

    out = []
    for r in rows:
        if isinstance(r, dict):
            row = dict(r)
        else:
            row = {
                "id": r[0], "paziente_id": r[1], "paziente_label": r[2],
                "metrics_json": r[3], "timeline_json": r[4], "payload_json": r[5],
                "notes": r[6], "created_at": r[7],
            }
        out.append(row)
    return out


def insert_gaze_session(conn, session_data: dict[str, Any]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO gaze_sessions (
                paziente_id,
                paziente_label,
                protocol_name,
                source_vendor,
                source_format,
                source_filename,
                operator_name,
                session_notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                session_data.get("paziente_id"),
                session_data.get("paziente_label"),
                session_data.get("protocol_name"),
                session_data.get("source_vendor"),
                session_data.get("source_format"),
                session_data.get("source_filename"),
                session_data.get("operator_name"),
                session_data.get("session_notes"),
            ),
        )
        session_id = cur.fetchone()[0]
    conn.commit()
    return int(session_id)


def insert_gaze_samples_bulk(conn, session_id: int, df: pd.DataFrame) -> int:
    rows = []
    for idx, row in df.reset_index(drop=True).iterrows():
        rows.append(
            (
                session_id,
                idx,
                _safe_num(row.get("ts_ms")),
                _safe_num(row.get("gaze_x")),
                _safe_num(row.get("gaze_y")),
                _safe_num(row.get("confidence")),
                bool(row.get("fixation_flag", False)) if row.get("fixation_flag") is not None else False,
                bool(row.get("saccade_flag", False)) if row.get("saccade_flag") is not None else False,
                bool(row.get("blink_flag", False)) if row.get("blink_flag") is not None else False,
                _safe_num(row.get("eye_left_x")),
                _safe_num(row.get("eye_left_y")),
                _safe_num(row.get("eye_right_x")),
                _safe_num(row.get("eye_right_y")),
                _safe_num(row.get("pupil_size")),
                _safe_num(row.get("distance_cm_est")),
                _safe_num(row.get("target_x")),
                _safe_num(row.get("target_y")),
                _safe_text(row.get("target_label")),
                _safe_text(row.get("source_vendor")),
                _safe_text(row.get("source_format")),
                _safe_text(row.get("source_filename")),
            )
        )

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO gaze_samples (
                session_id,
                sample_index,
                ts_ms,
                gaze_x,
                gaze_y,
                confidence,
                fixation_flag,
                saccade_flag,
                blink_flag,
                eye_left_x,
                eye_left_y,
                eye_right_x,
                eye_right_y,
                pupil_size,
                distance_cm_est,
                target_x,
                target_y,
                target_label,
                source_vendor,
                source_format,
                source_filename
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def upsert_gaze_report(conn, session_id: int, report_data: dict[str, Any]) -> None:
    summary_json = report_data.get("summary_json", {})
    metrics_json = report_data.get("metrics", {})
    clinical_indexes_json = report_data.get("clinical_indexes", {})
    distance_metrics_json = report_data.get("distance_metrics", {})

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO gaze_reports (
                session_id,
                report_version,
                analytics_version,
                metrics_json,
                clinical_indexes_json,
                distance_metrics_json,
                summary_json
            )
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
            ON CONFLICT (session_id)
            DO UPDATE SET
                report_version = EXCLUDED.report_version,
                analytics_version = EXCLUDED.analytics_version,
                metrics_json = EXCLUDED.metrics_json,
                clinical_indexes_json = EXCLUDED.clinical_indexes_json,
                distance_metrics_json = EXCLUDED.distance_metrics_json,
                summary_json = EXCLUDED.summary_json,
                updated_at = NOW();
            """,
            (
                session_id,
                summary_json.get("report_version"),
                summary_json.get("analytics_version"),
                json.dumps(metrics_json, ensure_ascii=False),
                json.dumps(clinical_indexes_json, ensure_ascii=False),
                json.dumps(distance_metrics_json, ensure_ascii=False),
                json.dumps(summary_json, ensure_ascii=False),
            ),
        )
    conn.commit()


def _safe_num(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _safe_text(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return str(value)
