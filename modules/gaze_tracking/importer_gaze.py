from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd


INTERNAL_REQUIRED_COLUMNS = ["ts_ms", "gaze_x", "gaze_y"]

GENERIC_COLUMN_ALIASES = {
    "timestamp": "ts_ms",
    "time": "ts_ms",
    "ts": "ts_ms",
    "time_ms": "ts_ms",
    "device_timestamp": "ts_ms",
    "system_timestamp": "ts_ms",
    "recording_timestamp": "ts_ms",
    "timestamp_ms": "ts_ms",
    "x": "gaze_x",
    "y": "gaze_y",
    "gazex": "gaze_x",
    "gazey": "gaze_y",
    "gaze_x": "gaze_x",
    "gaze_y": "gaze_y",
    "gaze_point_x": "gaze_x",
    "gaze_point_y": "gaze_y",
    "gaze_point_on_display_area_x": "gaze_x",
    "gaze_point_on_display_area_y": "gaze_y",
    "confidence": "confidence",
    "conf": "confidence",
    "validity": "confidence",
    "tracking_confidence": "confidence",
    "fixation": "fixation_flag",
    "fixation_flag": "fixation_flag",
    "saccade": "saccade_flag",
    "saccade_flag": "saccade_flag",
    "blink": "blink_flag",
    "blink_flag": "blink_flag",
    "left_x": "eye_left_x",
    "left_y": "eye_left_y",
    "right_x": "eye_right_x",
    "right_y": "eye_right_y",
    "eye_left_x": "eye_left_x",
    "eye_left_y": "eye_left_y",
    "eye_right_x": "eye_right_x",
    "eye_right_y": "eye_right_y",
    "left_gaze_point_x": "eye_left_x",
    "left_gaze_point_y": "eye_left_y",
    "right_gaze_point_x": "eye_right_x",
    "right_gaze_point_y": "eye_right_y",
    "left_gaze_point_on_display_area_x": "eye_left_x",
    "left_gaze_point_on_display_area_y": "eye_left_y",
    "right_gaze_point_on_display_area_x": "eye_right_x",
    "right_gaze_point_on_display_area_y": "eye_right_y",
    "left_pupil_diameter": "pupil_size",
    "right_pupil_diameter": "pupil_size",
    "pupil_size": "pupil_size",
    "pupil": "pupil_size",
    "distance_cm": "distance_cm_est",
    "distance_cm_est": "distance_cm_est",
    "target_x": "target_x",
    "target_y": "target_y",
    "targetlabel": "target_label",
    "target_label": "target_label",
}


def _clean_col(col: Any) -> str:
    s = str(col).strip().lower()
    s = s.replace("\n", " ").replace("\r", " ")
    while "  " in s:
        s = s.replace("  ", " ")
    s = s.replace("-", "_").replace(" ", "_")
    s = s.replace("/", "_").replace("\\", "_")
    return s


def _safe_scalar(value: Any):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _infer_file_format(filename: str | None) -> str:
    if not filename:
        return "unknown"
    return Path(filename).suffix.lower().replace(".", "") or "unknown"


def _normalize_flag(value: Any) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "fixation", "saccade", "blink"}:
            return 1
        if v in {"0", "false", "no", "n", ""}:
            return 0
        try:
            return 1 if float(v) != 0 else 0
        except Exception:
            return 0
    try:
        return 1 if float(value) != 0 else 0
    except Exception:
        return 0


def load_eye_tracker_file(file_obj) -> pd.DataFrame:
    name = getattr(file_obj, "name", "").lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(file_obj)
        except Exception:
            file_obj.seek(0)
            return pd.read_csv(file_obj, sep=";")
    if name.endswith(".xls") or name.endswith(".xlsx"):
        return pd.read_excel(file_obj)
    raise ValueError("Formato non supportato. Usa CSV, XLS o XLSX.")


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        clean = _clean_col(col)
        renamed[col] = GENERIC_COLUMN_ALIASES.get(clean, clean)
    return df.rename(columns=renamed)


