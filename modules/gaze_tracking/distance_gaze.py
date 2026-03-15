
from __future__ import annotations
from statistics import mean, pstdev

def estimate_distance_from_face(face_width_px: float | None, ref_face_width_px: float | None, ref_distance_cm: float | None) -> float | None:
    """Stima semplice della distanza monitor-volto.
    Formula proporzionale: distanza = ref_distance * ref_face_width / face_width.
    """
    if not face_width_px or face_width_px <= 0:
        return None
    if not ref_face_width_px or ref_face_width_px <= 0:
        return None
    if not ref_distance_cm or ref_distance_cm <= 0:
        return None
    return round(float(ref_distance_cm) * float(ref_face_width_px) / float(face_width_px), 2)

def classify_distance_zone(distance_cm: float | None, near_max: float = 35.0, mid_max: float = 55.0) -> str:
    if distance_cm is None:
        return "unknown"
    if distance_cm < near_max:
        return "near"
    if distance_cm <= mid_max:
        return "mid"
    return "far"

def summarize_distance(samples: list[dict]) -> dict:
    vals = [float(s["distance_cm_est"]) for s in samples if s.get("distance_cm_est") is not None]
    if not vals:
        return {
            "distance_mean_cm": None,
            "distance_min_cm": None,
            "distance_max_cm": None,
            "distance_std_cm": None,
            "time_near_pct": 0.0,
            "time_mid_pct": 0.0,
            "time_far_pct": 0.0,
        }

    total = len(vals)
    near = sum(1 for s in samples if s.get("distance_zone") == "near")
    mid = sum(1 for s in samples if s.get("distance_zone") == "mid")
    far = sum(1 for s in samples if s.get("distance_zone") == "far")

    return {
        "distance_mean_cm": round(mean(vals), 2),
        "distance_min_cm": round(min(vals), 2),
        "distance_max_cm": round(max(vals), 2),
        "distance_std_cm": round(pstdev(vals), 2) if len(vals) > 1 else 0.0,
        "time_near_pct": round((near / total) * 100, 2),
        "time_mid_pct": round((mid / total) * 100, 2),
        "time_far_pct": round((far / total) * 100, 2),
    }
