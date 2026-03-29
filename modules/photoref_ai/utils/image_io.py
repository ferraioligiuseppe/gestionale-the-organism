import cv2
import numpy as np
from PIL import Image

def pil_to_bgr(pil_img: Image.Image) -> np.ndarray:
    rgb = np.array(pil_img)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

def bgr_to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)