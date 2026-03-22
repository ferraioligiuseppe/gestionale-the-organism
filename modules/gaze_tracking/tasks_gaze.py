
from __future__ import annotations
from .calibration_gaze import build_calibration_points

def build_9_point_calibration(screen_w: int, screen_h: int) -> list[dict]:
    return build_calibration_points(screen_w, screen_h)

def build_fixation_task(screen_w: int, screen_h: int, duration_ms: int = 5000) -> list[dict]:
    return [{
        "x": screen_w / 2,
        "y": screen_h / 2,
        "label": "center_fixation",
        "start_ms": 0,
        "end_ms": duration_ms,
    }]

def build_horizontal_saccades(screen_w: int, screen_h: int, cycles: int = 8) -> list[dict]:
    y = screen_h / 2
    left = screen_w * 0.2
    right = screen_w * 0.8
    targets = []
    for i in range(cycles):
        targets.append({"x": left, "y": y, "label": f"L{i+1}"})
        targets.append({"x": right, "y": y, "label": f"R{i+1}"})
    return targets
