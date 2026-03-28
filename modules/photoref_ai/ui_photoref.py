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


def _fallback_eye_crop(img_rgb):
    h, w = img_rgb.shape[:2]

    left_eye = img_rgb[int(h * 0.32):int(h * 0.58), int(w * 0.18):int(w * 0.46)]
    right_eye = img_rgb[int(h * 0.32):int(h * 0.58), int(w * 0.54):int(w * 0.82)]

    return {
        "success": True,
        "annotated": img_rgb,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "face_detected": False,
        "eyes_detected": True,
        "used_fallback": True,
    }


def _detect_face_and_eyes(img_rgb):
    try:
        import mediapipe as mp
    except Exception:
        return _fallback_eye_crop(img_rgb)

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
        return _fallback_eye_crop(img_rgb)

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

    eyes_detected = (
        left_eye is not None
        and right_eye is not None
        and left_eye.size > 0
        and right_eye.size > 0
    )

    return {
        "success": True,
        "annotated": annotated,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "face_detected": True,
        "eyes_detected": eyes_detected,
        "used_fallback": False,
    }


def _segment_pupil_numpy(eye_rgb):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2)

    h, w = gray.shape
    if h < 10 or w < 10:
        return {
            "mask": np.zeros((h, w), dtype=np.uint8),
            "overlay": eye_rgb,
            "area": 0,
            "center": None,
            "confidence": 0.0,
        }

    y1 = int(h * 0.18)
    y2 = int(h * 0.82)
    x1 = int(w * 0.18)
    x2 = int(w * 0.82)

    core = gray[y1:y2, x1:x2]
    if core.size == 0:
        return {
            "mask": np.zeros((h, w), dtype=np.uint8),
            "overlay": eye_rgb,
            "area": 0,
            "center": None,
            "confidence": 0.0,
        }

    threshold = np.percentile(core, 18)
    raw_mask = (gray <= threshold).astype(np.uint8)

    central_mask = np.zeros_like(raw_mask)
    central_mask[y1:y2, x1:x2] = 1
    raw_mask = raw_mask * central_mask

    ys, xs = np.where(raw_mask > 0)
    if len(xs) == 0:
        return {
            "mask": np.zeros((h, w), dtype=np.uint8),
            "overlay": eye_rgb,
            "area": 0,
            "center": None,
            "confidence": 0.0,
        }

    cx = int(np.mean(xs))
    cy = int(np.mean(ys))

    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    keep = dist <= max(6, min(h, w) * 0.18)

    xs2 = xs[keep]
    ys2 = ys[keep]

    mask = np.zeros_like(raw_mask, dtype=np.uint8)
    mask[ys2, xs2] = 1
    area = int(mask.sum())

    overlay = eye_rgb.copy()
    overlay[mask > 0] = [0, 255, 0]

    darkness = float(np.mean(gray[mask > 0])) if area > 0 else 255.0
    global_mean = float(np.mean(gray))
    confidence = 0.0
    if area > 20:
        confidence = max(0.0, min(1.0, (global_mean - darkness) / 90.0))

    return {
        "mask": mask,
        "overlay": overlay,
        "area": area,
        "center": (cx, cy) if area > 0 else None,
        "confidence": confidence,
    }


