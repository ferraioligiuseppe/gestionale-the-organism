from __future__ import annotations

import json


def init_db_gaze_tracking(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gaze_sessions (
                id SERIAL PRIMARY KEY,
                paziente_id INTEGER,
                operatore TEXT,
                protocollo TEXT,
                camera_type TEXT,
                distance_cm NUMERIC,
                distance_mode TEXT,
                distance_target_min_cm NUMERIC,
                distance_target_max_cm NUMERIC,
                calibration_score NUMERIC,
                status TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS gaze_samples (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                ts_ms NUMERIC,
                gaze_x NUMERIC,
                gaze_y NUMERIC,
                confidence NUMERIC,
                tracking_ok BOOLEAN,
                distance_cm_est NUMERIC,
                distance_zone TEXT,
                target_x NUMERIC,
                target_y NUMERIC,
                target_label TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS gaze_reports (
                session_id INTEGER PRIMARY KEY REFERENCES gaze_sessions(id) ON DELETE CASCADE,
                fixation_total_ms NUMERIC,
                mean_fixation_ms NUMERIC,
                saccade_count INTEGER,
                target_hit_rate NUMERIC,
                tracking_loss_pct NUMERIC,
                center_bias_pct NUMERIC,
                distance_mean_cm NUMERIC,
                distance_min_cm NUMERIC,
                distance_max_cm NUMERIC,
                distance_std_cm NUMERIC,
                time_near_pct NUMERIC,
                time_mid_pct NUMERIC,
                time_far_pct NUMERIC,
                summary_json JSONB
            )
        """)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def insert_gaze_session(conn, payload: dict) -> int:
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO gaze_sessions (
                paziente_id,
                operatore,
                protocollo,
                camera_type,
                distance_cm,
                distance_mode,
                distance_target_min_cm,
                distance_target_max_cm,
                calibration_score,
                status,
                note
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            payload.get("paziente_id"),
            payload.get("operatore"),
            payload.get("protocollo"),
            payload.get("camera_type"),
            payload.get("distance_cm"),
            payload.get("distance_mode"),
            payload.get("distance_target_min_cm"),
            payload.get("distance_target_max_cm"),
            payload.get("calibration_score"),
            payload.get("status", "draft"),
            payload.get("note"),
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def insert_gaze_samples_bulk(conn, session_id: int, rows: list[dict]) -> int:
    cur = conn.cursor()
    try:
        count = 0
        for r in rows:
            cur.execute("""
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
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                session_id,
                r.get("ts_ms"),
                r.get("gaze_x"),
                r.get("gaze_y"),
                r.get("confidence"),
                r.get("tracking_ok"),
                r.get("distance_cm_est"),
                r.get("distance_zone"),
                r.get("target_x"),
                r.get("target_y"),
                r.get("target_label"),
            ))
            count += 1

        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def upsert_gaze_report(conn, session_id: int, report_payload: dict) -> None:
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO gaze_reports (
                session_id,
                fixation_total_ms,
                mean_fixation_ms,
                saccade_count,
                target_hit_rate,
                tracking_loss_pct,
                center_bias_pct,
                distance_mean_cm,
                distance_min_cm,
                distance_max_cm,
                distance_std_cm,
                time_near_pct,
                time_mid_pct,
                time_far_pct,
                summary_json
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_id)
            DO UPDATE SET
                fixation_total_ms = EXCLUDED.fixation_total_ms,
                mean_fixation_ms = EXCLUDED.mean_fixation_ms,
                saccade_count = EXCLUDED.saccade_count,
                target_hit_rate = EXCLUDED.target_hit_rate,
                tracking_loss_pct = EXCLUDED.tracking_loss_pct,
                center_bias_pct = EXCLUDED.center_bias_pct,
                distance_mean_cm = EXCLUDED.distance_mean_cm,
                distance_min_cm = EXCLUDED.distance_min_cm,
                distance_max_cm = EXCLUDED.distance_max_cm,
                distance_std_cm = EXCLUDED.distance_std_cm,
                time_near_pct = EXCLUDED.time_near_pct,
                time_mid_pct = EXCLUDED.time_mid_pct,
                time_far_pct = EXCLUDED.time_far_pct,
                summary_json = EXCLUDED.summary_json
        """, (
            session_id,
            report_payload.get("fixation_total_ms"),
            report_payload.get("mean_fixation_ms"),
            report_payload.get("saccade_count"),
            report_payload.get("target_hit_rate"),
            report_payload.get("tracking_loss_pct"),
            report_payload.get("center_bias_pct"),
            report_payload.get("distance_mean_cm"),
            report_payload.get("distance_min_cm"),
            report_payload.get("distance_max_cm"),
            report_payload.get("distance_std_cm"),
            report_payload.get("time_near_pct"),
            report_payload.get("time_mid_pct"),
            report_payload.get("time_far_pct"),
            json.dumps(report_payload.get("summary_json", {}), ensure_ascii=False),
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def get_gaze_session(conn, session_id: int) -> dict | None:
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM gaze_sessions WHERE id = %s", (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        cur.close()


def list_gaze_sessions_by_patient(conn, paziente_id: int) -> list[dict]:
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, paziente_id, operatore, protocollo, camera_type, status, created_at
            FROM gaze_sessions
            WHERE paziente_id = %s
            ORDER BY created_at DESC, id DESC
        """, (paziente_id,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        cur.close()


def delete_gaze_session(conn, session_id: int) -> None:
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM gaze_sessions WHERE id = %s", (session_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
