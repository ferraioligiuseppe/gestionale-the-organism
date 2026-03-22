from __future__ import annotations

from typing import Any, Dict


def prepare_text(stimulus: Dict[str, Any]) -> str:
    if not stimulus:
        return ""

    stimulus_type = stimulus.get("stimulus_type", "continuous_text")

    if stimulus_type == "continuous_text":
        return str(stimulus.get("text", ""))

    if stimulus_type == "segmented_text":
        segments = stimulus.get("segments", []) or []
        return "\n".join(str(s.get("text", "")) for s in segments)

    return str(stimulus.get("text", ""))
