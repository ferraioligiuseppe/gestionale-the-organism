from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Optional

from .utils import table_exists, fetch_rows_by_period, first_row

OSTEO_ANAM_TABLES = ["osteo_anamnesi", "anamnesi_osteopatica"]
OSTEO_SED_TABLES  = ["osteo_seduta", "sedute_osteopatia"]

def load_osteopatia_dataset(conn, paziente_id: int, date_from: dt.date, date_to: dt.date, include_deleted: bool = False) -> Dict[str, Any]:
    # pick first existing table names
    anam_table = next((t for t in OSTEO_ANAM_TABLES if table_exists(conn, t)), None)
    sed_table  = next((t for t in OSTEO_SED_TABLES if table_exists(conn, t)), None)

    anam_obj: Optional[Dict[str, Any]] = None
    if anam_table:
        anam_obj = first_row(conn, anam_table, paziente_id, include_deleted=include_deleted)

    sedute: List[Dict[str, Any]] = []
    if sed_table:
        sedute = fetch_rows_by_period(conn, sed_table, paziente_id, date_from, date_to, include_deleted=include_deleted, limit=200)

    return {
        "osteopatia": {
            "tabelle_rilevate": {"anamnesi": anam_table, "sedute": sed_table},
            "anamnesi": anam_obj,
            "sedute": sedute,
            "sedute_count": len(sedute),
        }
    }
