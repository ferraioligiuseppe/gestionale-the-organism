import cv2
import numpy as np

def compute_photoref_features(eye_bgr, pupil_mask):
    gray = cv2.cvtColor(eye_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

    valid = pupil_mask > 0
    if np.sum(valid) == 0:
        return {}

    values = gray[valid]

    h, w = gray.shape
    mid_x = w // 2
    mid_y = h // 2

    left = gray[:, :mid_x]
    right = gray[:, mid_x:]
    top = gray[:mid_y, :]
    bottom = gray[mid_y:, :]

    return {
        "mean_intensity": float(np.mean(values)),
        "horizontal_gradient": float(np.mean(right) - np.mean(left)),
        "vertical_gradient": float(np.mean(bottom) - np.mean(top)),
        "pupil_area_px": int(np.sum(valid))
    }