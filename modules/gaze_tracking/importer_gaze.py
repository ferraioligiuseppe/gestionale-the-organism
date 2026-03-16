from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


INTERNAL_REQUIRED_COLUMNS = ["ts_ms", "gaze_x", "gaze_y"]

OPTIONAL_COLUMNS = [
    "confidence",
    "fixation_flag",
    "saccade_flag",
    "blink_flag",
    "eye_left_x",
    "eye_left_y",
    "eye_right_x",
    "eye_right_y",
    "pupil_size",
    "distance_cm_est",
    "distance_zone",
    "target_x",
    "target_y",
    "target_label",
]

COLUMN_ALIASES = {
    "timestamp": "ts_ms",
    "time": "ts_ms",
    "ts": "ts_ms",
    "time_ms": "ts_ms",
    "gaze_timestamp": "ts_ms",
    "x": "gaze_x",
    "y": "gaze_y",
    "gaze_x": "gaze_x",
    "gaze_y": "gaze_y",
    "gazex": "gaze_x",
    "gazey": "gaze_y",
    "conf": "confidence",
    "confidence_score": "confidence",
    "fixation": "fixation_flag",
    "fixationflag": "fixation_flag",
    "saccade": "saccade_flag",
    "saccadeflag": "saccade_flag",
    "blink": "blink_flag",
    "blinkflag": "blink_flag",
    "left_x": "eye_left_x",
    "left_y": "eye_left_y",
    "right_x": "eye_right_x",
    "right_y": "eye_right_y",
    "eye_leftx": "eye_left_x",
    "eye_lefty": "eye_left_y",
    "eye_rightx": "eye_right_x",
    "eye_righty": "eye_right_y",
    "targetx": "target_x",
    "targety": "target_y",
}


def load_eye_tracker_file(file_obj) -> pd.DataFrame:
    """Legge CSV/XLS/XLSX e restituisce DataFrame grezzo."""
    name = getattr(file_obj, "name", "").lower()

    if name.endswith(".csv"):
        return pd.read_csv(file_obj)

    if name.endswith(".xls") or name.endswith(".xlsx"):
        return pd.read_excel(file_obj)

    raise ValueError("Formato non supportato. Usa CSV, XLS o XLSX.")


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        clean = str(col).strip().lower().replace("\n", " ").replace("  ", " ")
        clean = clean.replace("-", "_").replace(" ", "_")
        renamed[col] = COLUMN_ALIASES.get(clean, clean)
    return df.rename(columns=renamed)


def normalize_imported_dataframe(
    df: pd.DataFrame,
    screen_w_px: Optional[int] = None,
    screen_h_px: Optional[int] = None,
) -> pd.DataFrame:
    """
    Standardizza:
    - nomi colonne
    - tipi numerici
    - ordinamento temporale
    - coordinate normalizzate 0..1 se possibile
    """
    out = normalize_column_names(df).copy()

    for col in INTERNAL_REQUIRED_COLUMNS:
        if col not in out.columns:
            raise ValueError(f"Colonna richiesta mancante: {col}")

    numeric_cols = [
        "ts_ms",
        "gaze_x",
        "gaze_y",
        "confidence",
        "fixation_flag",
        "saccade_flag",
        "blink_flag",
        "eye_left_x",
        "eye_left_y",
        "eye_right_x",
        "eye_right_y",
        "pupil_size",
        "distance_cm_est",
        "target_x",
        "target_y",
    ]

    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "confidence" not in out.columns:
        out["confidence"] = 1.0

    if screen_w_px and out["gaze_x"].max(skipna=True) > 1.5:
        out["gaze_x"] = out["gaze_x"] / float(screen_w_px)

    if screen_h_px and out["gaze_y"].max(skipna=True) > 1.5:
        out["gaze_y"] = out["gaze_y"] / float(screen_h_px)

    eye_x_cols = ["eye_left_x", "eye_right_x", "target_x"]
    eye_y_cols = ["eye_left_y", "eye_right_y", "target_y"]

    for col in eye_x_cols:
        if col in out.columns and screen_w_px and out[col].max(skipna=True) > 1.5:
            out[col] = out[col] / float(screen_w_px)

    for col in eye_y_cols:
        if col in out.columns and screen_h_px and out[col].max(skipna=True) > 1.5:
            out[col] = out[col] / float(screen_h_px)

    out = out.sort_values("ts_ms").drop_duplicates(subset=["ts_ms"]).reset_index(drop=True)
    out["dt_ms"] = out["ts_ms"].diff().fillna(0)
    out["sample_index"] = range(len(out))

    return out


def validate_imported_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    missing = [c for c in INTERNAL_REQUIRED_COLUMNS if c not in df.columns]

    total_rows = len(df)
    valid_min_rows = int(df[["ts_ms", "gaze_x", "gaze_y"]].notna().all(axis=1).sum()) if total_rows else 0

    x_out = 0
    y_out = 0
    if "gaze_x" in df.columns:
        x_out = int((~df["gaze_x"].between(0, 1, inclusive="both")).fillna(False).sum())
    if "gaze_y" in df.columns:
        y_out = int((~df["gaze_y"].between(0, 1, inclusive="both")).fillna(False).sum())

    return {
        "ok": len(missing) == 0 and total_rows > 0 and valid_min_rows > 0,
        "missing_columns": missing,
        "rows_total": int(total_rows),
        "rows_valid_minimal": valid_min_rows,
        "gaze_x_out_of_range": x_out,
        "gaze_y_out_of_range": y_out,
        "columns_found": list(df.columns),
    }


def dataframe_to_sample_rows(df: pd.DataFrame) -> list[dict]:
    """Converte il dataframe in lista di dict pronta per insert DB."""
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


def _safe_scalar(value: Any):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value