def _to_numeric_if_exists(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _ensure_required_internal_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in INTERNAL_REQUIRED_COLUMNS:
        if col not in out.columns:
            out[col] = None
    return out


def _finalize_internal_dataframe(
    df: pd.DataFrame,
    vendor: str,
    filename: str | None = None,
    screen_w_px: int | None = None,
    screen_h_px: int | None = None,
) -> pd.DataFrame:
    out = df.copy()

    numeric_cols = [
        "ts_ms", "gaze_x", "gaze_y", "confidence", "fixation_flag", "saccade_flag", "blink_flag",
        "eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y", "pupil_size", "distance_cm_est",
        "target_x", "target_y",
    ]
    out = _to_numeric_if_exists(out, numeric_cols)

    if "confidence" not in out.columns:
        out["confidence"] = 1.0

    for x_col in ["gaze_x", "eye_left_x", "eye_right_x", "target_x"]:
        if x_col in out.columns and screen_w_px:
            max_x = out[x_col].max(skipna=True)
            if pd.notna(max_x) and max_x is not None and max_x > 1.5:
                out[x_col] = out[x_col] / float(screen_w_px)

    for y_col in ["gaze_y", "eye_left_y", "eye_right_y", "target_y"]:
        if y_col in out.columns and screen_h_px:
            max_y = out[y_col].max(skipna=True)
            if pd.notna(max_y) and max_y is not None and max_y > 1.5:
                out[y_col] = out[y_col] / float(screen_h_px)

    out = _ensure_required_internal_columns(out)

    if "ts_ms" in out.columns:
        out["ts_ms"] = pd.to_numeric(out["ts_ms"], errors="coerce")
        out = out.sort_values("ts_ms").drop_duplicates(subset=["ts_ms"]).reset_index(drop=True)
        out["dt_ms"] = out["ts_ms"].diff().fillna(0)
    else:
        out["dt_ms"] = None

    out["sample_index"] = range(len(out))
    out["source_vendor"] = vendor
    out["source_format"] = _infer_file_format(filename)
    out["source_filename"] = filename

    for flag_col in ["fixation_flag", "saccade_flag", "blink_flag"]:
        if flag_col in out.columns:
            out[flag_col] = out[flag_col].fillna(0).apply(_normalize_flag)

    if "confidence" in out.columns:
        conf_max = out["confidence"].max(skipna=True)
        if pd.notna(conf_max) and conf_max is not None and conf_max > 1.0:
            if conf_max <= 4:
                out["confidence"] = 1.0 - (out["confidence"].clip(lower=0, upper=4) / 4.0)
            elif conf_max <= 100:
                out["confidence"] = out["confidence"].clip(lower=0, upper=100) / 100.0
        out["confidence"] = out["confidence"].clip(lower=0, upper=1)

    base_cols = [
        "ts_ms", "dt_ms", "sample_index", "gaze_x", "gaze_y", "confidence", "fixation_flag",
        "saccade_flag", "blink_flag", "eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y",
        "pupil_size", "distance_cm_est", "distance_zone", "target_x", "target_y", "target_label",
        "source_vendor", "source_format", "source_filename",
    ]
    existing_base = [c for c in base_cols if c in out.columns]
    extra_cols = [c for c in out.columns if c not in existing_base]
    return out[existing_base + extra_cols]


def detect_source_vendor(df: pd.DataFrame, filename: str | None = None) -> str:
    cols = {_clean_col(c) for c in df.columns}
    fname = (filename or "").lower()

    tobii_markers = {
        "left_gaze_point_on_display_area_x", "left_gaze_point_on_display_area_y",
        "right_gaze_point_on_display_area_x", "right_gaze_point_on_display_area_y",
        "gaze_point_on_display_area_x", "gaze_point_on_display_area_y", "left_pupil_diameter",
        "right_pupil_diameter", "device_timestamp", "system_timestamp", "left_gaze_point_validity",
        "right_gaze_point_validity",
    }
    thomson_markers = {
        "fixation_flag", "saccade_flag", "blink_flag", "regression", "fixation_duration",
        "fixation_duration_ms", "eye_left_x", "eye_left_y", "eye_right_x", "eye_right_y",
    }

    tobii_score = len(cols.intersection(tobii_markers))
    thomson_score = len(cols.intersection(thomson_markers))
    if "tobii" in fname:
        tobii_score += 3
    if "thomson" in fname:
        thomson_score += 3
    if tobii_score >= 2 and tobii_score >= thomson_score:
        return "tobii"
    if thomson_score >= 2 and thomson_score > tobii_score:
        return "thomson"
    return "generic"


def normalize_generic_dataframe(df: pd.DataFrame, filename: str | None = None, screen_w_px: int | None = None, screen_h_px: int | None = None) -> Tuple[pd.DataFrame, dict]:
    out = _normalize_column_names(df).copy()
    warnings = []
    for col in INTERNAL_REQUIRED_COLUMNS:
        if col not in out.columns:
            warnings.append(f"Colonna mancante o non riconosciuta: {col}")
    out = _finalize_internal_dataframe(out, vendor="generic", filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    return out, {
        "vendor": "generic",
        "format": _infer_file_format(filename),
        "filename": filename,
        "warnings": warnings,
        "detected_columns": list(out.columns),
    }


def normalize_tobii_dataframe(df: pd.DataFrame, filename: str | None = None, screen_w_px: int | None = None, screen_h_px: int | None = None) -> Tuple[pd.DataFrame, dict]:
    out = df.copy()
    warnings = []
    rename_map = {}
    for col in out.columns:
        c = _clean_col(col)
        if c in {"device_timestamp", "system_timestamp", "recording_timestamp", "timestamp", "time"}:
            if "ts_ms" not in rename_map.values():
                rename_map[col] = "ts_ms"
        elif c in {"gaze_point_on_display_area_x", "gaze_point_x"}:
            rename_map[col] = "gaze_x"
        elif c in {"gaze_point_on_display_area_y", "gaze_point_y"}:
            rename_map[col] = "gaze_y"
        elif c in {"left_gaze_point_on_display_area_x", "left_gaze_point_x"}:
            rename_map[col] = "eye_left_x"
        elif c in {"left_gaze_point_on_display_area_y", "left_gaze_point_y"}:
            rename_map[col] = "eye_left_y"
        elif c in {"right_gaze_point_on_display_area_x", "right_gaze_point_x"}:
            rename_map[col] = "eye_right_x"
        elif c in {"right_gaze_point_on_display_area_y", "right_gaze_point_y"}:
            rename_map[col] = "eye_right_y"
        elif c in {"left_pupil_diameter", "right_pupil_diameter", "pupil_diameter"}:
            rename_map[col] = c
        elif c in {"left_gaze_point_validity", "right_gaze_point_validity", "validity"}:
            rename_map[col] = c
    out = out.rename(columns=rename_map)
    out = _normalize_column_names(out)

    if "ts_ms" in out.columns:
        out["ts_ms"] = pd.to_numeric(out["ts_ms"], errors="coerce")
        ts_max = out["ts_ms"].max(skipna=True)
        if pd.notna(ts_max) and ts_max is not None and ts_max > 1e10:
            out["ts_ms"] = out["ts_ms"] / 1000.0
    else:
        warnings.append("Timestamp Tobii non riconosciuto, provo fallback generico.")

    if "gaze_x" not in out.columns and {"eye_left_x", "eye_right_x"}.issubset(out.columns):
        out["gaze_x"] = out[["eye_left_x", "eye_right_x"]].mean(axis=1)
    if "gaze_y" not in out.columns and {"eye_left_y", "eye_right_y"}.issubset(out.columns):
        out["gaze_y"] = out[["eye_left_y", "eye_right_y"]].mean(axis=1)

    left_pupil_cols = [c for c in out.columns if _clean_col(c) == "left_pupil_diameter"]
    right_pupil_cols = [c for c in out.columns if _clean_col(c) == "right_pupil_diameter"]
    if left_pupil_cols or right_pupil_cols:
        pupil_parts = [pd.to_numeric(out[c], errors="coerce") for c in left_pupil_cols + right_pupil_cols]
        out["pupil_size"] = pd.concat(pupil_parts, axis=1).mean(axis=1)

    validity_cols = [c for c in out.columns if _clean_col(c) in {"left_gaze_point_validity", "right_gaze_point_validity", "validity"}]
    if validity_cols and "confidence" not in out.columns:
        validity_df = pd.concat([pd.to_numeric(out[c], errors="coerce") for c in validity_cols], axis=1)
        validity_mean = validity_df.mean(axis=1)
        out["confidence"] = 1.0 - (validity_mean.clip(lower=0, upper=4) / 4.0)

    out = _finalize_internal_dataframe(out, vendor="tobii", filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    return out, {
        "vendor": "tobii",
        "format": _infer_file_format(filename),
        "filename": filename,
        "warnings": warnings,
        "detected_columns": list(out.columns),
    }


def normalize_thomson_dataframe(df: pd.DataFrame, filename: str | None = None, screen_w_px: int | None = None, screen_h_px: int | None = None) -> Tuple[pd.DataFrame, dict]:
    out = _normalize_column_names(df).copy()
    warnings = []

    if "ts_ms" not in out.columns:
        for fallback in ["timestamp", "time", "ts", "sample", "index"]:
            if fallback in out.columns:
                out["ts_ms"] = pd.to_numeric(out[fallback], errors="coerce")
                break
    if "gaze_x" not in out.columns:
        if {"eye_left_x", "eye_right_x"}.issubset(out.columns):
            out["gaze_x"] = out[["eye_left_x", "eye_right_x"]].mean(axis=1)
        elif "x" in out.columns:
            out["gaze_x"] = pd.to_numeric(out["x"], errors="coerce")
    if "gaze_y" not in out.columns:
        if {"eye_left_y", "eye_right_y"}.issubset(out.columns):
            out["gaze_y"] = out[["eye_left_y", "eye_right_y"]].mean(axis=1)
        elif "y" in out.columns:
            out["gaze_y"] = pd.to_numeric(out["y"], errors="coerce")
    if "confidence" not in out.columns:
        out["confidence"] = 1.0
    if "fixation_flag" not in out.columns:
        for c in ["fixation", "fix_flag"]:
            if c in out.columns:
                out["fixation_flag"] = out[c]
    if "saccade_flag" not in out.columns:
        for c in ["saccade", "sac_flag"]:
            if c in out.columns:
                out["saccade_flag"] = out[c]
    if "blink_flag" not in out.columns:
        for c in ["blink", "blinkflag"]:
            if c in out.columns:
                out["blink_flag"] = out[c]
    if "pupil_size" not in out.columns:
        pupil_candidates = [c for c in out.columns if "pupil" in c]
        if pupil_candidates:
            out["pupil_size"] = pd.concat([pd.to_numeric(out[c], errors="coerce") for c in pupil_candidates], axis=1).mean(axis=1)

    out = _finalize_internal_dataframe(out, vendor="thomson", filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    missing_required = [c for c in INTERNAL_REQUIRED_COLUMNS if c not in out.columns or out[c].isna().all()]
    for col in missing_required:
        warnings.append(f"Colonna critica non trovata o vuota dopo normalizzazione: {col}")
    return out, {
        "vendor": "thomson",
        "format": _infer_file_format(filename),
        "filename": filename,
        "warnings": warnings,
        "detected_columns": list(out.columns),
    }


def import_eye_tracker_dataframe(file_obj=None, df: pd.DataFrame | None = None, filename: str | None = None, screen_w_px: int | None = None, screen_h_px: int | None = None, force_vendor: str | None = None) -> Tuple[pd.DataFrame, dict]:
    if df is None:
        if file_obj is None:
            raise ValueError("Serve file_obj oppure df.")
        raw_df = load_eye_tracker_file(file_obj)
        filename = filename or getattr(file_obj, "name", None)
    else:
        raw_df = df.copy()

    vendor = force_vendor or detect_source_vendor(raw_df, filename=filename)
    if vendor == "tobii":
        normalized_df, meta = normalize_tobii_dataframe(raw_df, filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    elif vendor == "thomson":
        normalized_df, meta = normalize_thomson_dataframe(raw_df, filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)
    else:
        normalized_df, meta = normalize_generic_dataframe(raw_df, filename=filename, screen_w_px=screen_w_px, screen_h_px=screen_h_px)

    meta["rows_total"] = int(len(normalized_df))
    meta["rows_valid_minimal"] = int(normalized_df[["ts_ms", "gaze_x", "gaze_y"]].notna().all(axis=1).sum()) if len(normalized_df) else 0
    return normalized_df, meta


def validate_imported_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    missing = [c for c in INTERNAL_REQUIRED_COLUMNS if c not in df.columns]
    total_rows = len(df)
    valid_min_rows = int(df[["ts_ms", "gaze_x", "gaze_y"]].notna().all(axis=1).sum()) if total_rows else 0
    x_out = int((~df["gaze_x"].between(0, 1, inclusive="both")).fillna(False).sum()) if "gaze_x" in df.columns else 0
    y_out = int((~df["gaze_y"].between(0, 1, inclusive="both")).fillna(False).sum()) if "gaze_y" in df.columns else 0
    return {
        "ok": len(missing) == 0 and total_rows > 0 and valid_min_rows > 0,
        "missing_columns": missing,
        "rows_total": int(total_rows),
        "rows_valid_minimal": valid_min_rows,
        "gaze_x_out_of_range": x_out,
        "gaze_y_out_of_range": y_out,
        "columns_found": list(df.columns),
        "source_vendor": df["source_vendor"].iloc[0] if "source_vendor" in df.columns and len(df) else None,
        "source_format": df["source_format"].iloc[0] if "source_format" in df.columns and len(df) else None,
    }


def dataframe_to_sample_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "ts_ms": _safe_scalar(r.get("ts_ms")),
            "gaze_x": _safe_scalar(r.get("gaze_x")),
            "gaze_y": _safe_scalar(r.get("gaze_y")),
            "confidence": _safe_scalar(r.get("confidence")),
            "tracking_ok": bool(r.get("tracking_ok", False)),
            "distance_cm_est": _safe_scalar(r.get("distance_cm_est")),
            "distance_zone": r.get("distance_zone"),
            "target_x": _safe_scalar(r.get("target_x")),
            "target_y": _safe_scalar(r.get("target_y")),
            "target_label": r.get("target_label"),
        })
    return rows
