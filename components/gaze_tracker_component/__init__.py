from __future__ import annotations

import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "gaze_tracker_component",
    path=os.path.join(os.path.dirname(__file__), "frontend"),
)


def gaze_tracker_component(*, key=None, patient_id=None, patient_label="", protocol_name="free_observation", height=920):
    return _component_func(
        key=key,
        patient_id=patient_id,
        patient_label=patient_label,
        protocol_name=protocol_name,
        default={
            "component_status": "idle",
            "samples": [],
            "metrics": {},
            "pnev_indexes": {},
            "meta": {},
        },
        height=height,
    )
