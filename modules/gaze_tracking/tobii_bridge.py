from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List


def run_tobii_session_placeholder(duration_sec: int = 20) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "device_name": "Tobii (placeholder)",
        "duration_sec": duration_sec,
        "samples": [],
    }


def save_session_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
