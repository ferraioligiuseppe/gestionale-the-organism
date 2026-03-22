from __future__ import annotations

import math
from typing import Any, Dict, List


def distance(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    return math.sqrt((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2)


def velocity(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    dt = (p2["t"] - p1["t"]) / 1000.0
    if dt == 0:
        return 0.0
    return distance(p1, p2) / dt


def preprocess_samples(samples: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    processed: List[Dict[str, float]] = []
    for s in samples:
        gaze = None
        if s.get("left_valid") == 1:
            gaze = s.get("left_gaze")
        elif s.get("right_valid") == 1:
            gaze = s.get("right_gaze")
        if not gaze or len(gaze) < 2:
            continue
        processed.append({"x": float(gaze[0]), "y": float(gaze[1]), "t": float(s["timestamp"])})
    return processed


def detect_fixations(samples: List[Dict[str, float]], velocity_threshold: float = 0.02, min_duration: float = 100.0) -> List[List[Dict[str, float]]]:
    fixations: List[List[Dict[str, float]]] = []
    current: List[Dict[str, float]] = []
    for i in range(1, len(samples)):
        v = velocity(samples[i - 1], samples[i])
        if v < velocity_threshold:
            if not current:
                current.append(samples[i - 1])
            current.append(samples[i])
        else:
            if current:
                duration = current[-1]["t"] - current[0]["t"]
                if duration >= min_duration:
                    fixations.append(current)
                current = []
    if current:
        duration = current[-1]["t"] - current[0]["t"]
        if duration >= min_duration:
            fixations.append(current)
    return fixations


def detect_regressions(fixations: List[List[Dict[str, float]]]) -> int:
    regressions = 0
    for i in range(1, len(fixations)):
        prev_x = sum(p["x"] for p in fixations[i - 1]) / len(fixations[i - 1])
        curr_x = sum(p["x"] for p in fixations[i]) / len(fixations[i])
        if curr_x < prev_x:
            regressions += 1
    return regressions


def detect_saccades_count(samples: List[Dict[str, float]], velocity_threshold: float = 0.02) -> int:
    count = 0
    for i in range(1, len(samples)):
        if velocity(samples[i - 1], samples[i]) >= velocity_threshold:
            count += 1
    return count


def compute_eye_metrics(raw_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    samples = preprocess_samples(raw_samples)
    if len(samples) < 10:
        return {
            "samples_total": len(raw_samples),
            "samples_valid": len(samples),
            "duration_sec": 0,
            "fixations_total": 0,
            "fixations_per_min": 0,
            "fixation_mean_ms": 0,
            "fixation_sd_ms": 0,
            "fixation_median_ms": 0,
            "regressions_total": 0,
            "saccades_total": 0,
        }

    fixations = detect_fixations(samples)
    fixation_durations = [f[-1]["t"] - f[0]["t"] for f in fixations]
    duration_sec = max((samples[-1]["t"] - samples[0]["t"]) / 1000.0, 0.001)
    fixations_total = len(fixations)
    fixations_per_min = (fixations_total / duration_sec) * 60.0
    fixation_mean = sum(fixation_durations) / len(fixation_durations) if fixation_durations else 0.0

    if fixation_durations:
        sorted_d = sorted(fixation_durations)
        mid = len(sorted_d) // 2
        fixation_median = (sorted_d[mid - 1] + sorted_d[mid]) / 2.0 if len(sorted_d) % 2 == 0 else sorted_d[mid]
        mean = fixation_mean
        fixation_sd = (sum((d - mean) ** 2 for d in fixation_durations) / len(fixation_durations)) ** 0.5
    else:
        fixation_median = 0.0
        fixation_sd = 0.0

    return {
        "samples_total": len(raw_samples),
        "samples_valid": len(samples),
        "duration_sec": duration_sec,
        "fixations_total": fixations_total,
        "fixations_per_min": fixations_per_min,
        "fixation_mean_ms": fixation_mean,
        "fixation_sd_ms": fixation_sd,
        "fixation_median_ms": fixation_median,
        "regressions_total": detect_regressions(fixations),
        "saccades_total": detect_saccades_count(samples),
    }
