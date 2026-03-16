ORAL_FACE_ENABLED = False

ORAL_FACE_FUTURE_METRICS = [
    "mouth_open_ratio",
    "lip_seal_ratio",
    "oral_symmetry_index",
    "chin_motion_proxy",
    "jaw_stability_index",
    "tongue_visible_flag",
    "tongue_interposition_flag",
    "head_pitch",
    "head_yaw",
    "head_roll",
]


def get_oral_face_stub_info() -> dict:
    return {
        "enabled": ORAL_FACE_ENABLED,
        "status": "future_module_stub",
        "planned_metrics": ORAL_FACE_FUTURE_METRICS,
    }
