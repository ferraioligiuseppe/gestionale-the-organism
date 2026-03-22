from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pandas as pd


CANONICAL_COLUMNS = [
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
    "target_label",
    "source_vendor",
    "source_format",
    "source_filename",
]


@dataclass
class ImportResult:
    df: pd.DataFrame
    metadata: dict[str, Any]
    validation: dict[str, Any]


def load_eye_tracker_file(uploaded_file) -> pd.DataFrame:
    filename = getattr(uploaded_file, "name", "unknown")
    suffix = filename.lower().split(".")[-1]

    file_bytes = uploaded_file.read()
    buffer = BytesIO(file_bytes)

    if suffix == "csv":
        return pd.read_csv(buffer)
    if suffix in {"xls", "xlsx"}:
        return pd.read_excel(buffer)

    raise ValueError(f"Formato file non supportato: {filename}")


def detect_source_vendor(df: pd.DataFrame, filename: str | None = None) -> str:
    cols = {str(c).strip().lower() for c in df.columns}
    file_name_l = (filename or "").lower()

    tobii_markers = {"gaze point x", "gaze point y", "validity left", "validity right"}
    thomson_markers = {"timestamp", "fixation", "saccade", "pupil"}
    generic_markers = {"ts_ms", "gaze_x", "gaze_y"}

    if tobii_markers.intersection(cols) or "tobii" in file_name_l:
        return "tobii"
    if thomson_markers.intersection(cols) or "thomson" in file_name_l:
        return "thomson"
    if generic_markers.issubset(cols):
        return "generic"
    return "generic"


def _coerce_bool_flag(series: pd.Series) -> pd.Series:
    if series is None:
        return pd.Series(dtype="boolean")
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"1", "true", "yes", "y", "fixation", "saccade", "blink"})


def _ensure_columns(df: pd.DataFrame, source_vendor: str, source_format: str, source_filename: str) -> pd.DataFrame:
    out = df.copy()

    for col in CANONICAL_COLUMNS:
        if col not in out.columns:
            out[col] = None

    out["source_vendor"] = source_vendor
    out["source_format"] = source_format
    out["source_filename"] = source_filename

    out = out[CANONICAL_COLUMNS].copy()
    return out


def normalize_tobii_dataframe(df: pd.DataFrame, filename: str = "") -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    out = pd.DataFrame()

    out["ts_ms"] = pd.to_numeric(df[cols.get("timestamp", list(df.columns)[0])], errors="coerce")
    out["gaze_x"] = pd.to_numeric(df[cols.get("gaze point x")], errors="coerce") if cols.get("gaze point x") else None
    out["gaze_y"] = pd.to_numeric(df[cols.get("gaze point y")], errors="coerce") if cols.get("gaze point y") else None
    out["confidence"] = 1.0
    out["fixation_flag"] = False
    out["saccade_flag"] = False
    out["blink_flag"] = False
    out["eye_left_x"] = pd.to_numeric(df[cols.get("left gaze point x")], errors="coerce") if cols.get("left gaze point x") else None
    out["eye_left_y"] = pd.to_numeric(df[cols.get("left gaze point y")], errors="coerce") if cols.get("left gaze point y") else None
    out["eye_right_x"] = pd.to_numeric(df[cols.get("right gaze point x")], errors="coerce") if cols.get("right gaze point x") else None
    out["eye_right_y"] = pd.to_numeric(df[cols.get("right gaze point y")], errors="coerce") if cols.get("right gaze point y") else None
    out["pupil_size"] = None
    out["distance_cm_est"] = None
    out["target_x"] = None
    out["target_y"] = None
    out["target_label"] = None

    return _finalize_internal_dataframe(
        out,
        source_vendor="tobii",
        source_format=filename.lower().split(".")[-1] if filename else "unknown",
        source_filename=filename,
    )


