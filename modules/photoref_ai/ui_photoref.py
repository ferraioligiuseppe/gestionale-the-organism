import streamlit as st
from PIL import Image
import numpy as np
import cv2


def detect_eyes_simple(img):
    h, w = img.shape[:2]

    left = img[int(h*0.3):int(h*0.6), int(w*0.2):int(w*0.45)]
    right = img[int(h*0.3):int(h*0.6), int(w*0.55):int(w*0.8)]

    return left, right


def segment_pupil(eye):
    gray = cv2.cvtColor(eye, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7,7), 0)

    _, thresh = cv2.threshold(blur, 50, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mask = np.zeros_like(gray)
    overlay = eye.copy()

    if contours:
        cnt = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [cnt], -1, 255, -1)
        cv2.drawContours(overlay, [cnt], -1, (0,255,0), 2)

    return mask, overlay


def compute_gradient(eye, mask):
    gray = cv2.cvtColor(eye, cv2.COLOR_BGR2GRAY).astype(np.float32)

    valid = mask > 0
    if np.sum(valid) == 0:
        return 0, 0

    h, w = gray.shape
    mid_x = w // 2
    mid_y = h // 2

    left = gray[:, :mid_x]
    right = gray[:, mid_x:]
    top = gray[:mid_y, :]
    bottom = gray[mid_y:, :]

    return float(np.mean(right) - np.mean(left)), float(np.mean(bottom) - np.mean(top))


def ui_photoref():
    st.title("📸 Photoref AI (v2)")
    st.caption("Analisi base pupillare con gradiente luminoso")

    uploaded = st.file_uploader("Carica immagine", type=["jpg", "png"])

    if not uploaded:
        st.info("Carica una foto del volto")
        return

    img = Image.open(uploaded).convert("RGB")
    img_np = np.array(img)
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    st.image(img, caption="Originale")

    left_eye, right_eye = detect_eyes_simple(img_bgr)

    col1, col2 = st.columns(2)

    def process(label, eye, col):
        with col:
            st.subheader(label)

            if eye is None or eye.size == 0:
                st.warning("Occhio non rilevato")
                return None

            st.image(cv2.cvtColor(eye, cv2.COLOR_BGR2RGB))

            mask, overlay = segment_pupil(eye)
            st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), caption="Pupilla")

            h_grad, v_grad = compute_gradient(eye, mask)

            st.metric("Gradiente Orizzontale", round(h_grad, 2))
            st.metric("Gradiente Verticale", round(v_grad, 2))

            return h_grad, v_grad

    left_feats = process("Occhio Sinistro", left_eye, col1)
    right_feats = process("Occhio Destro", right_eye, col2)

    if left_feats and right_feats:
        delta = abs(left_feats[0] - right_feats[0])

        st.subheader("Confronto")

        st.metric("Δ Gradiente OD-OS", round(delta, 2))

        if delta > 10:
            st.warning("Possibile anisometropia")
        else:
            st.success("Simmetria accettabile")
