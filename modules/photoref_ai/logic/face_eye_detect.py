import cv2

def detect_face_and_eyes(img):
    h, w = img.shape[:2]
    # fallback semplice (centro immagine)
    left = img[int(h*0.3):int(h*0.6), int(w*0.2):int(w*0.45)]
    right = img[int(h*0.3):int(h*0.6), int(w*0.55):int(w*0.8)]

    return {
        "success": True,
        "annotated": img,
        "left_eye": left,
        "right_eye": right
    }