# modules/stimolazione_uditiva/db_eq.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Tuple

from .db_orl import FREQS_STD

# --- B2 ADDON: read_eq_profile -------------------------------------------------
import json

def read_eq_profile(conn, eq_profile_id: int):
    """
    Legge un profilo EQ salvato e ritorna:
      (nome, params_dict, gain_dx_dict, gain_sx_dict)

    gain_* sono dict con chiavi int (freq Hz) e valori float (dB).
    Compatibile con psycopg2: i JSONB possono arrivare come dict oppure come stringa.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT nome, params_json, gain_dx_json, gain_sx_json FROM eq_profiles WHERE id=%s",
            (int(eq_profile_id),),
        )
        row = cur.fetchone()
        if not row:
            return None

        nome, params_j, dx_j, sx_j = row

        def _load(x):
            if x is None:
                return {}
            if isinstance(x, (dict, list)):
                return x
            return json.loads(x)

        params = _load(params_j)

        dx_raw = _load(dx_j)
        sx_raw = _load(sx_j)

        gain_dx = {int(k): float(v) for k, v in dx_raw.items()}
        gain_sx = {int(k): float(v) for k, v in sx_raw.items()}

        return str(nome), params, gain_dx, gain_sx
    finally:
        try:
            cur.close()
        except Exception:
            pass
def _is_postgres(conn) -> bool:
    mod = (getattr(conn.__class__, "__module__", "") or "").lower()
    name = (getattr(conn.__class__, "__name__", "") or "").lower()
    if "sqlite3" in mod or "sqlite" in mod or "sqlite" in name:
        return False
    return True
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

def list_eq_profiles(conn, paziente_id: int, limit: int = 100):
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                """
                SELECT
                  id,
                  nome,
                  COALESCE(created_at::text,'') AS created_at,
                  esame_id
                FROM eq_profiles
                WHERE paziente_id = %s
                ORDER BY id DESC
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
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(paziente_id), int(limit)),
            )
        return cur.fetchall() or []
    finally:
        try:
            cur.close()
        except Exception:
            pass
