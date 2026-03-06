from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Optional

from .utils import table_exists, fetch_rows_by_period, first_row

def load_generic_dataset(conn, table: str, paziente_id: int, date_from: dt.date, date_to: dt.date, include_deleted: bool = False, limit: int = 200) -> Dict[str, Any]:
    if not table_exists(conn, table):
        return {table: {"presente": False, "righe": [], "righe_count": 0}}
    rows = fetch_rows_by_period(conn, table, paziente_id, date_from, date_to, include_deleted=include_deleted, limit=limit)
    return {table: {"presente": True, "righe": rows, "righe_count": len(rows)}}

def load_single_row(conn, table: str, paziente_id: int, include_deleted: bool = False) -> Dict[str, Any]:
    if not table_exists(conn, table):
        return {table: {"presente": False, "record": None}}
    row = first_row(conn, table, paziente_id, include_deleted=include_deleted)
    return {table: {"presente": True, "record": row}}
