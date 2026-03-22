from __future__ import annotations

from copy import deepcopy


DEFAULT_PROTOCOLS = {
    "reading_standard": {
        "label": "Reading standard",
        "description": "Protocollo base per lettura e stabilità oculomotoria.",
        "sampling_rate_hint_hz": None,
        "fixation_min_ms": 80,
        "saccade_velocity_threshold": 30.0,
        "blink_confidence_threshold": 0.2,
        "line_cluster_tolerance_px": 40,
        "distance_zones_cm": {
            "near_max": 45.0,
            "mid_max": 75.0,
        },
    },
    "visual_attention": {
        "label": "Visual attention",
        "description": "Protocollo orientato ad attenzione visiva e instabilità.",
        "sampling_rate_hint_hz": None,
        "fixation_min_ms": 60,
        "saccade_velocity_threshold": 35.0,
        "blink_confidence_threshold": 0.2,
        "line_cluster_tolerance_px": 50,
        "distance_zones_cm": {
            "near_max": 45.0,
            "mid_max": 75.0,
        },
    },
    "oculomotor_screening": {
        "label": "Oculomotor screening",
        "description": "Screening rapido di fissazioni, saccadi e regressioni.",
        "sampling_rate_hint_hz": None,
        "fixation_min_ms": 70,
        "saccade_velocity_threshold": 28.0,
        "blink_confidence_threshold": 0.2,
        "line_cluster_tolerance_px": 45,
        "distance_zones_cm": {
            "near_max": 45.0,
            "mid_max": 75.0,
        },
    },
    "binocularity_basic": {
        "label": "Binocularity basic",
        "description": "Protocollo base per allineamento binocularità.",
        "sampling_rate_hint_hz": None,
        "fixation_min_ms": 80,
        "saccade_velocity_threshold": 30.0,
        "blink_confidence_threshold": 0.2,
        "line_cluster_tolerance_px": 40,
        "distance_zones_cm": {
            "near_max": 45.0,
            "mid_max": 75.0,
        },
    },
}


def list_protocols() -> list[dict]:
    items = []
    for key, cfg in DEFAULT_PROTOCOLS.items():
        items.append(
            {
                "key": key,
                "label": cfg["label"],
                "description": cfg.get("description", ""),
            }
        )
    return items


def get_protocol_config(protocol_name: str | None) -> dict:
    key = protocol_name or "reading_standard"
    cfg = DEFAULT_PROTOCOLS.get(key, DEFAULT_PROTOCOLS["reading_standard"])
    return deepcopy(cfg)
