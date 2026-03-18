# modules/gaze_tracking/ui_gaze_tracking.py

from __future__ import annotations

from .ui_webcam_browser_v3 import ui_webcam_browser_v3


def ui_gaze_tracking(paziente_id=None, paziente_label=""):
    return ui_webcam_browser_v3(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )
