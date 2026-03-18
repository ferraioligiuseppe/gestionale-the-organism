from __future__ import annotations

from typing import Any


def get_video_pipeline_status() -> dict[str, Any]:
    return {
        "mediapipe_available": True,
        "import_error": None,
        "mode": "browser_based_compat",
        "warnings": [
            "Pipeline legacy Python disattivata.",
            "Usare il modulo browser-based ui_webcam_browser_v3 per acquisizione live.",
        ],
    }


def analyze_face_image(image_bytes: bytes, protocol_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "ok": True,
        "mode": "browser_based_compat",
        "metrics": {"analysis_status": "legacy_pipeline_bypassed"},
        "indexes": {},
        "warnings": ["Analisi server-side non utilizzata. Fare riferimento alla sessione browser-based."],
        "overlay_image": image_bytes,
        "summary_json": {"protocol_name": protocol_name, "metadata": metadata},
    }
