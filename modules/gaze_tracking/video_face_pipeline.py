
from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

IMPORT_ERROR = None

try:
    import mediapipe as mp
    import numpy as np
    MEDIAPIPE_AVAILABLE = True
except Exception as exc:
    mp = None
    np = None
    MEDIAPIPE_AVAILABLE = False
    IMPORT_ERROR = str(exc)

from .mediapipe_draw import draw_face_analysis_overlay
from .metrics_face_oral import compute_face_oral_indexes, compute_face_oral_metrics


LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]
LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263


def get_video_pipeline_status() -> dict[str, Any]:
    return {
        "mediapipe_available": MEDIAPIPE_AVAILABLE,
        "import_error": IMPORT_ERROR,
    }


def _extract_face_landmarks_px(image: Image.Image) -> tuple[dict[int, tuple[float, float]], list[str]]:
    warnings: list[str] = []

    if not MEDIAPIPE_AVAILABLE or mp is None or np is None:
        return {}, [f"MediaPipe import fallito: {IMPORT_ERROR or 'errore sconosciuto'}"]

    rgb_image = image.convert("RGB")
    arr = np.array(rgb_image)
    h, w = arr.shape[:2]

    try:
        face_mesh_module = mp.solutions.face_mesh
    except Exception as exc:
        return {}, [f"FaceMesh non disponibile in mediapipe: {exc}"]

    with face_mesh_module.FaceMesh(
        static_image_mode=True,
        refine_landmarks=True,
        max_num_faces=1,
        min_detection_confidence=0.5,
    ) as face_mesh:
        results = face_mesh.process(arr.copy())

    if not results.multi_face_landmarks:
        return {}, ["Nessun volto rilevato nello snapshot."]

    face_landmarks = results.multi_face_landmarks[0]
    points: dict[int, tuple[float, float]] = {}

    for idx, lm in enumerate(face_landmarks.landmark):
        points[idx] = (float(lm.x * w), float(lm.y * h))

    return points, warnings


def _mean_point(points: dict[int, tuple[float, float]], indexes: list[int]) -> tuple[float, float] | None:
    vals = [points[i] for i in indexes if i in points]
    if not vals:
        return None
    return (
        sum(p[0] for p in vals) / len(vals),
        sum(p[1] for p in vals) / len(vals),
    )


def _safe_point(points: dict[int, tuple[float, float]], idx: int) -> tuple[float, float] | None:
    return points.get(idx)


def _estimate_gaze_direction(points: dict[int, tuple[float, float]]) -> dict[str, Any]:
    left_iris = _mean_point(points, LEFT_IRIS)
    right_iris = _mean_point(points, RIGHT_IRIS)

    left_outer = _safe_point(points, LEFT_EYE_OUTER)
    left_inner = _safe_point(points, LEFT_EYE_INNER)
    right_inner = _safe_point(points, RIGHT_EYE_INNER)
    right_outer = _safe_point(points, RIGHT_EYE_OUTER)

    if not all([left_iris, right_iris, left_outer, left_inner, right_inner, right_outer]):
        return {
            "direction_label": "non_determinabile",
            "horizontal_score": None,
            "vertical_score": None,
            "left_iris_center": left_iris,
            "right_iris_center": right_iris,
        }

    def horizontal_ratio(center, outer, inner):
        width = inner[0] - outer[0]
        if abs(width) < 1e-6:
            return 0.0
        return ((center[0] - outer[0]) / width) - 0.5

    left_h = horizontal_ratio(left_iris, left_outer, left_inner)
    right_h = horizontal_ratio(right_iris, right_inner, right_outer)
    horizontal_score = float((left_h + right_h) / 2.0)

    left_mid_y = (left_outer[1] + left_inner[1]) / 2.0
    right_mid_y = (right_outer[1] + right_inner[1]) / 2.0
    vertical_score = float((((left_iris[1] - left_mid_y) + (right_iris[1] - right_mid_y)) / 2.0) / 15.0)

    direction = "centrale"
    if horizontal_score < -0.08:
        direction = "sinistra"
    elif horizontal_score > 0.08:
        direction = "destra"

    if vertical_score < -0.12:
        direction = f"{direction}-alto" if direction != "centrale" else "alto"
    elif vertical_score > 0.12:
        direction = f"{direction}-basso" if direction != "centrale" else "basso"

    return {
        "direction_label": direction,
        "horizontal_score": round(horizontal_score, 4),
        "vertical_score": round(vertical_score, 4),
        "left_iris_center": left_iris,
        "right_iris_center": right_iris,
    }


def analyze_face_image(image_bytes: bytes, protocol_name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}

    if not image_bytes:
        return {"ok": False, "error": "Nessuna immagine ricevuta."}

    if not MEDIAPIPE_AVAILABLE:
        return {
            "ok": False,
            "error": f"Import MediaPipe fallito: {IMPORT_ERROR or 'errore sconosciuto'}",
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

    gaze_estimate = _estimate_gaze_direction(landmarks_px)
    metrics["gaze_direction_label"] = gaze_estimate.get("direction_label")
    metrics["gaze_horizontal_score"] = gaze_estimate.get("horizontal_score")
    metrics["gaze_vertical_score"] = gaze_estimate.get("vertical_score")
    metrics["left_iris_center"] = gaze_estimate.get("left_iris_center")
    metrics["right_iris_center"] = gaze_estimate.get("right_iris_center")

    indexes = compute_face_oral_indexes(metrics)
    overlay = draw_face_analysis_overlay(image, landmarks_px, metrics)

    summary_json = {
        "report_version": "0.2.0-video-b",
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
