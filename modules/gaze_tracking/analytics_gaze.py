
from __future__ import annotations
from math import hypot
from .distance_gaze import summarize_distance

def _target_hit_rate(samples: list[dict], current_targets: list[dict] | None, tolerance_px: float = 120.0) -> float:
    if not samples or not current_targets:
        return 0.0
    hits = 0
    checked = 0
    for s in samples:
        tx = s.get("target_x")
        ty = s.get("target_y")
        gx = s.get("gaze_x")
        gy = s.get("gaze_y")
        if tx is None or ty is None or gx is None or gy is None:
            continue
        checked += 1
        if hypot(float(gx) - float(tx), float(gy) - float(ty)) <= tolerance_px:
            hits += 1
    return round((hits / checked) * 100, 2) if checked else 0.0

def compute_basic_metrics(samples: list[dict], screen_w: int, screen_h: int, current_targets: list[dict] | None = None) -> dict:
    if not samples:
        base = {
            "fixation_total_ms": 0,
            "mean_fixation_ms": 0,
            "saccade_count": 0,
            "target_hit_rate": 0.0,
            "tracking_loss_pct": 100.0,
            "center_bias_pct": 0.0,
            "calibration_score": None,
        }
        base.update(summarize_distance(samples))
        return base

    total = len(samples)
    lost = sum(1 for s in samples if not s.get("tracking_ok", True))
    valid = [s for s in samples if s.get("tracking_ok", True) and s.get("gaze_x") is not None and s.get("gaze_y") is not None]

    center_x = screen_w / 2
    center_y = screen_h / 2
    center_radius = min(screen_w, screen_h) * 0.20

    center_hits = 0
    saccade_count = 0
    prev = None

    for s in valid:
        d = hypot(float(s["gaze_x"]) - center_x, float(s["gaze_y"]) - center_y)
        if d <= center_radius:
            center_hits += 1
        if prev is not None:
            jump = hypot(float(s["gaze_x"]) - float(prev["gaze_x"]), float(s["gaze_y"]) - float(prev["gaze_y"]))
            if jump > 80:
                saccade_count += 1
        prev = s

    tracking_loss_pct = round((lost / total) * 100, 2) if total else 100.0
    center_bias_pct = round((center_hits / len(valid)) * 100, 2) if valid else 0.0
    fixation_total_ms = len(valid) * 100
    mean_fixation_ms = 220 if valid else 0

    # score grezzo: più tracking ok e hit sui target, meglio è
    target_hit_rate = _target_hit_rate(samples, current_targets)
    calibration_score = round(max(0.0, 100.0 - (tracking_loss_pct * 0.6) - max(0.0, (100.0 - target_hit_rate)) * 0.2), 2)

    out = {
        "fixation_total_ms": fixation_total_ms,
        "mean_fixation_ms": mean_fixation_ms,
        "saccade_count": saccade_count,
        "target_hit_rate": target_hit_rate,
        "tracking_loss_pct": tracking_loss_pct,
        "center_bias_pct": center_bias_pct,
        "calibration_score": calibration_score,
    }
    out.update(summarize_distance(samples))
    return out
