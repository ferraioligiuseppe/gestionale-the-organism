
from __future__ import annotations

def build_calibration_points(screen_w: int, screen_h: int) -> list[dict]:
    xs = [0.1, 0.5, 0.9]
    ys = [0.1, 0.5, 0.9]
    points = []
    labels = [
        "alto_sx","alto_centro","alto_dx",
        "centro_sx","centro","centro_dx",
        "basso_sx","basso_centro","basso_dx",
    ]
    i = 0
    for y in ys:
        for x in xs:
            points.append({
                "x": round(screen_w * x, 2),
                "y": round(screen_h * y, 2),
                "label": labels[i],
            })
            i += 1
    return points
