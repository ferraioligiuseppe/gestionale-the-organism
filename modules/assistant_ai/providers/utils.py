from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

def table_exists(conn, table: str, schema: str = "public") -> bool:
    q = """
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = %s AND table_name = %s
    LIMIT 1;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (schema, table))
        return cur.fetchone() is not None
    finally:
        try: cur.close()
        except Exception: pass

def get_columns(conn, table: str, schema: str = "public") -> List[str]:
    q = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (schema, table))
        return [r[0] for r in cur.fetchall()]
    finally:
        try: cur.close()
        except Exception: pass

def pick_date_column(columns: List[str]) -> Optional[str]:
    candidates = [
        "data_seduta", "data_anamnesi", "data_visita", "data_valutazione", "data",
        "created_at", "timestamp", "ts"
    ]
    cols_set = set(columns)
    for c in candidates:
        if c in cols_set:
            return c
    return None

def safe_ident(name: str) -> str:
    # very small whitelist: letters, numbers, underscore only
    import re
    if not re.fullmatch(r"[A-Za-z0-9_]+", name or ""):
        raise ValueError("Invalid identifier")
    return name

def fetch_rows_by_period(conn, table: str, paziente_id: int, date_from: dt.date, date_to: dt.date, include_deleted: bool = False, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Carica righe da una tabella che abbia una colonna paziente_id.
    Se esiste is_deleted, filtra di default (a meno che include_deleted=True).
    """
    cols = get_columns(conn, table)
    if "paziente_id" not in cols:
        return []

    date_col = pick_date_column(cols)
    where = "paziente_id = %s"
    params: List[Any] = [paziente_id]

    if not include_deleted and "is_deleted" in cols:
        where += " AND is_deleted = FALSE"

    if date_col:
        where += f" AND {safe_ident(date_col)} >= %s AND {safe_ident(date_col)} <= %s"
        params += [date_from, date_to]

    q = f"SELECT * FROM {safe_ident(table)} WHERE {where} ORDER BY {safe_ident(date_col) if date_col else 'paziente_id'} DESC LIMIT {int(limit)};"

    cur = conn.cursor()
    try:
        cur.execute(q, tuple(params))
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
    finally:
        try: cur.close()
        except Exception: pass

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({desc[i]: r[i] for i in range(len(desc))})
    return out

def first_row(conn, table: str, paziente_id: int, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    import datetime as dt
    rows = fetch_rows_by_period(conn, table, paziente_id, dt.date(1900,1,1), dt.date(2100,1,1), include_deleted=include_deleted, limit=1)
    return rows[0] if rows else None
