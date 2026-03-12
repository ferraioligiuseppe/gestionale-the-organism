import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "gaze_tracker_component",
    path=os.path.join(os.path.dirname(__file__), "frontend"),
)

def gaze_tracker_component(*, key=None, mode="calibration", task=None, height=760):
    return _component_func(
        key=key,
        mode=mode,
        task=task or {},
        default={},
        height=height,
    )
