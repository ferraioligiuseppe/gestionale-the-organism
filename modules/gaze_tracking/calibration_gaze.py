import time

def build_calibration_points(screen_w, screen_h):
    xs = [0.1, 0.5, 0.9]
    ys = [0.1, 0.5, 0.9]

    points = []
    for y in ys:
        for x in xs:
            points.append({
                "x": screen_w * x,
                "y": screen_h * y
            })
    return points


def calibration_sequence(points, duration=2.0):
    for i, p in enumerate(points):
        yield {
            "index": i,
            "x": p["x"],
            "y": p["y"],
            "duration": duration
        }
