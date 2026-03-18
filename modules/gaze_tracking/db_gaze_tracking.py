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
                protocol_name TEXT NOT NULL DEFAULT 'browser_live',
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

        # compat / browser-live columns
        cur.execute("ALTER TABLE gaze_sessions ADD COLUMN IF NOT EXISTS session_mode TEXT DEFAULT 'browser_live';")
        cur.execute("ALTER TABLE gaze_sessions ADD COLUMN IF NOT EXISTS browser_payload_json JSONB;")
        cur.execute("ALTER TABLE gaze_sessions ADD COLUMN IF NOT EXISTS snapshot_data_url TEXT;")
        cur.execute("ALTER TABLE gaze_sessions ADD COLUMN IF NOT EXISTS session_duration_sec DOUBLE PRECISION;")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_sessions_paziente_id ON gaze_sessions(paziente_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_samples_session_id ON gaze_samples(session_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_gaze_reports_session_id ON gaze_reports(session_id);")
    conn.commit()


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
                session_notes,
                session_mode,
                browser_payload_json,
                snapshot_data_url,
                session_duration_sec
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING id;
            """,
            (
                session_data.get("paziente_id"),
                session_data.get("paziente_label"),
                session_data.get("protocol_name", "browser_live"),
                session_data.get("source_vendor"),
                session_data.get("source_format"),
                session_data.get("source_filename"),
                session_data.get("operator_name"),
                session_data.get("session_notes"),
                session_data.get("session_mode", "browser_live"),
                json.dumps(session_data.get("browser_payload_json") or {}, ensure_ascii=False),
                session_data.get("snapshot_data_url"),
                session_data.get("session_duration_sec"),
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


def save_browser_gaze_session(
    conn,
    *,
    paziente_id: int,
    paziente_label: str,
    payload: dict[str, Any],
    operator_name: str | None = None,
    session_notes: str | None = None,
    snapshot_data_url: str | None = None,
) -> int:
    init_gaze_tracking_db(conn)

    metrics = payload.get("metrics") or {}
    indexes = payload.get("pnev_indexes") or {}
    meta = payload.get("meta") or {}

    started_at = payload.get("session_started_at")
    ended_at = payload.get("timestamp")
    duration_sec = _estimate_duration_seconds(started_at, ended_at)

    session_id = insert_gaze_session(
        conn,
        {
            "paziente_id": int(paziente_id),
            "paziente_label": paziente_label,
            "protocol_name": "browser_live_v1",
            "source_vendor": "mediapipe_js",
            "source_format": "browser_json",
            "source_filename": "live_session.json",
            "operator_name": operator_name,
            "session_notes": session_notes,
            "session_mode": "browser_live",
            "browser_payload_json": payload,
            "snapshot_data_url": snapshot_data_url,
            "session_duration_sec": duration_sec,
        },
    )

    summary_json = {
        "report_version": "browser_live_v1",
        "analytics_version": "browser_live_v1",
        "source": "webcam_browser_v3",
        "patient_id": paziente_id,
        "patient_label": paziente_label,
        "session_started_at": started_at,
        "session_saved_at": ended_at,
        "session_duration_sec": duration_sec,
        "face_detected": bool(meta.get("face_detected")),
        "frame_count": meta.get("frame_count"),
        "image_width": meta.get("image_width"),
        "image_height": meta.get("image_height"),
    }

    upsert_gaze_report(
        conn,
        session_id,
        {
            "summary_json": summary_json,
            "metrics": metrics,
            "clinical_indexes": indexes,
            "distance_metrics": {},
        },
    )
    return int(session_id)


def list_gaze_sessions_summary(conn, paziente_id: int, limit: int = 20) -> list[dict[str, Any]]:
    init_gaze_tracking_db(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                s.id,
                s.created_at,
                s.protocol_name,
                s.operator_name,
                s.session_notes,
                s.session_duration_sec,
                r.metrics_json,
                r.clinical_indexes_json,
                r.summary_json
            FROM gaze_sessions s
            LEFT JOIN gaze_reports r ON r.session_id = s.id
            WHERE s.paziente_id = %s
            ORDER BY s.created_at DESC
            LIMIT %s;
            """,
            (int(paziente_id), int(limit)),
        )
        rows = cur.fetchall() or []

    out = []
    for row in rows:
        session_id, created_at, protocol_name, operator_name, session_notes, duration_sec, metrics_json, indexes_json, summary_json = row
        out.append(
            {
                "id": session_id,
                "created_at": str(created_at),
                "protocol_name": protocol_name,
                "operator_name": operator_name,
                "session_notes": session_notes,
                "session_duration_sec": duration_sec,
                "metrics_json": _json_to_dict(metrics_json),
                "clinical_indexes_json": _json_to_dict(indexes_json),
                "summary_json": _json_to_dict(summary_json),
            }
        )
    return out


def _json_to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


def _estimate_duration_seconds(started_at: Any, ended_at: Any) -> float | None:
    from datetime import datetime

    if not started_at or not ended_at:
        return None

    def _parse(v: Any) -> datetime | None:
        if not v:
            return None
        try:
            s = str(v).replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except Exception:
            return None

    sdt = _parse(started_at)
    edt = _parse(ended_at)
    if not sdt or not edt:
        return None
    try:
        sec = (edt - sdt).total_seconds()
        if sec < 0:
            return None
        return float(round(sec, 3))
    except Exception:
        return None


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
