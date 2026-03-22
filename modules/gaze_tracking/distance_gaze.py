from __future__ import annotations

import math
from typing import Any

import pandas as pd


def classify_distance_zone(distance_cm: float | None, near_max: float = 45.0, mid_max: float = 75.0) -> str | None:
    if distance_cm is None or (isinstance(distance_cm, float) and math.isnan(distance_cm)):
        return None
    if distance_cm <= near_max:
        return "near"
    if distance_cm <= mid_max:
        return "mid"
    return "far"


def compute_distance_metrics(
    df: pd.DataFrame,
    distance_col: str = "distance_cm_est",
    near_max: float = 45.0,
    mid_max: float = 75.0,
) -> dict[str, Any]:
    if df.empty or distance_col not in df.columns:
        return {
            "distance_available": False,
            "distance_mean_cm": None,
            "distance_min_cm": None,
            "distance_max_cm": None,
            "distance_std_cm": None,
            "distance_zone_percentages": {},
        }

    series = pd.to_numeric(df[distance_col], errors="coerce").dropna()
    if series.empty:
        return {
            "distance_available": False,
            "distance_mean_cm": None,
            "distance_min_cm": None,
            "distance_max_cm": None,
            "distance_std_cm": None,
            "distance_zone_percentages": {},
        }

    zones = series.apply(lambda x: classify_distance_zone(float(x), near_max=near_max, mid_max=mid_max))
    zone_pct = zones.value_counts(normalize=True).mul(100).round(2).to_dict()

    return {
        "distance_available": True,
        "distance_mean_cm": round(float(series.mean()), 2),
        "distance_min_cm": round(float(series.min()), 2),
        "distance_max_cm": round(float(series.max()), 2),
        "distance_std_cm": round(float(series.std(ddof=0)), 2) if len(series) > 1 else 0.0,
        "distance_zone_percentages": zone_pct,
    }
