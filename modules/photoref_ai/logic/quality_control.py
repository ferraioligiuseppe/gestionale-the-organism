import cv2
import numpy as np

def evaluate_image_quality(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = float(np.mean(gray))
    is_valid = sharpness > 40 and 40 < brightness < 220

    return {
        "sharpness": sharpness,
        "brightness": brightness,
        "is_valid": is_valid,
    }