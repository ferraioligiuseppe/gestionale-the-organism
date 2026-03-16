from __future__ import annotations

import pandas as pd


def classify_distance_zone(distance_cm: float | None, target_min: float | None = None, target_max: float | None = None) -> str | None:
    if distance_cm is None:
        return None
    if target_min is None or target_max is None:
        return None
    if distance_cm < target_min:
        return "near"
    if distance_cm > target_max:
        return "far"
    return "mid"


def add_distance_zone_column(df: pd.DataFrame, target_min: float | None = None, target_max: float | None = None) -> pd.DataFrame:
    out = df.copy()
    if "distance_cm_est" not in out.columns:
        return out
    out["distance_zone"] = out["distance_cm_est"].apply(lambda x: classify_distance_zone(x, target_min=target_min, target_max=target_max))
    return out


def compute_distance_metrics(df: pd.DataFrame) -> dict:
    if "distance_cm_est" not in df.columns:
        return {
            "distance_mean_cm": None,
            "distance_min_cm": None,
            "distance_max_cm": None,
            "distance_std_cm": None,
            "time_near_pct": None,
            "time_mid_pct": None,
            "time_far_pct": None,
        }

    work = df[df["distance_cm_est"].notna()].copy()
    if work.empty:
        return {
            "distance_mean_cm": None,
            "distance_min_cm": None,
            "distance_max_cm": None,
            "distance_std_cm": None,
            "time_near_pct": None,
            "time_mid_pct": None,
            "time_far_pct": None,
        }

    out = {
        "distance_mean_cm": round(float(work["distance_cm_est"].mean()), 2),
        "distance_min_cm": round(float(work["distance_cm_est"].min()), 2),
        "distance_max_cm": round(float(work["distance_cm_est"].max()), 2),
        "distance_std_cm": round(float(work["distance_cm_est"].std()), 2) if len(work) > 1 else 0.0,
        "time_near_pct": None,
        "time_mid_pct": None,
        "time_far_pct": None,
    }

    if "distance_zone" in work.columns:
        n = len(work)
        out["time_near_pct"] = round(float((work["distance_zone"] == "near").sum()) / n * 100.0, 2)
        out["time_mid_pct"] = round(float((work["distance_zone"] == "mid").sum()) / n * 100.0, 2)
        out["time_far_pct"] = round(float((work["distance_zone"] == "far").sum()) / n * 100.0, 2)

    return out
