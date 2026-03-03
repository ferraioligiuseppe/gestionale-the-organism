# modules/stimolazione_uditiva/db_eq.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Tuple

from .db_orl import FREQS_STD

def _is_postgres(conn) -> bool:
    mod = getattr(conn.__class__, "__module__", "") or ""
    return "psycopg2" in mod or "pg8000" in mod or "psycopg" in mod

def save_eq_profile(
    conn,
    paziente_id: int,
    esame_id: int | None,
    nome: str,
    params: dict,
    gain_dx: Dict[int, float],
    gain_sx: Dict[int, float],
) -> int:
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                """
                INSERT INTO eq_profiles(paziente_id, esame_id, nome, params_json, gain_dx_json, gain_sx_json)
                VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
                RETURNING id
                """,
                (
                    int(paziente_id),
                    (int(esame_id) if esame_id is not None else None),
                    str(nome),
                    json.dumps(params),
                    json.dumps({str(k): float(gain_dx[k]) for k in FREQS_STD}),
                    json.dumps({str(k): float(gain_sx[k]) for k in FREQS_STD}),
                ),
            )
            pid = int(cur.fetchone()[0])
        else:
            cur.execute(
                """
                INSERT INTO eq_profiles(created_at, paziente_id, esame_id, nome, params_json, gain_dx_json, gain_sx_json)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    int(paziente_id),
                    (int(esame_id) if esame_id is not None else None),
                    str(nome),
                    json.dumps(params),
                    json.dumps({str(k): float(gain_dx[k]) for k in FREQS_STD}),
                    json.dumps({str(k): float(gain_sx[k]) for k in FREQS_STD}),
                ),
            )
            pid = int(cur.lastrowid)
        conn.commit()
        return pid
    finally:
        try: cur.close()
        except Exception: pass

def list_eq_profiles(conn, paziente_id: int, limit: int = 100) -> List[Tuple[int, str, str, int | None]]:
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                """
                SELECT id, nome, to_char(created_at,'YYYY-MM-DD HH24:MI:SS') AS created_at, esame_id
                FROM eq_profiles
                WHERE paziente_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (int(paziente_id), int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT id, nome, COALESCE(created_at,'') AS created_at, esame_id
                FROM eq_profiles
                WHERE paziente_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (int(paziente_id), int(limit)),
            )
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            out.append((int(r[0]), str(r[1] or ""), str(r[2] or ""), (int(r[3]) if r[3] is not None else None)))
        return out
    finally:
        try: cur.close()
        except Exception: pass
