import streamlit as st
from PIL import Image
import numpy as np


def _traffic_light(score: int):
    if score >= 80:
        return "🟢", "Ottima"
    if score >= 50:
        return "🟡", "Accettabile"
    return "🔴", "Scarsa"


def _basic_image_checks(img_pil):
    width, height = img_pil.size
    resolution_ok = width >= 900 and height >= 900
    return {
        "width": width,
        "height": height,
        "resolution_ok": resolution_ok,
    }


def _load_mediapipe():
    import mediapipe as mp
    return mp


def _detect_face_and_eyes_with_mediapipe(img_rgb):
    mp = _load_mediapipe()
    mp_face_mesh = mp.solutions.face_mesh

    left_eye_idx = [33, 133, 159, 145, 153, 144]
    right_eye_idx = [362, 263, 386, 374, 380, 373]

    h, w = img_rgb.shape[:2]

    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
    ) as face_mesh:
        results = face_mesh.process(img_rgb)

    if not results.multi_face_landmarks:
        return {
            "success": False,
            "annotated": img_rgb,
            "left_eye": None,
            "right_eye": None,
            "face_detected": False,
            "eyes_detected": False,
        }

    annotated = img_rgb.copy()
    face_landmarks = results.multi_face_landmarks[0]
    pts = [(lm.x, lm.y) for lm in face_landmarks.landmark]

    def crop_from_points(points, pad=24):
        xs = [int(p[0] * w) for p in points]
        ys = [int(p[1] * h) for p in points]

        x1 = max(min(xs) - pad, 0)
        y1 = max(min(ys) - pad, 0)
        x2 = min(max(xs) + pad, w)
        y2 = min(max(ys) + pad, h)

        return annotated[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)

    left_points = [pts[i] for i in left_eye_idx]
    right_points = [pts[i] for i in right_eye_idx]

    left_eye, left_box = crop_from_points(left_points)
    right_eye, right_box = crop_from_points(right_points)

    try:
        import cv2
        cv2.rectangle(annotated, (left_box[0], left_box[1]), (left_box[2], left_box[3]), (0, 255, 0), 2)
        cv2.rectangle(annotated, (right_box[0], right_box[1]), (right_box[2], right_box[3]), (255, 0, 0), 2)
    except Exception:
        pass

    eyes_detected = left_eye is not None and right_eye is not None and left_eye.size > 0 and right_eye.size > 0

    return {
        "success": True,
        "annotated": annotated,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "face_detected": True,
        "eyes_detected": eyes_detected,
    }


def _evaluate_photoref_guidance(img_pil, face_detected: bool, eyes_detected: bool):
    basic = _basic_image_checks(img_pil)

    score = 0
    if basic["resolution_ok"]:
        score += 35
    if face_detected:
        score += 30
    if eyes_detected:
        score += 25

    # placeholder clinici: finché non analizziamo riflesso e illuminazione vera
    frontal_warning = True
    useful_reflex = False

    if not frontal_warning:
        score += 5
    if useful_reflex:
        score += 5

    light_icon, light_label = _traffic_light(score)

    return {
        **basic,
        "face_detected": face_detected,
        "eyes_detected": eyes_detected,
        "frontal_warning": frontal_warning,
        "useful_reflex": useful_reflex,
        "score": score,
        "quality_icon": light_icon,
        "quality_label": light_label,
    }


def ui_photoref():
    st.title("📸 Photoref AI – Acquisizione Guidata")
    st.caption("Semaforo qualità + rilevazione occhi con MediaPipe")

    st.markdown(
        """
### Istruzioni di acquisizione
- distanza indicativa: **50–100 cm**
- ambiente: **semi-buio**
- paziente: **sguardo diritto**
- evita luce frontale forte
- per photoretinoscopy reale serve luce **leggermente eccentrica**
"""
    )

    uploaded = st.file_uploader(
        "Carica immagine",
        type=["jpg", "jpeg", "png"],
        key="photoref_guided_mp_upload",
    )

    if uploaded is None:
        st.info("Carica una foto per iniziare.")
        return

    img_pil = Image.open(uploaded).convert("RGB")
    img_rgb = np.array(img_pil)

    st.subheader("Anteprima")
    st.image(img_pil, use_container_width=True)

    try:
        result = _detect_face_and_eyes_with_mediapipe(img_rgb)
        mp_ok = True
    except Exception as e:
        mp_ok = False
        result = {
            "success": False,
            "annotated": img_rgb,
            "left_eye": None,
            "right_eye": None,
            "face_detected": False,
            "eyes_detected": False,
        }
        st.warning("MediaPipe non disponibile o non caricato correttamente.")
        with st.expander("Dettagli errore MediaPipe"):
            st.exception(e)

    quality = _evaluate_photoref_guidance(
        img_pil,
        face_detected=result["face_detected"],
        eyes_detected=result["eyes_detected"],
    )

    st.subheader("Semaforo qualità")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stato", f"{quality['quality_icon']} {quality['quality_label']}")
    c2.metric("Score", f"{quality['score']}/100")
    c3.metric("Risoluzione", f"{quality['width']}×{quality['height']}")

    st.subheader("Controlli")
    if quality["resolution_ok"]:
        st.success("✔ Risoluzione adeguata")
    else:
        st.error("✘ Risoluzione troppo bassa")

    if quality["face_detected"]:
        st.success("✔ Volto rilevato")
    else:
        st.error("✘ Volto non rilevato")

    if quality["eyes_detected"]:
        st.success("✔ Occhi rilevati")
    else:
        st.warning("⚠ Occhi non rilevati correttamente")

    if quality["frontal_warning"]:
        st.warning("⚠ La foto sembra compatibile con luce frontale/non eccentrica")
    else:
        st.success("✔ Illuminazione compatibile")

    if quality["useful_reflex"]:
        st.success("✔ Riflesso photoret utile")
    else:
        st.warning("⚠ Riflesso photoret non ancora validato in questa versione")

    st.subheader("Feedback operativo")
    if not quality["resolution_ok"]:
        st.error("Avvicinati un po' di più o usa una foto più nitida.")
    if not quality["face_detected"]:
        st.error("Centra meglio il volto.")
    if quality["face_detected"] and not quality["eyes_detected"]:
        st.error("Assicurati che entrambi gli occhi siano ben visibili e non coperti.")
    if quality["frontal_warning"]:
        st.info(
            "Per uno scatto più utile: riduci la luce frontale e usa una sorgente leggermente laterale."
        )

    st.subheader("Rilevazione")
    st.image(result["annotated"], caption="Volto / ROI occhi", use_container_width=True)

    if result["eyes_detected"]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Occhio sinistro")
            st.image(result["left_eye"], use_container_width=True)
        with col2:
            st.markdown("### Occhio destro")
            st.image(result["right_eye"], use_container_width=True)

    st.subheader("Stato finale")
    if quality["score"] >= 80:
        st.success("Immagine buona per step successivo di analisi.")
    elif quality["score"] >= 50:
        st.warning("Immagine discreta, ma migliorabile.")
    else:
        st.error("Immagine non idonea per analisi affidabile.")

    if not mp_ok:
        st.info("Il modulo resta utilizzabile anche senza MediaPipe, ma senza rilevazione occhi reale.")
