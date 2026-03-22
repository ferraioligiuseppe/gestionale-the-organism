from __future__ import annotations

from typing import Any, Dict, List


def build_heatmap_points(mapped_points: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    points: List[Dict[str, float]] = []
    for p in mapped_points:
        try:
            if p.get("x") is None or p.get("y") is None:
                continue
            points.append({
                "x": float(p["x"]),
                "y": float(p["y"]),
                "value": 1.0,
            })
        except Exception:
            continue
    return points


def build_word_highlight_map(word_stats: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for w in word_stats:
        try:
            idx = int(w["index"])
            out[idx] = {
                "hits": int(w.get("hits", 0) or 0),
                "dwell_ms": float(w.get("dwell_ms", 0) or 0),
                "revisits": int(w.get("revisits", 0) or 0),
            }
        except Exception:
            continue
    return out
