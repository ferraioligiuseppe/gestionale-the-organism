from __future__ import annotations

from typing import Any, Dict, List, Optional


def normalize_gaze_samples(raw_samples: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for s in raw_samples:
        gaze = None
        if s.get("left_valid") == 1:
            gaze = s.get("left_gaze")
        elif s.get("right_valid") == 1:
            gaze = s.get("right_gaze")
        if not gaze or len(gaze) < 2:
            continue
        try:
            out.append({
                "x": float(gaze[0]),
                "y": float(gaze[1]),
                "t": float(s["timestamp"]),
            })
        except Exception:
            continue
    return out


def nearest_word(gaze_point: Dict[str, float], words: List[Dict[str, Any]], max_dist: float = 0.08) -> Optional[Dict[str, Any]]:
    gx = gaze_point["x"]
    gy = gaze_point["y"]
    best = None
    best_dist = 9999.0

    for w in words:
        wx = float(w["x_center"])
        wy = float(w["y_center"])
        dx = gx - wx
        dy = gy - wy
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best = w

    if best is None or best_dist > max_dist:
        return None
    return best


def map_gaze_to_words(gaze_points: List[Dict[str, float]], words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mapped: List[Dict[str, Any]] = []
    for g in gaze_points:
        w = nearest_word(g, words)
        mapped.append({
            "t": g["t"],
            "x": g["x"],
            "y": g["y"],
            "word_index": w["index"] if w else None,
            "word": w["word"] if w else None,
            "line": w["line"] if w else None,
        })
    return mapped


def compute_word_metrics(mapped: List[Dict[str, Any]], words: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_index: Dict[int, Dict[str, Any]] = {}
    visited_order: List[int] = []

    for w in words:
        by_index[int(w["index"])] = {
            "word": w["word"],
            "index": int(w["index"]),
            "line": int(w["line"]),
            "hits": 0,
            "dwell_ms": 0.0,
            "first_t": None,
            "last_t": None,
            "revisits": 0,
        }

    prev_idx = None
    seen_once = set()

    for i, m in enumerate(mapped):
        idx = m.get("word_index")
        if idx is None:
            continue

        stat = by_index[idx]
        stat["hits"] += 1
        visited_order.append(idx)

        if stat["first_t"] is None:
            stat["first_t"] = m["t"]
        stat["last_t"] = m["t"]

        if idx in seen_once and prev_idx != idx:
            stat["revisits"] += 1
        seen_once.add(idx)

        if i > 0 and mapped[i - 1].get("word_index") == idx:
            dt = m["t"] - mapped[i - 1]["t"]
            if dt > 0:
                stat["dwell_ms"] += dt

        prev_idx = idx

    regressions = 0
    line_transitions = 0

    for i in range(1, len(visited_order)):
        if visited_order[i] < visited_order[i - 1]:
            regressions += 1

    prev_line = None
    for idx in visited_order:
        line = by_index[idx]["line"]
        if prev_line is not None and line != prev_line:
            line_transitions += 1
        prev_line = line

    skipped_words = sum(1 for _, s in by_index.items() if s["hits"] == 0)
    revisited_words = sum(1 for _, s in by_index.items() if s["revisits"] > 0)
    high_dwell_words = [s for _, s in by_index.items() if s["dwell_ms"] >= 300]

    return {
        "word_stats": list(by_index.values()),
        "regressions_total": regressions,
        "skipped_words_total": skipped_words,
        "revisited_words_total": revisited_words,
        "line_transition_count": line_transitions,
        "words_with_high_dwell": high_dwell_words,
        "reading_path": visited_order,
    }


def compute_advanced_reading_metrics(raw_samples: List[Dict[str, Any]], word_boxes: List[Dict[str, Any]]) -> Dict[str, Any]:
    gaze_points = normalize_gaze_samples(raw_samples)
    mapped = map_gaze_to_words(gaze_points, word_boxes)
    word_metrics = compute_word_metrics(mapped, word_boxes)

    duration_sec = 0.0
    if gaze_points:
        duration_sec = max((gaze_points[-1]["t"] - gaze_points[0]["t"]) / 1000.0, 0.0)

    return {
        "samples_valid": len(gaze_points),
        "duration_sec": duration_sec,
        "mapped_points": mapped,
        **word_metrics,
    }
