from __future__ import annotations

from typing import Any

import pandas as pd

from .distance_gaze import compute_distance_metrics
from .protocols_gaze import get_protocol_config


def clean_gaze_signal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["gaze_x"] = pd.to_numeric(out["gaze_x"], errors="coerce")
    out["gaze_y"] = pd.to_numeric(out["gaze_y"], errors="coerce")
    out["confidence"] = pd.to_numeric(out["confidence"], errors="coerce").fillna(1.0)
    out = out.sort_values("ts_ms").reset_index(drop=True)

    out["dt_ms"] = out["ts_ms"].diff().fillna(0)
    out["dx"] = out["gaze_x"].diff().fillna(0)
    out["dy"] = out["gaze_y"].diff().fillna(0)
    out["distance_px"] = (out["dx"] ** 2 + out["dy"] ** 2) ** 0.5
    out["velocity_px_per_ms"] = out["distance_px"] / out["dt_ms"].replace(0, pd.NA)
    out["velocity_px_per_ms"] = out["velocity_px_per_ms"].fillna(0)

    return out


def detect_fixations_and_saccades(df: pd.DataFrame, fixation_velocity_threshold: float = 0.5) -> pd.DataFrame:
    out = df.copy()
    out["derived_fixation_flag"] = out["velocity_px_per_ms"] <= fixation_velocity_threshold
    out["derived_saccade_flag"] = out["velocity_px_per_ms"] > fixation_velocity_threshold
    return out


def cluster_reading_lines(df: pd.DataFrame, tolerance_px: float = 40.0) -> pd.DataFrame:
    out = df.copy()
    line_ids = []
    current_line = 0
    last_y = None

    for _, row in out.iterrows():
        y = row.get("gaze_y")
        if pd.isna(y):
            line_ids.append(None)
            continue

        if last_y is None:
            current_line = 0
        elif abs(float(y) - float(last_y)) > tolerance_px:
            current_line += 1

        line_ids.append(current_line)
        last_y = y

    out["reading_line_id"] = line_ids
    return out


