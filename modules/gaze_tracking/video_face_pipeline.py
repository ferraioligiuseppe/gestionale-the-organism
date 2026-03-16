
from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

try:
    import mediapipe as mp
    import numpy as np
    MEDIAPIPE_AVAILABLE = True
except Exception:
    mp = None
    np = None
    MEDIAPIPE_AVAILABLE = False

from .mediapipe_draw import draw_landmarks_on_image
from .metrics_face_oral import compute_face_oral_indexes, compute_face_oral_metrics



def get_video_pipeline_status() -> dict[str, Any]:
    return {
        "mediapipe_available": MEDIAPIPE_AVAILABLE,
    }



def _extract_face_landmarks_px(image: Image.Image) -> tuple[dict[int, tuple[float, float]], list[str]]:
    warnings: list[str] = []
    if not MEDIAPIPE_AVAILABLE:
        return {}, ["MediaPipe non disponibile nell'ambiente."]

    rgb_image = image.convert("RGB")
    arr = np.array(rgb_image)
    h, w = arr.shape[:2]

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        refine_landmarks=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(arr)

    if not results.multi_face_landmarks:
        return {}, ["Nessun volto rilevato nello snapshot."]

    face_landmarks = results.multi_face_landmarks[0]
    points: dict[int, tuple[float, float]] = {}
    for idx, lm in enumerate(face_landmarks.landmark):
        points[idx] = (float(lm.x * w), float(lm.y * h))

    return points, warnings



def analyze_face_image(image_bytes: bytes, protocol_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}

    if not image_bytes:
        return {"ok": False, "error": "Nessuna immagine ricevuta."}

    if not MEDIAPIPE_AVAILABLE:
        return {
            "ok": False,
            "error": "MediaPipe non installato nell'ambiente. Installa mediapipe, opencv-python-headless, numpy e Pillow.",
        }

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        return {"ok": False, "error": f"Immagine non leggibile: {exc}"}

    landmarks_px, warnings = _extract_face_landmarks_px(image)
    if not landmarks_px:
        return {"ok": False, "error": warnings[0] if warnings else "Nessun volto rilevato.", "warnings": warnings}

    metrics = compute_face_oral_metrics(landmarks_px)
    if not metrics.get("ok", False):
        return {"ok": False, "error": metrics.get("error", "Metriche non calcolabili.")}

    indexes = compute_face_oral_indexes(metrics)
    overlay = draw_landmarks_on_image(image, landmarks_px)

    summary_json = {
        "report_version": "0.1.0-video-b",
        "module": "face_eye_oral",
        "protocol_name": protocol_name,
        "metadata": metadata,
        "metrics": metrics,
        "indexes": indexes,
        "warnings": warnings,
    }

    return {
        "ok": True,
        "metrics": metrics,
        "indexes": indexes,
        "warnings": warnings,
        "overlay_image": overlay,
        "summary_json": summary_json,
    }
