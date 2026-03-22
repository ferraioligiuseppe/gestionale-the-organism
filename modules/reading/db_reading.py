from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def ensure_reading_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_stimuli (
                id SERIAL PRIMARY KEY,
                title TEXT,
                category TEXT,
                language TEXT,
                school_level TEXT,
                stimulus_type TEXT,
                content_json JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_sessions (
                id SERIAL PRIMARY KEY,
                patient_id INTEGER,
                stimulus_id INTEGER,
                device_type TEXT,
                reading_mode TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                raw_eye_json JSONB,
                raw_orofacial_json JSONB,
                metrics_json JSONB,
                notes TEXT
            );
            """
        )
    conn.commit()


def save_stimulus(conn, data: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO reading_stimuli
            (title, category, language, school_level, stimulus_type, content_json)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)
            """,
            (
                data.get("title"),
                data.get("category"),
                data.get("language"),
                data.get("school_level"),
                data.get("stimulus_type"),
                json.dumps(data, ensure_ascii=False),
            ),
        )
    conn.commit()


def get_stimuli(conn) -> List[Tuple[int, str]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, COALESCE(title, 'Stimolo senza titolo') FROM reading_stimuli ORDER BY id DESC"
        )
        return cur.fetchall() or []


def get_stimulus(conn, stimulus_id: int) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_json FROM reading_stimuli WHERE id = %s",
            (int(stimulus_id),),
        )
        row = cur.fetchone()
        if not row:
            return None
        payload = row[0]
        if isinstance(payload, dict):
            return payload
        try:
            return json.loads(payload)
        except Exception:
            return None
