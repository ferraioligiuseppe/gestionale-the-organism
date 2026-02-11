from __future__ import annotations
import json
from typing import Any, Dict

def is_pg_conn(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")

def ph(conn) -> str:
    return "%s" if is_pg_conn(conn) else "?"

def json_to_dict(val: Any) -> Dict[str, Any]:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, (bytes, bytearray, memoryview)):
        try:
            return json.loads(bytes(val).decode("utf-8"))
        except Exception:
            return {}
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}

def blob_to_bytes(val: Any) -> bytes:
    if val is None:
        return b""
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if isinstance(val, memoryview):
        return val.tobytes()
    return bytes(val)
