import streamlit as st
from PIL import Image
from .utils.image_io import pil_to_bgr, bgr_to_rgb
from .logic.face_eye_detect import detect_face_and_eyes
from .logic.pupil_segmentation import segment_pupil_basic
from .logic.photoref_features import compute_photoref_features
from .logic.quality_control import evaluate_image_quality

def ui_photoref():
    st.title("Photoref AI SAFE")

    uploaded = st.file_uploader("Carica immagine", type=["jpg","png"])

    if not uploaded:
        return

    img = Image.open(uploaded).convert("RGB")
    img_bgr = pil_to_bgr(img)

    st.image(img)

    q = evaluate_image_quality(img_bgr)
    st.write(q)

    res = detect_face_and_eyes(img_bgr)

    for label, eye in [("Sinistro", res["left_eye"]), ("Destro", res["right_eye"])]:
        st.subheader(label)
        st.image(bgr_to_rgb(eye))

        pupil = segment_pupil_basic(eye)
        st.image(pupil["overlay_rgb"])

        feats = compute_photoref_features(eye, pupil["mask"])
        st.write(feats)