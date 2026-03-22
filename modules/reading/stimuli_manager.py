from __future__ import annotations

import json
from typing import Any, Dict


def parse_txt(text: str) -> Dict[str, Any]:
    return {
        "title": "Stimolo TXT",
        "category": "testo_libero",
        "language": "it",
        "school_level": "",
        "stimulus_type": "continuous_text",
        "text": text,
    }


def parse_json_file(file_obj) -> Dict[str, Any]:
    return json.load(file_obj)
