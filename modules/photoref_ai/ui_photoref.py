import streamlit as st
from PIL import Image, ImageDraw
import numpy as np

from .ui_photoref_session import ui_photoref_session
from .ui_photoref_mobile import ui_photoref_mobile


def _traffic_light(score: int):
    if score >= 80:
        return "🟢", "Ottima"
    if score >= 50:
        return "🟡", "Accettabile"
    return "🔴", "Scarsa"


def _basic_image_checks(img_pil):
    width, height = img_pil.size
    resolution_ok = width >= 900 and height >= 900
    return {"width": width, "height": height, "resolution_ok": resolution_ok}


def _estimate_brightness(img_rgb):
    gray = np.mean(img_rgb.astype(np.float32), axis=2)
    return float(np.mean(gray))


def _brightness_label(brightness: float):
    if brightness < 70:
        return "troppo bassa"
    if brightness > 185:
        return "troppo alta"
    return "ok"


def _fallback_eye_crop(img_rgb):
    h, w = img_rgb.shape[:2]
    y_top = int(h * 0.22)
    y_bottom = int(h * 0.55)
    x_left = int(w * 0.15)
    x_right = int(w * 0.85)
    face_upper = img_rgb[y_top:y_bottom, x_left:x_right]
    fh, fw = face_upper.shape[:2]
    mid_x = fw // 2
    eye_pad_x = int(fw * 0.08)
    eye_pad_y = int(fh * 0.12)

    left_eye = face_upper[eye_pad_y:fh - eye_pad_y, eye_pad_x:mid_x - eye_pad_x]
    right_eye = face_upper[eye_pad_y:fh - eye_pad_y, mid_x + eye_pad_x:fw - eye_pad_x]

    # box stimate nel riferimento immagine completa
    left_box = (
        x_left + eye_pad_x,
        y_top + eye_pad_y,
        x_left + mid_x - eye_pad_x,
        y_top + fh - eye_pad_y,
    )
    right_box = (
        x_left + mid_x + eye_pad_x,
        y_top + eye_pad_y,
        x_left + fw - eye_pad_x,
        y_top + fh - eye_pad_y,
    )

    return {
        "success": True,
        "annotated": img_rgb,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "face_detected": False,
        "eyes_detected": True,
        "used_fallback": True,
        "left_box": left_box,
        "right_box": right_box,
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

    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as face_mesh:
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

    eyes_detected = left_eye is not None and right_eye is not None and left_eye.size > 0 and right_eye.size > 0
    return {
        "success": True,
        "annotated": annotated,
        "left_eye": left_eye,
        "right_eye": right_eye,
        "face_detected": True,
        "eyes_detected": eyes_detected,
        "used_fallback": False,
        "left_box": left_box,
        "right_box": right_box,
    }


def _draw_guidance_overlay(img_rgb, left_box=None, right_box=None):
    h, w = img_rgb.shape[:2]
    pil_img = Image.fromarray(img_rgb.copy())
    draw = ImageDraw.Draw(pil_img, "RGBA")

    # Maschera ideale
    face_box = (
        int(w * 0.20),
        int(h * 0.12),
        int(w * 0.80),
        int(h * 0.88),
    )
    left_eye_ideal = (
        int(w * 0.26),
        int(h * 0.30),
        int(w * 0.44),
        int(h * 0.46),
    )
    right_eye_ideal = (
        int(w * 0.56),
        int(h * 0.30),
        int(w * 0.74),
        int(h * 0.46),
    )

    # Ovale volto approssimato
    draw.ellipse(face_box, outline=(255, 255, 0, 220), width=5)

    # Finestre occhi ideali
    draw.rectangle(left_eye_ideal, outline=(0, 255, 255, 220), width=4)
    draw.rectangle(right_eye_ideal, outline=(0, 255, 255, 220), width=4)

    # linee guida
    draw.line((w // 2, int(h * 0.10), w // 2, int(h * 0.90)), fill=(255, 180, 0, 180), width=3)
    draw.line((int(w * 0.20), int(h * 0.38), int(w * 0.80), int(h * 0.38)), fill=(255, 180, 0, 180), width=3)

    # box rilevate/stimate
    if left_box:
        draw.rectangle(left_box, outline=(0, 255, 0, 220), width=4)
    if right_box:
        draw.rectangle(right_box, outline=(255, 0, 0, 220), width=4)

    return np.array(pil_img), left_eye_ideal, right_eye_ideal


def _box_center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _box_size(box):
    return (max(1.0, box[2] - box[0]), max(1.0, box[3] - box[1]))


def _guidance_feedback(img_rgb, left_box=None, right_box=None):
    h, w = img_rgb.shape[:2]
    brightness = _estimate_brightness(img_rgb)
    brightness_status = _brightness_label(brightness)

    left_ideal = (int(w * 0.26), int(h * 0.30), int(w * 0.44), int(h * 0.46))
    right_ideal = (int(w * 0.56), int(h * 0.30), int(w * 0.74), int(h * 0.46))

    alignment_score = 0
    messages = []

    if left_box and right_box:
        lcx, lcy = _box_center(left_box)
        rcx, rcy = _box_center(right_box)
        licx, licy = _box_center(left_ideal)
        ricx, ricy = _box_center(right_ideal)

        dx = abs((lcx - licx) + (rcx - ricx)) / 2.0
        dy = abs((lcy - licy) + (rcy - ricy)) / 2.0

        # distanza stimata dal size ratio
        lw, lh = _box_size(left_box)
        rw, rh = _box_size(right_box)
        iw, ih = _box_size(left_ideal)
        jw, jh = _box_size(right_ideal)
        size_ratio = ((lw / iw) + (lh / ih) + (rw / jw) + (rh / jh)) / 4.0

        if dx < w * 0.03 and dy < h * 0.03:
            alignment_score += 40
        elif dx < w * 0.06 and dy < h * 0.05:
            alignment_score += 25
            messages.append("Volto quasi centrato")
        else:
            if dx >= w * 0.06:
                messages.append("Sposta il volto verso il centro")
            if dy >= h * 0.05:
                messages.append("Alza o abbassa leggermente il telefono")

        if size_ratio < 0.75:
            messages.append("Troppo lontano")
            distance_label = "troppo lontano"
            distance_score = 10
        elif size_ratio > 1.30:
            messages.append("Troppo vicino")
            distance_label = "troppo vicino"
            distance_score = 10
        else:
            distance_label = "ok"
            distance_score = 30

        alignment_score += distance_score

        eye_level_delta = abs(lcy - rcy)
        if eye_level_delta < h * 0.02:
            alignment_score += 20
        else:
            messages.append("Raddrizza la testa")
    else:
        distance_label = "non stimabile"
        messages.append("Occhi non rilevati/stimati bene")

    if brightness_status == "ok":
        lum_score = 30
    elif brightness_status == "troppo bassa":
        lum_score = 12
        messages.append("Aumenta leggermente la luce")
    else:
        lum_score = 12
        messages.append("Riduci la luce frontale")

    total_score = min(100, alignment_score + lum_score)
    icon, label = _traffic_light(total_score)

    if not messages:
        messages.append("Acquisizione ben allineata")

    return {
        "brightness": round(brightness, 1),
        "brightness_status": brightness_status,
        "distance_label": distance_label,
        "alignment_score": alignment_score,
        "total_score": total_score,
        "quality_icon": icon,
        "quality_label": label,
        "messages": messages[:4],
    }


def _reflection_direction(offset_x, offset_y, offset_norm):
    if offset_x is None or offset_y is None or offset_norm is None:
        return "riflesso poco utile"
    if offset_norm < 0.12:
        return "riflesso centrale"

    vertical = ""
    horizontal = ""
    if offset_y < -2:
        vertical = "superiore"
    elif offset_y > 2:
        vertical = "inferiore"
    if offset_x < -2:
        horizontal = "nasale"
    elif offset_x > 2:
        horizontal = "temporale"

    if vertical and horizontal:
        return f"riflesso {vertical}-{horizontal}"
    if vertical:
        return f"riflesso {vertical}"
    if horizontal:
        return f"riflesso {horizontal}"
    if offset_norm < 0.30:
        return "riflesso decentrato lieve"
    return "riflesso molto decentrato"


def _segment_pupil_numpy(eye_rgb):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2)
    h, w = gray.shape
    if h < 10 or w < 10:
        return {"mask": np.zeros((h, w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}

    y1 = int(h * 0.18); y2 = int(h * 0.82); x1 = int(w * 0.18); x2 = int(w * 0.82)
    core = gray[y1:y2, x1:x2]
    if core.size == 0:
        return {"mask": np.zeros((h, w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}

    threshold = np.percentile(core, 18)
    raw_mask = (gray <= threshold).astype(np.uint8)
    central_mask = np.zeros_like(raw_mask)
    central_mask[y1:y2, x1:x2] = 1
    raw_mask = raw_mask * central_mask

    ys, xs = np.where(raw_mask > 0)
    if len(xs) == 0:
        return {"mask": np.zeros((h, w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}

    cx = int(np.mean(xs)); cy = int(np.mean(ys))
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    keep = dist <= max(6, min(h, w) * 0.18)
    xs2 = xs[keep]; ys2 = ys[keep]

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

    return {"mask": mask, "overlay": overlay, "area": area, "center": (cx, cy) if area > 0 else None, "confidence": confidence}


def _detect_bright_spot_in_pupil(eye_rgb, mask):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2)
    valid = mask > 0
    if np.sum(valid) == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": eye_rgb, "reflection_score": 0.0, "intensity_ratio": 0.0}

    ys, xs = np.where(valid)
    pupil_vals = gray[valid]
    if pupil_vals.size == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": eye_rgb, "reflection_score": 0.0, "intensity_ratio": 0.0}

    pupil_mean = float(np.mean(pupil_vals))
    thr = np.percentile(pupil_vals, 92)
    bright_mask = ((gray >= thr) & valid)
    bys, bxs = np.where(bright_mask)
    overlay = eye_rgb.copy()
    if len(bxs) == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": overlay, "reflection_score": 0.0, "intensity_ratio": 0.0}

    sx = float(np.mean(bxs)); sy = float(np.mean(bys))
    spot_intensity = float(np.mean(gray[bright_mask]))
    spot_pixels = int(np.sum(bright_mask))
    cy = float(np.mean(ys)); cx = float(np.mean(xs))
    pupil_w = max(1.0, float(xs.max() - xs.min()))
    pupil_h = max(1.0, float(ys.max() - ys.min()))
    offset_x = float(sx - cx); offset_y = float(sy - cy)
    offset_norm_x = offset_x / pupil_w; offset_norm_y = offset_y / pupil_h
    offset_norm = float(np.sqrt(offset_norm_x ** 2 + offset_norm_y ** 2))
    label = _reflection_direction(offset_x, offset_y, offset_norm)

    intensity_ratio = float(spot_intensity / max(1.0, pupil_mean))
    size_ratio = float(spot_pixels / max(1, np.sum(valid)))

    reflection_score = 0.0
    reflection_score += min(40.0, max(0.0, (intensity_ratio - 1.0) * 40.0))
    reflection_score += min(30.0, max(0.0, size_ratio * 600.0))
    reflection_score += min(30.0, max(0.0, (1.0 - min(1.0, offset_norm)) * 30.0))
    reflection_score = round(reflection_score, 2)

    overlay[bright_mask] = [255, 0, 0]
    x0 = max(0, int(round(sx)) - 2); x1 = min(overlay.shape[1], int(round(sx)) + 3)
    y0 = max(0, int(round(sy)) - 2); y1 = min(overlay.shape[0], int(round(sy)) + 3)
    overlay[y0:y1, x0:x1] = [255, 255, 0]

    return {"spot_center": (float(sx), float(sy)), "spot_intensity": spot_intensity, "spot_pixels": spot_pixels, "offset_x": offset_x, "offset_y": offset_y, "offset_norm": offset_norm, "label": label, "overlay": overlay, "reflection_score": reflection_score, "intensity_ratio": round(intensity_ratio, 3)}


def _analyze_eye(label, eye_rgb):
    if eye_rgb is None or eye_rgb.size == 0:
        return {"ok": False, "eye_rgb": None, "overlay": None, "area": 0, "confidence": 0.0, "message": f"{label}: ROI non disponibile", "pupil_center": None, "bright_spot": None}

    seg = _segment_pupil_numpy(eye_rgb)
    bright = _detect_bright_spot_in_pupil(eye_rgb, seg["mask"])
    useful_reflex = seg["area"] > 40 and seg["confidence"] >= 0.18 and bright["spot_center"] is not None and bright["spot_pixels"] > 5
    msg = bright["label"] if useful_reflex else "riflesso poco utile"

    return {"ok": True, "eye_rgb": eye_rgb, "overlay": bright["overlay"], "area": seg["area"], "confidence": seg["confidence"], "message": msg, "pupil_center": seg["center"], "bright_spot": bright}


def _render_eye_panel(title, analysis):
    st.markdown(f"### {title}")
    if analysis["eye_rgb"] is not None:
        st.image(analysis["eye_rgb"], use_container_width=True)
    if analysis["overlay"] is not None:
        st.image(analysis["overlay"], caption="Pupilla + spot luminoso", use_container_width=True)
    st.caption(analysis["message"])

    bright = analysis["bright_spot"]
    if bright:
        st.json({
            "pupil_area_px": int(analysis["area"]),
            "confidence": round(analysis["confidence"], 3),
            "pupil_center": analysis["pupil_center"],
            "bright_spot_center": bright["spot_center"],
            "spot_pixels": int(bright["spot_pixels"]),
            "offset_x": round(bright["offset_x"], 3) if bright["offset_x"] is not None else None,
            "offset_y": round(bright["offset_y"], 3) if bright["offset_y"] is not None else None,
            "offset_norm": round(bright["offset_norm"], 3) if bright["offset_norm"] is not None else None,
            "reflection_label": analysis["message"],
            "reflection_score": bright["reflection_score"],
            "intensity_ratio": bright["intensity_ratio"],
        })


def _ui_analysis():
    st.markdown("### 📸 Analisi riflesso + maschera guida")
    uploaded = st.file_uploader("Carica immagine", type=["jpg", "jpeg", "png"], key="photoref_guided_analysis_upload")
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

    overlay_img, _, _ = _draw_guidance_overlay(
        img_rgb,
        left_box=result.get("left_box"),
        right_box=result.get("right_box"),
    )
    guidance = _guidance_feedback(
        img_rgb,
        left_box=result.get("left_box"),
        right_box=result.get("right_box"),
    )

    st.subheader("Maschera guida acquisizione")
    st.image(overlay_img, caption="Sovraimpressione: sagoma volto, finestre occhi, linee guida", use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stato guida", f"{guidance['quality_icon']} {guidance['quality_label']}")
    c2.metric("Score guida", f"{guidance['total_score']}/100")
    c3.metric("Luminanza", f"{guidance['brightness']}")
    c4.metric("Distanza stimata", guidance["distance_label"])

    st.markdown("**Feedback acquisizione**")
    for msg in guidance["messages"]:
        st.info(msg)

    left_analysis = _analyze_eye("Occhio sinistro", result["left_eye"])
    right_analysis = _analyze_eye("Occhio destro", result["right_eye"])

    st.subheader("Rilevazione")
    st.image(result["annotated"], caption="Volto / ROI occhi", use_container_width=True)

    if result["eyes_detected"]:
        col1, col2 = st.columns(2)
        with col1:
            _render_eye_panel("Occhio sinistro", left_analysis)
        with col2:
            _render_eye_panel("Occhio destro", right_analysis)


def ui_photoref():
    if st.query_params.get("photoref_token", ""):
        ui_photoref_mobile()
        return

    st.title("📸 Photoref AI")
    tab1, tab2 = st.tabs(["Analisi riflesso", "Sessioni smartphone"])
    with tab1:
        _ui_analysis()
    with tab2:
        ui_photoref_session()
