
from __future__ import annotations

from typing import Any


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5



def _safe_ratio(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return round(num / den, 4)



def compute_face_oral_metrics(landmarks_px: dict[int, tuple[float, float]]) -> dict[str, Any]:
    required = [33, 133, 159, 145, 362, 263, 386, 374, 61, 291, 13, 14, 10, 152, 1]
    missing = [idx for idx in required if idx not in landmarks_px]
    if missing:
        return {
            "ok": False,
            "error": f"Landmark mancanti per metriche base: {missing[:10]}",
        }

    left_eye_width = _distance(landmarks_px[33], landmarks_px[133])
    left_eye_open = _distance(landmarks_px[159], landmarks_px[145])
    right_eye_width = _distance(landmarks_px[362], landmarks_px[263])
    right_eye_open = _distance(landmarks_px[386], landmarks_px[374])

    mouth_width = _distance(landmarks_px[61], landmarks_px[291])
    mouth_open = _distance(landmarks_px[13], landmarks_px[14])

    face_height = _distance(landmarks_px[10], landmarks_px[152])
    head_dx = landmarks_px[152][0] - landmarks_px[10][0]
    head_dy = landmarks_px[152][1] - landmarks_px[10][1]

    eye_ratio_left = _safe_ratio(left_eye_open, left_eye_width)
    eye_ratio_right = _safe_ratio(right_eye_open, right_eye_width)
    eye_ratio_mean = None
    if eye_ratio_left is not None and eye_ratio_right is not None:
        eye_ratio_mean = round((eye_ratio_left + eye_ratio_right) / 2.0, 4)

    mouth_ratio = _safe_ratio(mouth_open, mouth_width)
    mouth_face_ratio = _safe_ratio(mouth_open, face_height)

    head_tilt_deg = None
    if head_dx != 0 or head_dy != 0:
        import math
        head_tilt_deg = round(math.degrees(math.atan2(head_dx, head_dy)), 2)

    face_center_x = (landmarks_px[33][0] + landmarks_px[263][0]) / 2.0
    nose_x = landmarks_px[1][0]
    face_width = _distance(landmarks_px[33], landmarks_px[263])
    head_yaw_est = _safe_ratio(nose_x - face_center_x, face_width)

    return {
        "ok": True,
        "eye_aperture_ratio_left": eye_ratio_left,
        "eye_aperture_ratio_right": eye_ratio_right,
        "eye_aperture_ratio_mean": eye_ratio_mean,
        "mouth_opening_ratio": mouth_ratio,
        "mouth_face_opening_ratio": mouth_face_ratio,
        "head_tilt_deg": head_tilt_deg,
        "head_yaw_est": head_yaw_est,
        "face_height_px": round(face_height, 2),
        "face_width_px": round(face_width, 2),
    }



def compute_face_oral_indexes(metrics: dict[str, Any]) -> dict[str, Any]:
    eye = metrics.get("eye_aperture_ratio_mean") or 0.0
    mouth = metrics.get("mouth_opening_ratio") or 0.0
    tilt = abs(metrics.get("head_tilt_deg") or 0.0)
    yaw = abs(metrics.get("head_yaw_est") or 0.0)

    oculo_postural_index = round((tilt / 10.0) + (yaw * 5.0) + max(0.0, 0.35 - eye), 2)
    oral_motor_index = round((mouth * 10.0) + (yaw * 2.0), 2)
    pnev_multimodal_index = round((oculo_postural_index * 0.6) + (oral_motor_index * 0.4), 2)

    return {
        "oculo_postural_index": oculo_postural_index,
        "oral_motor_index": oral_motor_index,
        "pnev_multimodal_index": pnev_multimodal_index,
    }
