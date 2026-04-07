from __future__ import annotations
import json
from pathlib import Path

def _data_paths(base_dir: str) -> dict:
    data_dir = Path(base_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    sessions = data_dir / "capture_sessions.json"
    captures = data_dir / "captures.json"
    analyses = data_dir / "analyses.json"
    for p in (sessions, captures, analyses):
        if not p.exists():
            p.write_text("[]", encoding="utf-8")
    return {"sessions": str(sessions), "captures": str(captures), "analyses": str(analyses)}

def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_json(path: str, value):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def create_capture_session(base_dir: str, record: dict):
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    rows.append(record)
    _write_json(paths["sessions"], rows)
    return record

def get_session_by_token(base_dir: str, token: str):
    paths = _data_paths(base_dir)
    rows = _read_json(paths["sessions"])
    for row in reversed(rows):
        if row.get("token") == token:
            return row
    return None

def update_session_status(base_dir: str, token: str, **updates):
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

def save_capture_record(base_dir: str, record: dict):
    paths = _data_paths(base_dir)
    rows = _read_json(paths["captures"])
    rows.append(record)
    _write_json(paths["captures"], rows)
    return record

def save_analysis_record(base_dir: str, record: dict):
    paths = _data_paths(base_dir)
    rows = _read_json(paths["analyses"])
    rows.append(record)
    _write_json(paths["analyses"], rows)
    return record

def list_recent_sessions(base_dir: str, limit: int = 20):
    paths = _data_paths(base_dir)
    return list(reversed(_read_json(paths["sessions"])))[:limit]

def list_recent_captures(base_dir: str, limit: int = 20):
    paths = _data_paths(base_dir)
    return list(reversed(_read_json(paths["captures"])))[:limit]

def list_recent_analyses(base_dir: str, limit: int = 20):
    paths = _data_paths(base_dir)
    return list(reversed(_read_json(paths["analyses"])))[:limit]