def _compute_gradients(eye_rgb, mask):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2)

    valid = mask > 0
    if np.sum(valid) == 0:
        return {
            "mean_intensity": 0.0,
            "horizontal_gradient": 0.0,
            "vertical_gradient": 0.0,
            "nasal_temporal_asymmetry": 0.0,
            "superior_inferior_asymmetry": 0.0,
        }

    ys, xs = np.where(valid)
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()

    pupil = gray[y_min:y_max + 1, x_min:x_max + 1]
    pupil_mask = valid[y_min:y_max + 1, x_min:x_max + 1]

    values = pupil[pupil_mask]
    mean_intensity = float(np.mean(values)) if values.size else 0.0

    h, w = pupil.shape
    mid_x = max(1, w // 2)
    mid_y = max(1, h // 2)

    left_vals = pupil[:, :mid_x][pupil_mask[:, :mid_x]]
    right_vals = pupil[:, mid_x:][pupil_mask[:, mid_x:]]
    top_vals = pupil[:mid_y, :][pupil_mask[:mid_y, :]]
    bottom_vals = pupil[mid_y:, :][pupil_mask[mid_y:, :]]

    l_mean = float(np.mean(left_vals)) if left_vals.size else 0.0
    r_mean = float(np.mean(right_vals)) if right_vals.size else 0.0
    t_mean = float(np.mean(top_vals)) if top_vals.size else 0.0
    b_mean = float(np.mean(bottom_vals)) if bottom_vals.size else 0.0

    return {
        "mean_intensity": mean_intensity,
        "horizontal_gradient": r_mean - l_mean,
        "vertical_gradient": b_mean - t_mean,
        "nasal_temporal_asymmetry": r_mean - l_mean,
        "superior_inferior_asymmetry": b_mean - t_mean,
    }


def _evaluate_photoref_guidance(img_pil, face_detected, eyes_detected, reflex_useful):
    basic = _basic_image_checks(img_pil)

    score = 0
    if basic["resolution_ok"]:
        score += 30
    if face_detected:
        score += 25
    if eyes_detected:
        score += 25
    if reflex_useful:
        score += 20

    quality_icon, quality_label = _traffic_light(score)

    return {
        **basic,
        "face_detected": face_detected,
        "eyes_detected": eyes_detected,
        "reflex_useful": reflex_useful,
        "score": score,
        "quality_icon": quality_icon,
        "quality_label": quality_label,
    }


def _analyze_eye(label, eye_rgb):
    if eye_rgb is None or eye_rgb.size == 0:
        return {
            "ok": False,
            "eye_rgb": None,
            "overlay": None,
            "mask": None,
            "area": 0,
            "confidence": 0.0,
            "features": None,
            "useful_reflex": False,
            "message": f"{label}: ROI non disponibile",
        }

    seg = _segment_pupil_numpy(eye_rgb)
    feats = _compute_gradients(eye_rgb, seg["mask"])

    useful_reflex = seg["area"] > 40 and seg["confidence"] >= 0.18
    msg = "Riflesso/pupilla utili" if useful_reflex else "Riflesso non sufficientemente utile"

    return {
        "ok": True,
        "eye_rgb": eye_rgb,
        "overlay": seg["overlay"],
        "mask": seg["mask"],
        "area": seg["area"],
        "confidence": seg["confidence"],
        "features": feats,
        "useful_reflex": useful_reflex,
        "message": msg,
    }


def ui_photoref():
    st.title("📸 Photoref AI – Acquisizione Guidata + Analisi Base")
    st.caption("Semaforo qualità, crop occhi, segmentazione pupilla e gradienti")

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
        key="photoref_guided_analysis_upload",
    )

    if uploaded is None:
        st.info("Carica una foto per iniziare.")
        return

    img_pil = Image.open(uploaded).convert("RGB")
    img_rgb = np.array(img_pil)

    st.subheader("Anteprima")
    st.image(img_pil, use_container_width=True)

    result = _detect_face_and_eyes(img_rgb)

    if result.get("used_fallback"):
        st.warning("MediaPipe non disponibile: uso ritaglio occhi stimato (fallback).")

    left_analysis = _analyze_eye("Occhio sinistro", result["left_eye"])
    right_analysis = _analyze_eye("Occhio destro", result["right_eye"])

    reflex_useful = left_analysis["useful_reflex"] or right_analysis["useful_reflex"]

    quality = _evaluate_photoref_guidance(
        img_pil,
        face_detected=result["face_detected"],
        eyes_detected=result["eyes_detected"],
        reflex_useful=reflex_useful,
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
        st.error("✘ Risoluzione non adeguata")

    if quality["face_detected"]:
        st.success("✔ Volto rilevato")
    else:
        st.warning("⚠ Volto non rilevato con MediaPipe")

    if quality["eyes_detected"]:
        st.success("✔ Occhi rilevati / stimati")
    else:
        st.warning("⚠ Occhi non rilevati correttamente")

    if quality["reflex_useful"]:
        st.success("✔ Almeno un riflesso/pupilla utile")
    else:
        st.warning("⚠ Riflesso/pupilla non ancora sufficientemente utili")

    st.subheader("Rilevazione")
    st.image(result["annotated"], caption="Volto / ROI occhi", use_container_width=True)

    if result["eyes_detected"]:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Occhio sinistro")
            if left_analysis["eye_rgb"] is not None:
                st.image(left_analysis["eye_rgb"], use_container_width=True)
            if left_analysis["overlay"] is not None:
                st.image(left_analysis["overlay"], caption="Segmentazione pupilla", use_container_width=True)
            st.caption(left_analysis["message"])

            if left_analysis["features"] is not None:
                st.json({
                    "pupil_area_px": int(left_analysis["area"]),
                    "confidence": round(left_analysis["confidence"], 3),
                    "mean_intensity": round(left_analysis["features"]["mean_intensity"], 3),
                    "horizontal_gradient": round(left_analysis["features"]["horizontal_gradient"], 3),
                    "vertical_gradient": round(left_analysis["features"]["vertical_gradient"], 3),
                })

        with col2:
            st.markdown("### Occhio destro")
            if right_analysis["eye_rgb"] is not None:
                st.image(right_analysis["eye_rgb"], use_container_width=True)
            if right_analysis["overlay"] is not None:
                st.image(right_analysis["overlay"], caption="Segmentazione pupilla", use_container_width=True)
            st.caption(right_analysis["message"])

            if right_analysis["features"] is not None:
                st.json({
                    "pupil_area_px": int(right_analysis["area"]),
                    "confidence": round(right_analysis["confidence"], 3),
                    "mean_intensity": round(right_analysis["features"]["mean_intensity"], 3),
                    "horizontal_gradient": round(right_analysis["features"]["horizontal_gradient"], 3),
                    "vertical_gradient": round(right_analysis["features"]["vertical_gradient"], 3),
                })

    st.subheader("Confronto OD-OS")
    if left_analysis["features"] is not None and right_analysis["features"] is not None:
        delta_h = abs(
            left_analysis["features"]["horizontal_gradient"]
            - right_analysis["features"]["horizontal_gradient"]
        )
        delta_v = abs(
            left_analysis["features"]["vertical_gradient"]
            - right_analysis["features"]["vertical_gradient"]
        )

        c1, c2 = st.columns(2)
        c1.metric("Δ gradiente orizzontale", f"{delta_h:.3f}")
        c2.metric("Δ gradiente verticale", f"{delta_v:.3f}")

        if delta_h > 12 or delta_v > 12:
            st.warning("Possibile asimmetria interoculare da approfondire.")
        else:
            st.success("Nessuna forte asimmetria rilevata in questa analisi preliminare.")
    else:
        st.info("Confronto non disponibile: segmentazione insufficiente in uno o entrambi gli occhi.")

    st.subheader("Feedback operativo")
    if not quality["resolution_ok"]:
        st.error("Usa una foto più nitida o più ravvicinata.")
    if not quality["reflex_useful"]:
        st.info(
            "Per una photoretinoscopy più utile: riduci la luce frontale, usa una sorgente leggermente laterale e prova in ambiente semi-buio."
        )

    st.subheader("Stato finale")
    if quality["score"] >= 80:
        st.success("Immagine buona per step successivo di analisi.")
    elif quality["score"] >= 50:
        st.warning("Immagine discreta, ma migliorabile.")
    else:
        st.error("Immagine non idonea per analisi affidabile.")
