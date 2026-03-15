def build_9_point_calibration(screen_w: int, screen_h: int) -> list[dict]:
    xs = [0.1, 0.5, 0.9]
    ys = [0.1, 0.5, 0.9]
    points = []
    for y in ys:
        for x in xs:
            points.append({
                "target_type": "calibration",
                "x": round(screen_w * x, 2),
                "y": round(screen_h * y, 2),
                "label": f"{int(x*100)}_{int(y*100)}",
            })
    return points


def build_fixation_task(screen_w: int, screen_h: int, duration_ms: int = 5000) -> list[dict]:
    return [{
        "target_type": "fixation",
        "x": round(screen_w / 2, 2),
        "y": round(screen_h / 2, 2),
        "start_ms": 0,
        "end_ms": duration_ms,
        "label": "center_fixation",
    }]


def build_horizontal_saccades(screen_w: int, screen_h: int, cycles: int = 8) -> list[dict]:
    y = screen_h / 2
    left = screen_w * 0.2
    right = screen_w * 0.8
    targets = []
    t = 0
    for i in range(cycles):
        targets.append({"target_type": "saccade", "x": round(left,2), "y": round(y,2), "start_ms": t, "end_ms": t + 900, "label": f"L{i+1}"})
        t += 900
        targets.append({"target_type": "saccade", "x": round(right,2), "y": round(y,2), "start_ms": t, "end_ms": t + 900, "label": f"R{i+1}"})
        t += 900
    return targets
