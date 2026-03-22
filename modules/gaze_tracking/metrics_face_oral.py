
from __future__ import annotations

from typing import Any
import math

LEFT_EYE_OUTER = 33
LEFT_EYE_INNER = 133
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263
LEFT_UPPER_LID = 159
LEFT_LOWER_LID = 145
RIGHT_UPPER_LID = 386
RIGHT_LOWER_LID = 374

UPPER_LIP = 13
LOWER_LIP = 14
MOUTH_LEFT = 61
MOUTH_RIGHT = 291

NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152


def _distance(a: tuple[float, float] | None, b: tuple[float, float] | None) -> float | None:
    if a is None or b is None:
        return None
    return math.dist(a, b)


def _safe_point(points: dict[int, tuple[float, float]], idx: int) -> tuple[float, float] | None:
    return points.get(idx)


def compute_face_oral_metrics(points: dict[int, tuple[float, float]]) -> dict[str, Any]:
    if not points:
        return {"ok": False, "error": "Landmarks non disponibili."}

    left_outer = _safe_point(points, LEFT_EYE_OUTER)
    left_inner = _safe_point(points, LEFT_EYE_INNER)
    right_inner = _safe_point(points, RIGHT_EYE_INNER)
    right_outer = _safe_point(points, RIGHT_EYE_OUTER)
    left_upper = _safe_point(points, LEFT_UPPER_LID)
    left_lower = _safe_point(points, LEFT_LOWER_LID)
    right_upper = _safe_point(points, RIGHT_UPPER_LID)
    right_lower = _safe_point(points, RIGHT_LOWER_LID)

    mouth_up = _safe_point(points, UPPER_LIP)
    mouth_low = _safe_point(points, LOWER_LIP)
    mouth_left = _safe_point(points, MOUTH_LEFT)
    mouth_right = _safe_point(points, MOUTH_RIGHT)

    forehead = _safe_point(points, FOREHEAD)
    chin = _safe_point(points, CHIN)

    face_height = _distance(forehead, chin)
    mouth_open_px = _distance(mouth_up, mouth_low)
    mouth_width_px = _distance(mouth_left, mouth_right)

    left_eye_width_px = _distance(left_outer, left_inner)
    right_eye_width_px = _distance(right_inner, right_outer)
    left_eye_open_px = _distance(left_upper, left_lower)
    right_eye_open_px = _distance(right_upper, right_lower)

    if not face_height or face_height <= 0:
        return {"ok": False, "error": "Volto non sufficientemente rilevato."}

    eye_open_mean_px = None
    if left_eye_open_px is not None and right_eye_open_px is not None:
        eye_open_mean_px = (left_eye_open_px + right_eye_open_px) / 2.0

    mouth_open_ratio = round((mouth_open_px / face_height), 4) if mouth_open_px is not None else None
    mouth_width_ratio = round((mouth_width_px / face_height), 4) if mouth_width_px is not None else None

    left_eye_open_ratio = round((left_eye_open_px / left_eye_width_px), 4) if left_eye_open_px and left_eye_width_px else None
    right_eye_open_ratio = round((right_eye_open_px / right_eye_width_px), 4) if right_eye_open_px and right_eye_width_px else None

    palpebral_asymmetry = None
    if left_eye_open_ratio is not None and right_eye_open_ratio is not None:
        palpebral_asymmetry = round(abs(left_eye_open_ratio - right_eye_open_ratio), 4)

    head_tilt_deg = None
    if forehead is not None and chin is not None:
        dx = chin[0] - forehead[0]
        dy = chin[1] - forehead[1]
        head_tilt_deg = round(math.degrees(math.atan2(dx, dy)), 2)

    oral_state = "chiusa"
    if mouth_open_ratio is not None:
        if mouth_open_ratio >= 0.09:
            oral_state = "aperta"
        elif mouth_open_ratio >= 0.05:
            oral_state = "semiaperta"

    return {
        "ok": True,
        "face_height_px": round(face_height, 2),
        "mouth_open_px": round(mouth_open_px, 2) if mouth_open_px is not None else None,
        "mouth_width_px": round(mouth_width_px, 2) if mouth_width_px is not None else None,
        "mouth_open_ratio": mouth_open_ratio,
        "mouth_width_ratio": mouth_width_ratio,
        "oral_state": oral_state,
        "left_eye_open_ratio": left_eye_open_ratio,
        "right_eye_open_ratio": right_eye_open_ratio,
        "eye_open_mean_px": round(eye_open_mean_px, 2) if eye_open_mean_px is not None else None,
        "palpebral_asymmetry": palpebral_asymmetry,
        "head_tilt_deg": head_tilt_deg,
    }


def compute_face_oral_indexes(metrics: dict[str, Any]) -> dict[str, Any]:
    if not metrics.get("ok"):
        return {"ok": False}

    mouth_open_ratio = metrics.get("mouth_open_ratio") or 0.0
    palpebral_asymmetry = metrics.get("palpebral_asymmetry") or 0.0
    head_tilt_deg = abs(metrics.get("head_tilt_deg") or 0.0)

    oral_instability_index = round((mouth_open_ratio * 100) + (palpebral_asymmetry * 40), 2)
    oculo_postural_index = round((head_tilt_deg * 0.7) + (palpebral_asymmetry * 100), 2)
    facial_balance_index = round(max(0.0, 100.0 - (head_tilt_deg * 2.5) - (palpebral_asymmetry * 120)), 2)

    gaze_direction = metrics.get("gaze_direction_label") or "non_determinabile"
    gaze_stability_index = 50.0
    if gaze_direction == "centrale":
        gaze_stability_index = 85.0
    elif gaze_direction in {"sinistra", "destra", "alto", "basso"}:
        gaze_stability_index = 65.0
    elif gaze_direction != "non_determinabile":
        gaze_stability_index = 55.0

    return {
        "ok": True,
        "oral_instability_index": oral_instability_index,
        "oculo_postural_index": oculo_postural_index,
        "facial_balance_index": facial_balance_index,
        "gaze_stability_index": gaze_stability_index,
    }