def assign_fixations_to_lines(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["fixation_line_id"] = out["reading_line_id"].where(out["derived_fixation_flag"], None)
    return out


def classify_reading_transitions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["prev_x"] = out["gaze_x"].shift(1)
    out["prev_line"] = out["reading_line_id"].shift(1)

    out["is_regression"] = (out["gaze_x"] < out["prev_x"]) & (out["reading_line_id"] == out["prev_line"])
    out["is_line_return"] = (out["reading_line_id"] > out["prev_line"].fillna(out["reading_line_id"])) & (
        out["gaze_x"] < out["prev_x"].fillna(out["gaze_x"])
    )
    out["is_line_loss"] = (out["reading_line_id"] > out["prev_line"].fillna(out["reading_line_id"]) + 1)

    out["is_regression"] = out["is_regression"].fillna(False)
    out["is_line_return"] = out["is_line_return"].fillna(False)
    out["is_line_loss"] = out["is_line_loss"].fillna(False)
    return out


def compute_reading_metrics(df: pd.DataFrame) -> dict[str, Any]:
    fixation_count = int(df["derived_fixation_flag"].sum()) if "derived_fixation_flag" in df.columns else 0
    regression_count = int(df["is_regression"].sum()) if "is_regression" in df.columns else 0
    line_returns = int(df["is_line_return"].sum()) if "is_line_return" in df.columns else 0
    line_losses = int(df["is_line_loss"].sum()) if "is_line_loss" in df.columns else 0

    mean_fixation_ms = None
    if "dt_ms" in df.columns and fixation_count > 0:
        mean_fixation_ms = round(float(df.loc[df["derived_fixation_flag"], "dt_ms"].mean()), 2)

    lines = df["reading_line_id"].dropna()
    unique_lines = int(lines.nunique()) if not lines.empty else 0

    regressions_per_line = round(regression_count / unique_lines, 2) if unique_lines > 0 else 0.0

    return {
        "fixation_count": fixation_count,
        "mean_fixation_ms": mean_fixation_ms,
        "regressions": regression_count,
        "regressions_per_line": regressions_per_line,
        "line_returns": line_returns,
        "line_losses": line_losses,
        "reading_line_count": unique_lines,
    }


def compute_saccade_metrics(df: pd.DataFrame) -> dict[str, Any]:
    saccade_count = int(df["derived_saccade_flag"].sum()) if "derived_saccade_flag" in df.columns else 0
    mean_velocity = None

    if "velocity_px_per_ms" in df.columns and saccade_count > 0:
        mean_velocity = round(float(df.loc[df["derived_saccade_flag"], "velocity_px_per_ms"].mean()), 4)

    return {
        "saccade_count": saccade_count,
        "mean_saccade_velocity_px_ms": mean_velocity,
    }


def compute_binocular_metrics(df: pd.DataFrame) -> dict[str, Any]:
    available = {"eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y"}.issubset(df.columns)
    if not available:
        return {
            "binocular_available": False,
            "binocular_mean_disparity_px": None,
        }

    tmp = df.copy()
    tmp["binocular_disparity_px"] = (
        (pd.to_numeric(tmp["eye_left_x"], errors="coerce") - pd.to_numeric(tmp["eye_right_x"], errors="coerce")) ** 2
        + (pd.to_numeric(tmp["eye_left_y"], errors="coerce") - pd.to_numeric(tmp["eye_right_y"], errors="coerce")) ** 2
    ) ** 0.5

    disparity = tmp["binocular_disparity_px"].dropna()
    return {
        "binocular_available": not disparity.empty,
        "binocular_mean_disparity_px": round(float(disparity.mean()), 4) if not disparity.empty else None,
    }


def compute_clinical_indexes(metrics: dict[str, Any]) -> dict[str, Any]:
    fixation_count = metrics.get("fixation_count", 0) or 0
    regressions = metrics.get("regressions", 0) or 0
    line_losses = metrics.get("line_losses", 0) or 0
    mean_fix_ms = metrics.get("mean_fixation_ms") or 0
    saccade_count = metrics.get("saccade_count", 0) or 0

    attention_instability_index = round((regressions * 1.5) + (line_losses * 3.0), 2)
    fatigue_index = round((mean_fix_ms / 100.0) + (fixation_count / 500.0), 2)
    dyslexia_oculomotor_risk = round(
        (regressions * 0.4) + (line_losses * 1.2) + (saccade_count / 100.0),
        2,
    )

    return {
        "attention_instability_index": attention_instability_index,
        "fatigue_index": fatigue_index,
        "dyslexia_oculomotor_risk": dyslexia_oculomotor_risk,
    }


def build_summary_json(
    metadata: dict[str, Any],
    protocol_name: str,
    metrics: dict[str, Any],
    clinical_indexes: dict[str, Any],
    distance_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_version": "0.1.0",
        "analytics_version": "0.1.0",
        "protocol_name": protocol_name,
        "source_vendor": metadata.get("source_vendor"),
        "source_filename": metadata.get("source_filename"),
        "row_count": metadata.get("row_count"),
        "metrics": metrics,
        "clinical_indexes": clinical_indexes,
        "distance_metrics": distance_metrics,
    }


def run_gaze_analytics(
    df: pd.DataFrame,
    protocol_name: str = "reading_standard",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    protocol = get_protocol_config(protocol_name)

    cleaned = clean_gaze_signal(df)
    detected = detect_fixations_and_saccades(cleaned)
    lined = cluster_reading_lines(detected, tolerance_px=protocol["line_cluster_tolerance_px"])
    assigned = assign_fixations_to_lines(lined)
    classified = classify_reading_transitions(assigned)

    reading_metrics = compute_reading_metrics(classified)
    saccade_metrics = compute_saccade_metrics(classified)
    binocular_metrics = compute_binocular_metrics(classified)
    distance_metrics = compute_distance_metrics(
        classified,
        near_max=protocol["distance_zones_cm"]["near_max"],
        mid_max=protocol["distance_zones_cm"]["mid_max"],
    )

    merged_metrics = {
        **reading_metrics,
        **saccade_metrics,
        **binocular_metrics,
    }
    clinical_indexes = compute_clinical_indexes(merged_metrics)
    summary_json = build_summary_json(
        metadata=metadata,
        protocol_name=protocol_name,
        metrics=merged_metrics,
        clinical_indexes=clinical_indexes,
        distance_metrics=distance_metrics,
    )

    return {
        "samples_enriched": classified,
        "metrics": merged_metrics,
        "clinical_indexes": clinical_indexes,
        "distance_metrics": distance_metrics,
        "summary_json": summary_json,
        "warnings": [],
    }
