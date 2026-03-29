from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def _data_paths(base_dir: str) -> dict:
    data_dir = Path(base_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sessions = data_dir / "capture_sessions.json"
    captures = data_dir / "captures.json"
    if not sessions.exists():
        sessions.write_text("[]", encoding="utf-8")
    if not captures.exists():
        captures.write_text("[]", encoding="utf-8")
    return {"data_dir": str(data_dir), "sessions": str(sessions), "captures": str(captures)}

def _read_json(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_json(path: str, value: list[dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def create_capture_session(base_dir: str, record: dict[str, Any]) -> dict[str, Any]:
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    rows.append(record)
    _write_json(paths["sessions"], rows)
    return record

def get_session_by_token(base_dir: str, token: str) -> dict[str, Any] | None:
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    for row in reversed(rows):
        if row.get("token") == token:
            return row
    return None

def update_session_status(base_dir: str, token: str, **updates) -> dict[str, Any] | None:
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    updated = None
    for row in rows:
        if row.get("token") == token:
            row.update(updates)
            updated = row
            break
    _write_json(paths["sessions"], rows)
    return updated

def save_capture_record(base_dir: str, record: dict[str, Any]) -> dict[str, Any]:
    paths = _data_paths(base_dir)
    rows = _read_json(paths["captures"])
    rows.append(record)
    _write_json(paths["captures"], rows)
    return record

def list_recent_sessions(base_dir: str, limit: int = 20) -> list[dict[str, Any]]:
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    return list(reversed(rows))[:limit]
