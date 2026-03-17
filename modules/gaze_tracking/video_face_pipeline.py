from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image


IMPORT_ERROR = None

try:
    # Cloud-safe fallback: do not import mediapipe/opencv on Streamlit Cloud
    # to avoid libGL / native dependency failures.
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception as exc:
    np = None
    NUMPY_AVAILABLE = False
    IMPORT_ERROR = str(exc)

MEDIAPIPE_AVAILABLE = False


def get_video_pipeline_status() -> dict[str, Any]:
    return {
        "mediapipe_available": False,
        "import_error": (
            "Modalità cloud-safe attiva: analisi FaceMesh/MediaPipe disabilitata "
            "in ambiente Streamlit Cloud per evitare errori di librerie native "
            "(es. libGL.so.1). Usa ambiente locale o server dedicato per il modulo video AI completo."
        ),
    }


def _build_stub_summary(protocol_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "report_version": "0.3.0-cloud-safe",
        "module": "face_eye_oral_stub",
        "protocol_name": protocol_name,
        "metadata": metadata,
        "mode": "cloud_safe_stub",
        "warnings": [
            "Modulo video AI avanzato disabilitato su Streamlit Cloud.",
            "Per volto/occhi/bocca/postura con FaceMesh serve esecuzione locale o server dedicato con dipendenze native abilitate.",
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
    summary_json = _build_stub_summary(protocol_name=protocol_name, metadata=metadata)

    return {
        "ok": True,
        "mode": "cloud_safe_stub",
        "metrics": {
            "image_width_px": width,
            "image_height_px": height,
            "analysis_status": "stub_cloud_safe",
            "gaze_direction_label": "non_disponibile_su_cloud",
            "head_tilt_deg": None,
            "oral_state": "non_disponibile_su_cloud",
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
