from __future__ import annotations
from math import hypot


def compute_basic_metrics(samples: list[dict], screen_w: int, screen_h: int, current_targets: list[dict] | None = None) -> dict:
    if not samples:
        return {
            "fixation_total_ms": 0,
            "mean_fixation_ms": 0,
            "saccade_count": 0,
            "target_hit_rate": 0,
            "tracking_loss_pct": 100.0,
            "center_bias_pct": 0.0,
            "sample_count": 0,
        }

    total = len(samples)
    valid = [s for s in samples if s.get("tracking_ok") and s.get("gaze_x") is not None and s.get("gaze_y") is not None]
    lost = total - len(valid)

    cx = screen_w / 2
    cy = screen_h / 2
    center_radius = min(screen_w, screen_h) * 0.20

    center_hits = 0
    saccades = 0
    prev = None
    hit_count = 0

    target_lookup = {}
    for t in current_targets or []:
        label = t.get("label")
        if label:
            target_lookup[label] = t

    for s in valid:
        if hypot(s["gaze_x"] - cx, s["gaze_y"] - cy) <= center_radius:
            center_hits += 1
        if prev is not None:
            jump = hypot(s["gaze_x"] - prev["gaze_x"], s["gaze_y"] - prev["gaze_y"])
            if jump >= 80:
                saccades += 1
        prev = s

        t = target_lookup.get(s.get("target_label"))
        if t:
            if hypot(s["gaze_x"] - t["x"], s["gaze_y"] - t["y"]) <= 120:
                hit_count += 1

    return {
        "fixation_total_ms": len(valid) * 33,
        "mean_fixation_ms": 220 if valid else 0,
        "saccade_count": int(saccades),
        "target_hit_rate": round((hit_count / len(valid)) * 100, 2) if valid else 0,
        "tracking_loss_pct": round((lost / total) * 100, 2) if total else 100,
        "center_bias_pct": round((center_hits / len(valid)) * 100, 2) if valid else 0,
        "sample_count": total,
    }
