from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


DEFAULT_CONFIG: Dict[str, Any] = {
    "min_confidence": 0.60,
    "fix_min_dur_ms": 80,
    "fix_merge_gap_ms": 50,
    "max_dispersion": 0.03,
    "speed_threshold": 0.0008,
    "dbscan_eps_y": 0.025,
    "dbscan_min_samples": 3,
    "short_regression_ratio": 0.05,
    "long_regression_ratio": 0.20,
    "line_return_ratio": 0.25,
    "refix_radius": 0.02,
    "off_text_margin": 0.04,
    "interpolate_small_gaps": True,
    "small_gap_max_ms": 75,
    "max_samples_to_interpolate": 3,
}


def _cfg(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = DEFAULT_CONFIG.copy()
    if config:
        out.update(config)
    return out


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def _euclidean(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def _std(values: List[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return 0.0
    mean_v = sum(values) / len(values)
    var = sum((v - mean_v) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def normalize_gaze_dataframe(
    df: pd.DataFrame,
    screen_w_px: Optional[int] = None,
    screen_h_px: Optional[int] = None,
) -> pd.DataFrame:
    out = df.copy()

    required = ["ts_ms", "gaze_x", "gaze_y"]
    for col in required:
        if col not in out.columns:
            raise ValueError(f"Colonna richiesta mancante: {col}")

    numeric_cols = [
        "ts_ms", "gaze_x", "gaze_y", "confidence",
        "fixation_flag", "saccade_flag", "blink_flag",
        "eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y",
        "pupil_size", "distance_cm_est", "target_x", "target_y"
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "confidence" not in out.columns:
        out["confidence"] = 1.0

    max_x = out["gaze_x"].max(skipna=True)
    max_y = out["gaze_y"].max(skipna=True)

    if max_x is not None and pd.notna(max_x) and max_x > 1.5 and screen_w_px:
        out["gaze_x"] = out["gaze_x"] / float(screen_w_px)

    if max_y is not None and pd.notna(max_y) and max_y > 1.5 and screen_h_px:
        out["gaze_y"] = out["gaze_y"] / float(screen_h_px)

    for eye_col, denom in [
        ("eye_left_x", screen_w_px),
        ("eye_right_x", screen_w_px),
        ("eye_left_y", screen_h_px),
        ("eye_right_y", screen_h_px),
        ("target_x", screen_w_px),
        ("target_y", screen_h_px),
    ]:
        if eye_col in out.columns and denom:
            col_max = out[eye_col].max(skipna=True)
            if col_max is not None and pd.notna(col_max) and col_max > 1.5:
                out[eye_col] = out[eye_col] / float(denom)

    out = out.sort_values("ts_ms").drop_duplicates(subset=["ts_ms"]).reset_index(drop=True)
    out["dt_ms"] = out["ts_ms"].diff().fillna(0)
    out["sample_index"] = range(len(out))

    return out


def clean_gaze_signal(
    df: pd.DataFrame,
    min_confidence: float = 0.60,
    interpolate_small_gaps: bool = True,
    small_gap_max_ms: float = 75,
    max_samples_to_interpolate: int = 3,
) -> pd.DataFrame:
    out = df.copy()

    out["tracking_ok"] = (
        out["ts_ms"].notna()
        & out["gaze_x"].notna()
        & out["gaze_y"].notna()
        & out["gaze_x"].between(0, 1, inclusive="both")
        & out["gaze_y"].between(0, 1, inclusive="both")
        & (out["confidence"].fillna(0) >= min_confidence)
    )

    if "blink_flag" in out.columns:
        out.loc[out["blink_flag"].fillna(0).astype(int) == 1, "tracking_ok"] = False

    out["interpolated"] = False

    if not interpolate_small_gaps:
        return out

    bad_idx = out.index[~out["tracking_ok"]].tolist()
    if not bad_idx:
        return out

    groups: List[List[int]] = []
    current_group: List[int] = []

    for idx in bad_idx:
        if not current_group:
            current_group = [idx]
        elif idx == current_group[-1] + 1:
            current_group.append(idx)
        else:
            groups.append(current_group)
            current_group = [idx]
    if current_group:
        groups.append(current_group)

    for grp in groups:
        if len(grp) > max_samples_to_interpolate:
            continue

        first_idx = grp[0]
        last_idx = grp[-1]
        prev_idx = first_idx - 1
        next_idx = last_idx + 1

        if prev_idx < 0 or next_idx >= len(out):
            continue

        if not bool(out.at[prev_idx, "tracking_ok"]) or not bool(out.at[next_idx, "tracking_ok"]):
            continue

        gap_ms = _safe_float(out.at[next_idx, "ts_ms"]) - _safe_float(out.at[prev_idx, "ts_ms"])
        if gap_ms > small_gap_max_ms:
            continue

        x0 = _safe_float(out.at[prev_idx, "gaze_x"])
        y0 = _safe_float(out.at[prev_idx, "gaze_y"])
        x1 = _safe_float(out.at[next_idx, "gaze_x"])
        y1 = _safe_float(out.at[next_idx, "gaze_y"])

        total_steps = len(grp) + 1
        for i, idx in enumerate(grp, start=1):
            alpha = i / total_steps
            out.at[idx, "gaze_x"] = x0 + (x1 - x0) * alpha
            out.at[idx, "gaze_y"] = y0 + (y1 - y0) * alpha
            out.at[idx, "tracking_ok"] = True
            out.at[idx, "interpolated"] = True

    return out


def detect_fixations_and_saccades(
    df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    cfg = _cfg(config)

    work = df.copy()
    if work.empty:
        return pd.DataFrame(), pd.DataFrame()

    if "tracking_ok" not in work.columns:
        work["tracking_ok"] = True

    work["dx"] = work["gaze_x"].diff().fillna(0.0)
    work["dy"] = work["gaze_y"].diff().fillna(0.0)
    work["dt_seg"] = work["ts_ms"].diff().replace(0, 1).fillna(1)
    work["speed"] = ((work["dx"] ** 2 + work["dy"] ** 2) ** 0.5) / work["dt_seg"]

    has_fix_flag = "fixation_flag" in work.columns
    has_sac_flag = "saccade_flag" in work.columns

    if has_fix_flag:
        work["is_fix_candidate"] = work["fixation_flag"].fillna(0).astype(int) == 1
    else:
        work["is_fix_candidate"] = work["tracking_ok"] & (work["speed"] <= cfg["speed_threshold"])

    if has_sac_flag:
        work["is_saccade_candidate"] = work["saccade_flag"].fillna(0).astype(int) == 1
    else:
        work["is_saccade_candidate"] = work["tracking_ok"] & (work["speed"] > cfg["speed_threshold"])

    work.loc[~work["tracking_ok"], "is_fix_candidate"] = False
    work.loc[~work["tracking_ok"], "is_saccade_candidate"] = False

    fix_df = _build_fixations_from_candidates(work, cfg)
    fix_df = _merge_near_fixations(fix_df, cfg["fix_merge_gap_ms"], cfg["max_dispersion"])
    sac_df = _build_saccades_from_fixations(work, fix_df)

    return fix_df, sac_df


def _build_fixations_from_candidates(work: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    if work.empty:
        return pd.DataFrame()

    tmp = work.copy()
    tmp["fix_grp"] = (tmp["is_fix_candidate"] != tmp["is_fix_candidate"].shift()).cumsum()

    rows: List[Dict[str, Any]] = []

    for _, chunk in tmp.groupby("fix_grp"):
        if not bool(chunk["is_fix_candidate"].iloc[0]):
            continue

        start_ms = _safe_float(chunk["ts_ms"].iloc[0])
        end_ms = _safe_float(chunk["ts_ms"].iloc[-1])
        dur_ms = end_ms - start_ms
        if dur_ms < cfg["fix_min_dur_ms"]:
            continue

        x_vals = chunk["gaze_x"].dropna().tolist()
        y_vals = chunk["gaze_y"].dropna().tolist()
        if not x_vals or not y_vals:
            continue

        x_mean = float(sum(x_vals) / len(x_vals))
        y_mean = float(sum(y_vals) / len(y_vals))
        dispersion_x = max(x_vals) - min(x_vals)
        dispersion_y = max(y_vals) - min(y_vals)
        dispersion = float(dispersion_x + dispersion_y)

        if dispersion > (cfg["max_dispersion"] * 2.5):
            continue

        rows.append({
            "start_ms": start_ms,
            "end_ms": end_ms,
            "dur_ms": dur_ms,
            "x": x_mean,
            "y": y_mean,
            "dispersion": dispersion,
            "n_samples": int(len(chunk)),
            "sample_start_idx": int(chunk.index[0]),
            "sample_end_idx": int(chunk.index[-1]),
            "confidence_mean": float(chunk["confidence"].fillna(0).mean()) if "confidence" in chunk.columns else None,
        })

    fix_df = pd.DataFrame(rows)
    if not fix_df.empty:
        fix_df = fix_df.sort_values("start_ms").reset_index(drop=True)
        fix_df["fix_id"] = range(1, len(fix_df) + 1)
    return fix_df


def _merge_near_fixations(
    fix_df: pd.DataFrame,
    max_gap_ms: float,
    max_spatial_dist: float,
) -> pd.DataFrame:
    if fix_df.empty or len(fix_df) < 2:
        return fix_df.copy()

    merged: List[Dict[str, Any]] = []
    current = fix_df.iloc[0].to_dict()

    for i in range(1, len(fix_df)):
        nxt = fix_df.iloc[i].to_dict()
        gap_ms = _safe_float(nxt["start_ms"]) - _safe_float(current["end_ms"])
        dist = _euclidean(
            _safe_float(current["x"]), _safe_float(current["y"]),
            _safe_float(nxt["x"]), _safe_float(nxt["y"])
        )

        if gap_ms <= max_gap_ms and dist <= max_spatial_dist:
            dur1 = _safe_float(current["dur_ms"])
            dur2 = _safe_float(nxt["dur_ms"])
            total_dur = max(dur1 + dur2, 1.0)

            current["x"] = (_safe_float(current["x"]) * dur1 + _safe_float(nxt["x"]) * dur2) / total_dur
            current["y"] = (_safe_float(current["y"]) * dur1 + _safe_float(nxt["y"]) * dur2) / total_dur
            current["end_ms"] = nxt["end_ms"]
            current["dur_ms"] = _safe_float(current["end_ms"]) - _safe_float(current["start_ms"])
            current["dispersion"] = max(_safe_float(current["dispersion"]), _safe_float(nxt["dispersion"]))
            current["n_samples"] = _safe_int(current.get("n_samples")) + _safe_int(nxt.get("n_samples"))
            current["sample_end_idx"] = _safe_int(nxt.get("sample_end_idx"))
        else:
            merged.append(current)
            current = nxt

    merged.append(current)

    out = pd.DataFrame(merged)
    if not out.empty:
        out = out.sort_values("start_ms").reset_index(drop=True)
        out["fix_id"] = range(1, len(out) + 1)
    return out


def _build_saccades_from_fixations(work: pd.DataFrame, fix_df: pd.DataFrame) -> pd.DataFrame:
    if fix_df.empty or len(fix_df) < 2:
        return pd.DataFrame()

    rows: List[Dict[str, Any]] = []

    for i in range(1, len(fix_df)):
        prev_fix = fix_df.iloc[i - 1]
        curr_fix = fix_df.iloc[i]

        start_ms = _safe_float(prev_fix["end_ms"])
        end_ms = _safe_float(curr_fix["start_ms"])
        dur_ms = max(0.0, end_ms - start_ms)

        x0 = _safe_float(prev_fix["x"])
        y0 = _safe_float(prev_fix["y"])
        x1 = _safe_float(curr_fix["x"])
        y1 = _safe_float(curr_fix["y"])
        amp = _euclidean(x0, y0, x1, y1)

        dx = x1 - x0
        dy = y1 - y0

        direction = _classify_direction(dx, dy)

        rows.append({
            "sac_id": i,
            "from_fix_id": int(prev_fix["fix_id"]),
            "to_fix_id": int(curr_fix["fix_id"]),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "dur_ms": dur_ms,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "dx": dx,
            "dy": dy,
            "amp": amp,
            "direction": direction,
        })

    sac_df = pd.DataFrame(rows)
    if not sac_df.empty:
        sac_df["velocity_proxy"] = sac_df.apply(
            lambda r: (r["amp"] / r["dur_ms"]) if r["dur_ms"] and r["dur_ms"] > 0 else None,
            axis=1
        )
    return sac_df


def _classify_direction(dx: float, dy: float) -> str:
    abs_dx = abs(dx)
    abs_dy = abs(dy)
    if abs_dx >= abs_dy:
        return "right" if dx >= 0 else "left"
    return "down" if dy >= 0 else "up"


def cluster_reading_lines(
    fixations_df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    cfg = _cfg(config)

    if fixations_df.empty:
        return pd.DataFrame(columns=["line_bucket", "line_id", "line_y_center", "n_fixations"])

    work = fixations_df.copy().sort_values("y").reset_index(drop=True)

    eps = float(cfg["dbscan_eps_y"])
    min_samples = int(cfg["dbscan_min_samples"])

    clusters: List[List[float]] = []
    current_cluster: List[float] = []

    for y in work["y"].tolist():
        if not current_cluster:
            current_cluster = [y]
            continue

        cluster_center = sum(current_cluster) / len(current_cluster)
        if abs(y - cluster_center) <= eps:
            current_cluster.append(y)
        else:
            clusters.append(current_cluster)
            current_cluster = [y]

    if current_cluster:
        clusters.append(current_cluster)

    valid_clusters = [c for c in clusters if len(c) >= min_samples]
    if not valid_clusters and clusters:
        valid_clusters = clusters

    rows: List[Dict[str, Any]] = []
    for idx, cluster in enumerate(valid_clusters, start=1):
        center = float(sum(cluster) / len(cluster))
        rows.append({
            "line_bucket": idx,
            "line_id": idx,
            "line_y_center": center,
            "n_fixations": len(cluster),
        })

    lines_df = pd.DataFrame(rows).sort_values("line_y_center").reset_index(drop=True)
    if not lines_df.empty:
        lines_df["line_id"] = range(1, len(lines_df) + 1)
        lines_df["line_bucket"] = lines_df["line_id"]

    return lines_df


def assign_fixations_to_lines(
    fixations_df: pd.DataFrame,
    lines_df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    cfg = _cfg(config)

    if fixations_df.empty:
        return fixations_df.copy()

    out = fixations_df.copy()

    if lines_df.empty:
        out["line_id"] = None
        out["line_y_center"] = None
        out["dist_from_line_center"] = None
        out["off_text"] = True
        return out

    margin = float(cfg["off_text_margin"])

    assigned_line_ids = []
    assigned_centers = []
    dists = []
    off_text_flags = []

    centers = lines_df[["line_id", "line_y_center"]].to_dict("records")

    for _, row in out.iterrows():
        y = _safe_float(row["y"], default=None)  # type: ignore[arg-type]
        if y is None:
            assigned_line_ids.append(None)
            assigned_centers.append(None)
            dists.append(None)
            off_text_flags.append(True)
            continue

        best = min(
            centers,
            key=lambda c: abs(y - _safe_float(c["line_y_center"]))
        )
        dist = abs(y - _safe_float(best["line_y_center"]))

        assigned_line_ids.append(_safe_int(best["line_id"]))
        assigned_centers.append(_safe_float(best["line_y_center"]))
        dists.append(dist)
        off_text_flags.append(dist > margin)

    out["line_id"] = assigned_line_ids
    out["line_y_center"] = assigned_centers
    out["dist_from_line_center"] = dists
    out["off_text"] = off_text_flags

    return out


def classify_reading_transitions(
    fixations_df: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    cfg = _cfg(config)

    if fixations_df.empty or len(fixations_df) < 2:
        return pd.DataFrame()

    ordered = fixations_df.sort_values("start_ms").reset_index(drop=True)

    x_min = _safe_float(ordered["x"].min())
    x_max = _safe_float(ordered["x"].max())
    line_width = max(0.05, x_max - x_min)

    short_thr = max(0.015, line_width * float(cfg["short_regression_ratio"]))
    long_thr = max(0.08, line_width * float(cfg["long_regression_ratio"]))
    line_return_thr = max(0.20, line_width * float(cfg["line_return_ratio"]))
    refix_radius = float(cfg["refix_radius"])

    rows = []

    for i in range(1, len(ordered)):
        prev = ordered.iloc[i - 1]
        curr = ordered.iloc[i]

        prev_line = prev.get("line_id")
        curr_line = curr.get("line_id")

        dx = _safe_float(curr["x"]) - _safe_float(prev["x"])
        dy = _safe_float(curr["y"]) - _safe_float(prev["y"])
        dist = _euclidean(_safe_float(prev["x"]), _safe_float(prev["y"]), _safe_float(curr["x"]), _safe_float(curr["y"]))

        same_line = pd.notna(prev_line) and pd.notna(curr_line) and (int(prev_line) == int(curr_line))
        kind = "progression"

        if bool(curr.get("off_text", False)) or bool(prev.get("off_text", False)):
            kind = "off_text_transition"
        elif same_line:
            if dist <= refix_radius:
                kind = "refixation"
            elif dx < -long_thr:
                kind = "long_regression"
            elif dx < -short_thr:
                kind = "short_regression"
            elif abs(dy) > abs(dx) and abs(dy) > 0.02:
                kind = "vertical_search"
            else:
                kind = "progression"
        else:
            if pd.notna(prev_line) and pd.notna(curr_line):
                prev_line_i = int(prev_line)
                curr_line_i = int(curr_line)

                if curr_line_i == prev_line_i + 1 and dx < -line_return_thr:
                    kind = "line_return"
                elif curr_line_i < prev_line_i:
                    kind = "interline_regression"
                elif abs(curr_line_i - prev_line_i) > 1:
                    kind = "line_loss"
                elif abs(dy) > 0.02 and abs(dx) < 0.04:
                    kind = "vertical_search"
                else:
                    kind = "interline_progression"
            else:
                kind = "unclassified"

        rows.append({
            "transition_id": i,
            "from_fix_id": _safe_int(prev["fix_id"]),
            "to_fix_id": _safe_int(curr["fix_id"]),
            "from_line_id": _safe_int(prev_line, default=0) if pd.notna(prev_line) else None,
            "to_line_id": _safe_int(curr_line, default=0) if pd.notna(curr_line) else None,
            "dx": dx,
            "dy": dy,
            "dist": dist,
            "kind": kind,
            "same_line": bool(same_line),
            "start_ms": _safe_float(prev["end_ms"]),
            "end_ms": _safe_float(curr["start_ms"]),
            "dur_ms": max(0.0, _safe_float(curr["start_ms"]) - _safe_float(prev["end_ms"])),
        })

    return pd.DataFrame(rows)


def compute_quality_metrics(raw_df: pd.DataFrame) -> Dict[str, Any]:
    total = int(len(raw_df))
    if total == 0:
        return {
            "rows_total": 0,
            "valid_sample_pct": 0.0,
            "tracking_loss_pct": 100.0,
            "confidence_mean": 0.0,
            "interpolated_pct": 0.0,
            "blink_count": 0,
        }

    valid = int(raw_df["tracking_ok"].sum()) if "tracking_ok" in raw_df.columns else 0
    confidence_mean = float(raw_df["confidence"].fillna(0).mean()) if "confidence" in raw_df.columns else 0.0
    interpolated_pct = float(raw_df["interpolated"].mean() * 100) if "interpolated" in raw_df.columns else 0.0
    blink_count = int(raw_df["blink_flag"].fillna(0).astype(int).sum()) if "blink_flag" in raw_df.columns else 0

    valid_pct = (valid / total) * 100.0
    tracking_loss_pct = 100.0 - valid_pct

    return {
        "rows_total": total,
        "valid_sample_pct": round(valid_pct, 2),
        "tracking_loss_pct": round(tracking_loss_pct, 2),
        "confidence_mean": round(confidence_mean, 4),
        "interpolated_pct": round(interpolated_pct, 2),
        "blink_count": blink_count,
    }


def compute_reading_metrics(
    fixations_df: pd.DataFrame,
    transitions_df: pd.DataFrame,
    samples_df: Optional[pd.DataFrame] = None,
    words_count: Optional[int] = None,
) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}

    if fixations_df.empty:
        metrics.update({
            "fixation_count": 0,
            "fixation_total_ms": 0.0,
            "mean_fixation_ms": 0.0,
            "median_fixation_ms": 0.0,
            "std_fixation_ms": 0.0,
            "line_count_detected": 0,
            "fixations_per_line": 0.0,
            "regression_total": 0,
            "short_regression_count": 0,
            "long_regression_count": 0,
            "interline_regression_count": 0,
            "line_returns": 0,
            "line_losses": 0,
            "refixation_count": 0,
            "regressions_per_line": 0.0,
            "regressions_fixation_ratio": 0.0,
            "refixation_pct": 0.0,
            "words_per_min": None,
            "reading_time_ms": 0.0,
        })
        if samples_df is not None:
            metrics.update(compute_quality_metrics(samples_df))
        return metrics

    dur_list = fixations_df["dur_ms"].dropna().tolist()

    fixation_count = int(len(fixations_df))
    fixation_total_ms = float(sum(dur_list))
    mean_fixation_ms = float(sum(dur_list) / len(dur_list)) if dur_list else 0.0
    median_fixation_ms = float(_median(dur_list))
    std_fixation_ms = float(_std(dur_list))

    metrics.update({
        "fixation_count": fixation_count,
        "fixation_total_ms": round(fixation_total_ms, 2),
        "mean_fixation_ms": round(mean_fixation_ms, 2),
        "median_fixation_ms": round(median_fixation_ms, 2),
        "std_fixation_ms": round(std_fixation_ms, 2),
    })

    n_lines = int(fixations_df["line_id"].nunique()) if "line_id" in fixations_df.columns else 0
    metrics["line_count_detected"] = n_lines
    metrics["fixations_per_line"] = round(fixation_count / max(n_lines, 1), 2) if n_lines else 0.0

    if transitions_df.empty:
        regression_total = 0
        short_reg = 0
        long_reg = 0
        interline_reg = 0
        line_returns = 0
        line_losses = 0
        refix_count = 0
        vertical_search_count = 0
        off_text_transition_count = 0
    else:
        kind_series = transitions_df["kind"].fillna("")

        short_reg = int((kind_series == "short_regression").sum())
        long_reg = int((kind_series == "long_regression").sum())
        interline_reg = int((kind_series == "interline_regression").sum())
        regression_total = short_reg + long_reg + interline_reg
        line_returns = int((kind_series == "line_return").sum())
        line_losses = int((kind_series == "line_loss").sum())
        refix_count = int((kind_series == "refixation").sum())
        vertical_search_count = int((kind_series == "vertical_search").sum())
        off_text_transition_count = int((kind_series == "off_text_transition").sum())

    metrics.update({
        "regression_total": regression_total,
        "short_regression_count": short_reg,
        "long_regression_count": long_reg,
        "interline_regression_count": interline_reg,
        "line_returns": line_returns,
        "line_losses": line_losses,
        "refixation_count": refix_count,
        "vertical_search_count": vertical_search_count,
        "off_text_transition_count": off_text_transition_count,
        "regressions_per_line": round(regression_total / max(n_lines, 1), 2) if n_lines else 0.0,
        "regressions_fixation_ratio": round(regression_total / max(fixation_count, 1), 4),
        "refixation_pct": round((refix_count / max(fixation_count, 1)) * 100.0, 2),
    })

    if "off_text" in fixations_df.columns:
        off_text_fix_count = int(fixations_df["off_text"].fillna(False).astype(bool).sum())
    else:
        off_text_fix_count = 0

    metrics["off_text_fixation_count"] = off_text_fix_count
    metrics["off_text_fixation_pct"] = round((off_text_fix_count / max(fixation_count, 1)) * 100.0, 2)

    reading_time_ms = max(0.0, _safe_float(fixations_df["end_ms"].max()) - _safe_float(fixations_df["start_ms"].min()))
    metrics["reading_time_ms"] = round(reading_time_ms, 2)

    if words_count and reading_time_ms > 0:
        minutes = reading_time_ms / 60000.0
        metrics["words_per_min"] = round(words_count / minutes, 2)
    else:
        metrics["words_per_min"] = None

    if samples_df is not None:
        metrics.update(compute_quality_metrics(samples_df))

    return metrics


def compute_saccade_metrics(saccades_df: pd.DataFrame) -> Dict[str, Any]:
    if saccades_df.empty:
        return {
            "saccade_count": 0,
            "mean_saccade_amp": 0.0,
            "median_saccade_amp": 0.0,
            "std_saccade_amp": 0.0,
            "mean_saccade_duration_ms": 0.0,
            "progressive_saccades": 0,
            "regressive_saccades": 0,
            "vertical_saccades": 0,
        }

    amps = saccades_df["amp"].dropna().tolist()
    durs = saccades_df["dur_ms"].dropna().tolist()
    dirs = saccades_df["direction"].fillna("")

    return {
        "saccade_count": int(len(saccades_df)),
        "mean_saccade_amp": round(float(sum(amps) / len(amps)) if amps else 0.0, 4),
        "median_saccade_amp": round(float(_median(amps)), 4),
        "std_saccade_amp": round(float(_std(amps)), 4),
        "mean_saccade_duration_ms": round(float(sum(durs) / len(durs)) if durs else 0.0, 2),
        "progressive_saccades": int((dirs == "right").sum()),
        "regressive_saccades": int((dirs == "left").sum()),
        "vertical_saccades": int(((dirs == "up") | (dirs == "down")).sum()),
    }


def compute_binocular_metrics(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    required = ["eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y"]
    if any(col not in df.columns for col in required):
        return {
            "binocular_available": False,
            "disparity_mean": None,
            "disparity_std": None,
            "horizontal_disparity_mean": None,
            "vertical_disparity_mean": None,
            "drift_score": None,
            "suspect_misalignment": None,
        }

    work = df.copy()
    if "tracking_ok" in work.columns:
        work = work[work["tracking_ok"]].copy()

    for col in required:
        work = work[work[col].notna()]

    if work.empty:
        return {
            "binocular_available": False,
            "disparity_mean": None,
            "disparity_std": None,
            "horizontal_disparity_mean": None,
            "vertical_disparity_mean": None,
            "drift_score": None,
            "suspect_misalignment": None,
        }

    work["dx_eyes"] = work["eye_right_x"] - work["eye_left_x"]
    work["dy_eyes"] = work["eye_right_y"] - work["eye_left_y"]
    work["disparity"] = ((work["dx_eyes"] ** 2) + (work["dy_eyes"] ** 2)) ** 0.5

    disparity_vals = work["disparity"].dropna().tolist()
    dx_vals = work["dx_eyes"].dropna().tolist()
    dy_vals = work["dy_eyes"].dropna().tolist()

    disparity_mean = float(sum(disparity_vals) / len(disparity_vals)) if disparity_vals else 0.0
    disparity_std = float(_std(disparity_vals))
    horizontal_disparity_mean = float(sum(dx_vals) / len(dx_vals)) if dx_vals else 0.0
    vertical_disparity_mean = float(sum(dy_vals) / len(dy_vals)) if dy_vals else 0.0

    n = len(work)
    window = max(3, n // 5)
    first = work.head(window)
    last = work.tail(window)
    drift_dx = abs(_safe_float(last["dx_eyes"].mean()) - _safe_float(first["dx_eyes"].mean()))
    drift_dy = abs(_safe_float(last["dy_eyes"].mean()) - _safe_float(first["dy_eyes"].mean()))
    drift_score = math.sqrt(drift_dx ** 2 + drift_dy ** 2)

    suspect_misalignment = (
        disparity_mean > 0.03
        or disparity_std > 0.02
        or abs(horizontal_disparity_mean) > 0.025
        or abs(vertical_disparity_mean) > 0.02
    )

    return {
        "binocular_available": True,
        "disparity_mean": round(disparity_mean, 4),
        "disparity_std": round(disparity_std, 4),
        "horizontal_disparity_mean": round(horizontal_disparity_mean, 4),
        "vertical_disparity_mean": round(vertical_disparity_mean, 4),
        "drift_score": round(drift_score, 4),
        "suspect_misalignment": bool(suspect_misalignment),
    }


def compute_clinical_indexes(metrics: Dict[str, Any]) -> Dict[str, Any]:
    tracking_loss_pct = _safe_float(metrics.get("tracking_loss_pct"), 0.0)
    line_losses = _safe_float(metrics.get("line_losses"), 0.0)
    off_text_fix_pct = _safe_float(metrics.get("off_text_fixation_pct"), 0.0)
    regressions_fix_ratio = _safe_float(metrics.get("regressions_fixation_ratio"), 0.0)
    mean_fix = _safe_float(metrics.get("mean_fixation_ms"), 0.0)
    long_reg = _safe_float(metrics.get("long_regression_count"), 0.0)
    refix_pct = _safe_float(metrics.get("refixation_pct"), 0.0)
    drift_score = _safe_float(metrics.get("drift_score"), 0.0)

    attention_instability_index = min(100.0, (tracking_loss_pct * 0.7 + line_losses * 10.0 + off_text_fix_pct * 0.5 + regressions_fix_ratio * 100.0 * 0.35))
    fatigue_index = min(100.0, (max(0.0, mean_fix - 180.0) * 0.18 + long_reg * 2.8 + drift_score * 300.0))
    dyslexia_oculomotor_risk = min(100.0, (regressions_fix_ratio * 100.0 * 0.8 + line_losses * 12.0 + max(0.0, mean_fix - 200.0) * 0.12 + refix_pct * 0.35 + off_text_fix_pct * 0.20))

    if dyslexia_oculomotor_risk < 30:
        risk_class = "low"
    elif dyslexia_oculomotor_risk < 60:
        risk_class = "moderate"
    else:
        risk_class = "moderate_high"

    return {
        "attention_instability_index": round(attention_instability_index, 2),
        "fatigue_index": round(fatigue_index, 2),
        "dyslexia_oculomotor_risk": round(dyslexia_oculomotor_risk, 2),
        "risk_class": risk_class,
    }


def build_summary_json(metrics: Dict[str, Any], indexes: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "quality": {
            "rows_total": metrics.get("rows_total"),
            "valid_sample_pct": metrics.get("valid_sample_pct"),
            "tracking_loss_pct": metrics.get("tracking_loss_pct"),
            "confidence_mean": metrics.get("confidence_mean"),
            "interpolated_pct": metrics.get("interpolated_pct"),
            "blink_count": metrics.get("blink_count"),
        },
        "reading": {
            "fixation_count": metrics.get("fixation_count"),
            "fixation_total_ms": metrics.get("fixation_total_ms"),
            "mean_fixation_ms": metrics.get("mean_fixation_ms"),
            "median_fixation_ms": metrics.get("median_fixation_ms"),
            "std_fixation_ms": metrics.get("std_fixation_ms"),
            "line_count_detected": metrics.get("line_count_detected"),
            "fixations_per_line": metrics.get("fixations_per_line"),
            "regression_total": metrics.get("regression_total"),
            "short_regression_count": metrics.get("short_regression_count"),
            "long_regression_count": metrics.get("long_regression_count"),
            "interline_regression_count": metrics.get("interline_regression_count"),
            "line_returns": metrics.get("line_returns"),
            "line_losses": metrics.get("line_losses"),
            "refixation_count": metrics.get("refixation_count"),
            "refixation_pct": metrics.get("refixation_pct"),
            "vertical_search_count": metrics.get("vertical_search_count"),
            "off_text_fixation_count": metrics.get("off_text_fixation_count"),
            "off_text_fixation_pct": metrics.get("off_text_fixation_pct"),
            "regressions_per_line": metrics.get("regressions_per_line"),
            "regressions_fixation_ratio": metrics.get("regressions_fixation_ratio"),
            "reading_time_ms": metrics.get("reading_time_ms"),
            "words_per_min": metrics.get("words_per_min"),
        },
        "saccades": {
            "saccade_count": metrics.get("saccade_count"),
            "mean_saccade_amp": metrics.get("mean_saccade_amp"),
            "median_saccade_amp": metrics.get("median_saccade_amp"),
            "std_saccade_amp": metrics.get("std_saccade_amp"),
            "mean_saccade_duration_ms": metrics.get("mean_saccade_duration_ms"),
            "progressive_saccades": metrics.get("progressive_saccades"),
            "regressive_saccades": metrics.get("regressive_saccades"),
            "vertical_saccades": metrics.get("vertical_saccades"),
        },
        "binocular": {
            "binocular_available": metrics.get("binocular_available"),
            "disparity_mean": metrics.get("disparity_mean"),
            "disparity_std": metrics.get("disparity_std"),
            "horizontal_disparity_mean": metrics.get("horizontal_disparity_mean"),
            "vertical_disparity_mean": metrics.get("vertical_disparity_mean"),
            "drift_score": metrics.get("drift_score"),
            "suspect_misalignment": metrics.get("suspect_misalignment"),
        },
        "indexes": indexes,
    }


def run_reading_analysis(
    df_samples: pd.DataFrame,
    config: Optional[Dict[str, Any]] = None,
    words_count: Optional[int] = None,
    screen_w_px: Optional[int] = None,
    screen_h_px: Optional[int] = None,
) -> Dict[str, Any]:
    cfg = _cfg(config)

    df = normalize_gaze_dataframe(df_samples, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    df = clean_gaze_signal(
        df,
        min_confidence=cfg["min_confidence"],
        interpolate_small_gaps=cfg["interpolate_small_gaps"],
        small_gap_max_ms=cfg["small_gap_max_ms"],
        max_samples_to_interpolate=cfg["max_samples_to_interpolate"],
    )

    fix_df, sac_df = detect_fixations_and_saccades(df, config=cfg)
    lines_df = cluster_reading_lines(fix_df, config=cfg)
    fix_df = assign_fixations_to_lines(fix_df, lines_df, config=cfg)
    trans_df = classify_reading_transitions(fix_df, config=cfg)

    reading_metrics = compute_reading_metrics(fixations_df=fix_df, transitions_df=trans_df, samples_df=df, words_count=words_count)
    saccade_metrics = compute_saccade_metrics(sac_df)
    binocular_metrics = compute_binocular_metrics(df, config=cfg)

    metrics: Dict[str, Any] = {}
    metrics.update(reading_metrics)
    metrics.update(saccade_metrics)
    metrics.update(binocular_metrics)

    indexes = compute_clinical_indexes(metrics)
    summary = build_summary_json(metrics, indexes)

    return {
        "samples": df,
        "fixations": fix_df,
        "saccades": sac_df,
        "lines": lines_df,
        "transitions": trans_df,
        "metrics": metrics,
        "indexes": indexes,
        "summary": summary,
    }
