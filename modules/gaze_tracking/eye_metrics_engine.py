import math


# =========================
# UTILS
# =========================

def distance(p1, p2):
    return math.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)


def velocity(p1, p2):
    dt = (p2["t"] - p1["t"]) / 1000  # ms → sec
    if dt == 0:
        return 0
    return distance(p1, p2) / dt


# =========================
# PREPROCESSING
# =========================

def preprocess_samples(samples):
    processed = []

    for s in samples:
        if s["left_valid"] == 1:
            gaze = s["left_gaze"]
        elif s["right_valid"] == 1:
            gaze = s["right_gaze"]
        else:
            continue

        if gaze is None:
            continue

        processed.append({
            "x": gaze[0],
            "y": gaze[1],
            "t": s["timestamp"]
        })

    return processed


# =========================
# FIXATION DETECTION (I-VT)
# =========================

def detect_fixations(samples, velocity_threshold=0.02, min_duration=100):
    fixations = []
    current = []

    for i in range(1, len(samples)):
        v = velocity(samples[i-1], samples[i])

        if v < velocity_threshold:
            current.append(samples[i])
        else:
            if current:
                duration = current[-1]["t"] - current[0]["t"]
                if duration >= min_duration:
                    fixations.append(current)
                current = []

    return fixations


# =========================
# SACCADES
# =========================

def detect_saccades(samples, fixations):
    fixation_points = set()

    for f in fixations:
        for p in f:
            fixation_points.add(id(p))

    saccades = [p for p in samples if id(p) not in fixation_points]

    return saccades


# =========================
# REGRESSIONS (lettura)
# =========================

def detect_regressions(fixations):
    regressions = 0

    for i in range(1, len(fixations)):
        prev_x = sum(p["x"] for p in fixations[i-1]) / len(fixations[i-1])
        curr_x = sum(p["x"] for p in fixations[i]) / len(fixations[i])

        if curr_x < prev_x:  # movimento indietro
            regressions += 1

    return regressions


# =========================
# METRICHE
# =========================

def compute_eye_metrics(raw_samples):

    samples = preprocess_samples(raw_samples)

    if len(samples) < 10:
        return {}

    fixations = detect_fixations(samples)
    saccades = detect_saccades(samples, fixations)

    fixation_durations = [
        f[-1]["t"] - f[0]["t"] for f in fixations
    ]

    duration_sec = (samples[-1]["t"] - samples[0]["t"]) / 1000

    fixations_total = len(fixations)
    fixations_per_min = (fixations_total / duration_sec) * 60 if duration_sec else 0

    fixation_mean = sum(fixation_durations) / len(fixation_durations) if fixation_durations else 0

    regressions = detect_regressions(fixations)

    return {
        "fixations_total": fixations_total,
        "fixations_per_min": fixations_per_min,
        "fixation_mean_ms": fixation_mean,
        "regressions_total": regressions,
        "saccades_total": len(saccades),
    }
