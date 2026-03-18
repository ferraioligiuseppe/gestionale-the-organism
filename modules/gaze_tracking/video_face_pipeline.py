from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

IMPORT_ERROR = None
MEDIAPIPE_AVAILABLE = True
NUMPY_AVAILABLE = True


def get_video_pipeline_status() -> dict[str, Any]:
    """Compat layer: il pipeline Python legacy è stato sostituito da quello browser-based."""
    return {
        "mediapipe_available": True,
        "import_error": None,
        "mode": "browser_based_compat",
        "message": "Pipeline video legacy dismesso: usare il modulo browser-based integrato.",
    }


def _build_compat_summary(protocol_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "report_version": "1.0.0-browser-compat",
        "module": "face_eye_oral_browser_based",
        "protocol_name": protocol_name,
        "metadata": metadata,
        "mode": "browser_based_compat",
        "warnings": [
            "Il vecchio pipeline Python server-side è stato sostituito dal modulo browser-based.",
            "Per analisi live completa usare la sezione Eye Tracking / Webcam AI del gestionale.",
        ],
    }


def analyze_face_image(
    image_bytes: bytes,
    protocol_name: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}

    if not image_bytes:
        return {"ok": False, "error": "Nessuna immagine ricevuta."}

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return {"ok": False, "error": f"Immagine non leggibile: {exc}"}

    width, height = image.size
    summary_json = _build_compat_summary(protocol_name=protocol_name, metadata=metadata)

    return {
        "ok": True,
        "mode": "browser_based_compat",
        "metrics": {
            "image_width_px": width,
            "image_height_px": height,
            "analysis_status": "compat_placeholder",
            "gaze_direction_label": "usa_modulo_browser_based",
            "head_tilt_deg": None,
            "oral_state": "usa_modulo_browser_based",
            "palpebral_asymmetry": None,
            "mouth_open_ratio": None,
            "left_eye_open_ratio": None,
            "right_eye_open_ratio": None,
            "gaze_horizontal_score": None,
        },
        "indexes": {
            "oral_instability_index": None,
            "oculo_postural_index": None,
            "facial_balance_index": None,
            "gaze_stability_index": None,
        },
        "warnings": summary_json["warnings"],
        "overlay_image": image_bytes,
        "summary_json": summary_json,
    }
