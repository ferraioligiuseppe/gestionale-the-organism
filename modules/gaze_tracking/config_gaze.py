from __future__ import annotations

GAZE_DEFAULT_CONFIG = {
    "min_confidence": 0.60,
    "fix_min_dur_ms": 80,
    "fix_merge_gap_ms": 50,
    "max_dispersion": 0.03,
    "speed_threshold": 0.0008,      # coordinate normalizzate / ms
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

GAZE_PRESETS = {
    "clinical_standard": {
        **GAZE_DEFAULT_CONFIG,
    },
    "child_relaxed": {
        **GAZE_DEFAULT_CONFIG,
        "min_confidence": 0.50,
        "fix_min_dur_ms": 70,
        "dbscan_eps_y": 0.03,
        "off_text_margin": 0.05,
    },
    "high_precision_tracker": {
        **GAZE_DEFAULT_CONFIG,
        "min_confidence": 0.75,
        "fix_min_dur_ms": 90,
        "max_dispersion": 0.02,
        "dbscan_eps_y": 0.02,
        "off_text_margin": 0.03,
    },
}

SUPPORTED_IMPORT_TYPES = ["csv", "xls", "xlsx"]
