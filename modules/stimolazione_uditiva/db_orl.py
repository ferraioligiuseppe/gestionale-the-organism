# modules/stimolazione_uditiva/db_orl.py
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Tuple

FREQS_STD = [125, 250, 500, 1000, 2000, 4000, 6000, 8000]

def _is_postgres(conn) -> bool:
    mod = (getattr(conn.__class__, "__module__", "") or "").lower()
    name = (getattr(conn.__class__, "__name__", "") or "").lower()
    if "sqlite3" in mod or "sqlite" in mod or "sqlite" in name:
        return False
    return True

def list_orl_esami(conn, paziente_id: int, limit: int = 50) -> List[Tuple[int, str, str]]:
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                """
                SELECT id, COALESCE(to_char(data_esame,'YYYY-MM-DD'),'') AS data_esame, COALESCE(fonte,'') AS fonte
                FROM orl_esami
                WHERE paziente_id = %s
                ORDER BY data_esame DESC NULLS LAST, id DESC
                LIMIT %s
                """,
                (int(paziente_id), int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT id, COALESCE(data_esame,'') AS data_esame, COALESCE(fonte,'') AS fonte
                FROM orl_esami
                WHERE paziente_id = ?
                ORDER BY data_esame DESC, id DESC
                LIMIT ?
                """,
                (int(paziente_id), int(limit)),
            )
        rows = cur.fetchall() or []
        return [(int(r[0]), str(r[1] or ""), str(r[2] or "")) for r in rows]
    finally:
        try: cur.close()
        except Exception: pass

def get_orl_soglie(conn, esame_id: int) -> Dict[str, Dict[int, float | None]]:
    cur = conn.cursor()
    out = {"DX": {f: None for f in FREQS_STD}, "SX": {f: None for f in FREQS_STD}}
    try:
        if _is_postgres(conn):
            cur.execute(
                "SELECT ear, freq_hz, db_hl FROM orl_soglie WHERE esame_id = %s",
                (int(esame_id),),
            )
        else:
            cur.execute(
                "SELECT ear, freq_hz, db_hl FROM orl_soglie WHERE esame_id = ?",
                (int(esame_id),),
            )
        rows = cur.fetchall() or []
        for ear, freq, dbhl in rows:
            ear = str(ear or "").upper()
            try:
                freq_i = int(freq)
            except Exception:
                continue
            if ear in ("DX", "SX") and freq_i in out[ear]:
                out[ear][freq_i] = None if dbhl is None else float(dbhl)
        return out
    finally:
        try: cur.close()
        except Exception: pass

def upsert_orl_esame(
    conn,
    paziente_id: int,
    data_esame: date | None,
    fonte: str | None,
    note: str | None,
    soglie_dx: Dict[int, float | None],
    soglie_sx: Dict[int, float | None],
) -> int:
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                "INSERT INTO orl_esami(paziente_id, data_esame, fonte, note) VALUES (%s,%s,%s,%s) RETURNING id",
                (int(paziente_id), data_esame, fonte, note),
            )
            esame_id = int(cur.fetchone()[0])
            for ear, soglie in (("DX", soglie_dx), ("SX", soglie_sx)):
                for f in FREQS_STD:
                    cur.execute(
                        """
                        INSERT INTO orl_soglie(esame_id, ear, freq_hz, db_hl)
                        VALUES (%s,%s,%s,%s)
                        ON CONFLICT (esame_id, ear, freq_hz) DO UPDATE SET db_hl = EXCLUDED.db_hl
                        """,
                        (esame_id, ear, int(f), soglie.get(f)),
                    )
        else:
            cur.execute(
                "INSERT INTO orl_esami(created_at, paziente_id, data_esame, fonte, note) VALUES (?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), int(paziente_id), (data_esame.isoformat() if data_esame else None), fonte, note),
            )
            esame_id = int(cur.lastrowid)
            for ear, soglie in (("DX", soglie_dx), ("SX", soglie_sx)):
                for f in FREQS_STD:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO orl_soglie(esame_id, ear, freq_hz, db_hl)
                        VALUES (?,?,?,?)
                        """,
                        (esame_id, ear, int(f), soglie.get(f)),
                    )
        conn.commit()
        return esame_id
    finally:
        try: cur.close()
        except Exception: pass
