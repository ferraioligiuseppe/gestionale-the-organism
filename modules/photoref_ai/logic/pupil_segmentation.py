import cv2
import numpy as np

def segment_pupil_basic(eye_bgr):
    gray = cv2.cvtColor(eye_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)

    _, thresh = cv2.threshold(blur, 45, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mask = np.zeros_like(gray)
    overlay = eye_bgr.copy()

    if contours:
        cnt = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        cv2.drawContours(overlay, [cnt], -1, (0,255,0), 2)

    overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

    return {"mask": mask, "overlay_rgb": overlay_rgb}