def normalize_thomson_dataframe(df: pd.DataFrame, filename: str = "") -> pd.DataFrame:
    cols = {c.lower(): c for c in df.columns}
    out = pd.DataFrame()

    out["ts_ms"] = pd.to_numeric(df[cols.get("timestamp", list(df.columns)[0])], errors="coerce")
    out["gaze_x"] = pd.to_numeric(df[cols.get("gaze_x", cols.get("x", ""))], errors="coerce") if cols.get("gaze_x") or cols.get("x") else None
    out["gaze_y"] = pd.to_numeric(df[cols.get("gaze_y", cols.get("y", ""))], errors="coerce") if cols.get("gaze_y") or cols.get("y") else None
    out["confidence"] = pd.to_numeric(df[cols.get("confidence")], errors="coerce") if cols.get("confidence") else 1.0
    out["fixation_flag"] = _coerce_bool_flag(df[cols.get("fixation")]) if cols.get("fixation") else False
    out["saccade_flag"] = _coerce_bool_flag(df[cols.get("saccade")]) if cols.get("saccade") else False
    out["blink_flag"] = _coerce_bool_flag(df[cols.get("blink")]) if cols.get("blink") else False
    out["eye_left_x"] = None
    out["eye_left_y"] = None
    out["eye_right_x"] = None
    out["eye_right_y"] = None
    out["pupil_size"] = pd.to_numeric(df[cols.get("pupil")], errors="coerce") if cols.get("pupil") else None
    out["distance_cm_est"] = pd.to_numeric(df[cols.get("distance_cm_est", cols.get("distance"))], errors="coerce") if cols.get("distance_cm_est") or cols.get("distance") else None
    out["target_x"] = None
    out["target_y"] = None
    out["target_label"] = df[cols.get("target_label")] if cols.get("target_label") else None

    return _finalize_internal_dataframe(
        out,
        source_vendor="thomson",
        source_format=filename.lower().split(".")[-1] if filename else "unknown",
        source_filename=filename,
    )


def normalize_generic_dataframe(df: pd.DataFrame, filename: str = "") -> pd.DataFrame:
    out = df.copy()

    if "ts_ms" not in out.columns:
        first_col = list(out.columns)[0]
        out["ts_ms"] = pd.to_numeric(out[first_col], errors="coerce")

    return _finalize_internal_dataframe(
        out,
        source_vendor="generic",
        source_format=filename.lower().split(".")[-1] if filename else "unknown",
        source_filename=filename,
    )


def _finalize_internal_dataframe(
    df: pd.DataFrame,
    source_vendor: str,
    source_format: str,
    source_filename: str,
) -> pd.DataFrame:
    out = _ensure_columns(df, source_vendor, source_format, source_filename)

    numeric_cols = [
        "ts_ms",
        "gaze_x",
        "gaze_y",
        "confidence",
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
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for flag_col in ["fixation_flag", "saccade_flag", "blink_flag"]:
        if out[flag_col].dtype != bool:
            out[flag_col] = out[flag_col].fillna(False).astype(bool)

    out = out.dropna(subset=["ts_ms"]).sort_values("ts_ms").reset_index(drop=True)
    return out


def validate_imported_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if df.empty:
        errors.append("Il file importato non contiene righe valide.")
        return {"valid": False, "errors": errors, "warnings": warnings}

    required = ["ts_ms", "gaze_x", "gaze_y"]
    missing_required = [c for c in required if c not in df.columns]
    if missing_required:
        errors.append(f"Colonne obbligatorie mancanti: {', '.join(missing_required)}")

    if df["ts_ms"].isna().all():
        errors.append("La colonna ts_ms è interamente vuota o non convertibile.")

    if df["gaze_x"].isna().mean() > 0.8:
        warnings.append("Molti valori gaze_x mancanti o non leggibili.")
    if df["gaze_y"].isna().mean() > 0.8:
        warnings.append("Molti valori gaze_y mancanti o non leggibili.")

    duplicated_ts = int(df["ts_ms"].duplicated().sum())
    if duplicated_ts > 0:
        warnings.append(f"Presenti {duplicated_ts} timestamp duplicati.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
    }


def import_eye_tracking_file(uploaded_file, forced_vendor: str = "auto") -> ImportResult:
    raw_df = load_eye_tracker_file(uploaded_file)
    filename = getattr(uploaded_file, "name", "unknown")
    source_format = filename.lower().split(".")[-1] if "." in filename else "unknown"

    vendor = detect_source_vendor(raw_df, filename=filename) if forced_vendor == "auto" else forced_vendor

    if vendor == "tobii":
        df = normalize_tobii_dataframe(raw_df, filename=filename)
    elif vendor == "thomson":
        df = normalize_thomson_dataframe(raw_df, filename=filename)
    else:
        df = normalize_generic_dataframe(raw_df, filename=filename)

    validation = validate_imported_dataframe(df)

    metadata = {
        "source_vendor": vendor,
        "source_format": source_format,
        "source_filename": filename,
        "raw_columns": [str(c) for c in raw_df.columns],
        "normalized_columns": list(df.columns),
        "row_count": int(len(df)),
    }

    return ImportResult(df=df, metadata=metadata, validation=validation)
