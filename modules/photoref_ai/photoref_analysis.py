from __future__ import annotations
import numpy as np
from PIL import Image, ImageDraw

def traffic_light(score: int):
    if score >= 80:
        return "🟢", "Ottima"
    if score >= 50:
        return "🟡", "Accettabile"
    return "🔴", "Scarsa"

def estimate_brightness(img_rgb):
    gray = np.mean(img_rgb.astype(np.float32), axis=2)
    return float(np.mean(gray))

def brightness_label(brightness: float):
    if brightness < 70:
        return "troppo bassa"
    if brightness > 185:
        return "troppo alta"
    return "ok"

def sharpness_score(img_rgb):
    gray = np.mean(img_rgb.astype(np.float32), axis=2)
    gy, gx = np.gradient(gray)
    lap = np.abs(gx) + np.abs(gy)
    v = float(np.mean(lap))
    if v >= 18:
        return 100, "nitida"
    if v >= 10:
        return 70, "discreta"
    return 35, "mossa / sfocata"

def fallback_eye_crop(img_rgb):
    h, w = img_rgb.shape[:2]
    y_top = int(h * 0.22); y_bottom = int(h * 0.55)
    x_left = int(w * 0.15); x_right = int(w * 0.85)
    face_upper = img_rgb[y_top:y_bottom, x_left:x_right]
    fh, fw = face_upper.shape[:2]
    mid_x = fw // 2; eye_pad_x = int(fw * 0.08); eye_pad_y = int(fh * 0.12)
    left_eye = face_upper[eye_pad_y:fh-eye_pad_y, eye_pad_x:mid_x-eye_pad_x]
    right_eye = face_upper[eye_pad_y:fh-eye_pad_y, mid_x+eye_pad_x:fw-eye_pad_x]
    left_box = (x_left + eye_pad_x, y_top + eye_pad_y, x_left + mid_x - eye_pad_x, y_top + fh - eye_pad_y)
    right_box = (x_left + mid_x + eye_pad_x, y_top + eye_pad_y, x_left + fw - eye_pad_x, y_top + fh - eye_pad_y)
    return {"success": True, "annotated": img_rgb, "left_eye": left_eye, "right_eye": right_eye, "face_detected": False, "eyes_detected": True, "used_fallback": True, "left_box": left_box, "right_box": right_box}

def detect_face_and_eyes(img_rgb):
    try:
        import mediapipe as mp
    except Exception:
        return fallback_eye_crop(img_rgb)
    mp_face_mesh = mp.solutions.face_mesh
    left_eye_idx = [33, 133, 159, 145, 153, 144]
    right_eye_idx = [362, 263, 386, 374, 380, 373]
    h, w = img_rgb.shape[:2]
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True) as face_mesh:
        results = face_mesh.process(img_rgb)
    if not results.multi_face_landmarks:
        return fallback_eye_crop(img_rgb)
    annotated = img_rgb.copy()
    face_landmarks = results.multi_face_landmarks[0]
    pts = [(lm.x, lm.y) for lm in face_landmarks.landmark]
    def crop_from_points(points, pad=24):
        xs = [int(p[0] * w) for p in points]; ys = [int(p[1] * h) for p in points]
        x1 = max(min(xs) - pad, 0); y1 = max(min(ys) - pad, 0); x2 = min(max(xs) + pad, w); y2 = min(max(ys) + pad, h)
        return annotated[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)
    left_eye, left_box = crop_from_points([pts[i] for i in left_eye_idx])
    right_eye, right_box = crop_from_points([pts[i] for i in right_eye_idx])
    try:
        import cv2
        cv2.rectangle(annotated, (left_box[0], left_box[1]), (left_box[2], left_box[3]), (0, 255, 0), 2)
        cv2.rectangle(annotated, (right_box[0], right_box[1]), (right_box[2], right_box[3]), (255, 0, 0), 2)
    except Exception:
        pass
    eyes_detected = left_eye is not None and right_eye is not None and left_eye.size > 0 and right_eye.size > 0
    return {"success": True, "annotated": annotated, "left_eye": left_eye, "right_eye": right_eye, "face_detected": True, "eyes_detected": eyes_detected, "used_fallback": False, "left_box": left_box, "right_box": right_box}

def box_center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)

def box_size(box):
    return (max(1.0, box[2] - box[0]), max(1.0, box[3] - box[1]))

def draw_guidance_overlay(img_rgb, left_box=None, right_box=None):
    h, w = img_rgb.shape[:2]
    pil_img = Image.fromarray(img_rgb.copy())
    draw = ImageDraw.Draw(pil_img, "RGBA")
    face_box = (int(w * 0.20), int(h * 0.12), int(w * 0.80), int(h * 0.88))
    left_eye_ideal = (int(w * 0.26), int(h * 0.30), int(w * 0.44), int(h * 0.46))
    right_eye_ideal = (int(w * 0.56), int(h * 0.30), int(w * 0.74), int(h * 0.46))
    draw.ellipse(face_box, outline=(255, 255, 0, 220), width=5)
    draw.rectangle(left_eye_ideal, outline=(0, 255, 255, 220), width=4)
    draw.rectangle(right_eye_ideal, outline=(0, 255, 255, 220), width=4)
    draw.line((w // 2, int(h * 0.10), w // 2, int(h * 0.90)), fill=(255, 180, 0, 180), width=3)
    draw.line((int(w * 0.20), int(h * 0.38), int(w * 0.80), int(h * 0.38)), fill=(255, 180, 0, 180), width=3)
    if left_box: draw.rectangle(left_box, outline=(0, 255, 0, 220), width=4)
    if right_box: draw.rectangle(right_box, outline=(255, 0, 0, 220), width=4)
    return np.array(pil_img)

def guidance_feedback(img_rgb, left_box=None, right_box=None):
    h, w = img_rgb.shape[:2]
    brightness = estimate_brightness(img_rgb)
    brightness_status = brightness_label(brightness)
    blur_score, blur_label = sharpness_score(img_rgb)
    left_ideal = (int(w * 0.26), int(h * 0.30), int(w * 0.44), int(h * 0.46))
    right_ideal = (int(w * 0.56), int(h * 0.30), int(w * 0.74), int(h * 0.46))
    alignment_score = 0; messages = []
    if left_box and right_box:
        lcx, lcy = box_center(left_box); rcx, rcy = box_center(right_box)
        licx, licy = box_center(left_ideal); ricx, ricy = box_center(right_ideal)
        dx = abs((lcx - licx) + (rcx - ricx)) / 2.0
        dy = abs((lcy - licy) + (rcy - ricy)) / 2.0
        lw, lh = box_size(left_box); rw, rh = box_size(right_box)
        iw, ih = box_size(left_ideal); jw, jh = box_size(right_ideal)
        size_ratio = ((lw / iw) + (lh / ih) + (rw / jw) + (rh / jh)) / 4.0
        if dx < w * 0.03 and dy < h * 0.03: alignment_score += 35
        elif dx < w * 0.06 and dy < h * 0.05:
            alignment_score += 22; messages.append("Volto quasi centrato")
        else:
            if dx >= w * 0.06: messages.append("Sposta il volto verso il centro")
            if dy >= h * 0.05: messages.append("Alza o abbassa leggermente il telefono")
        if size_ratio < 0.75:
            messages.append("Troppo lontano"); distance_label = "troppo lontano"; alignment_score += 8
        elif size_ratio > 1.30:
            messages.append("Troppo vicino"); distance_label = "troppo vicino"; alignment_score += 8
        else:
            distance_label = "ok"; alignment_score += 25
        eye_level_delta = abs(lcy - rcy)
        if eye_level_delta < h * 0.02: alignment_score += 15
        else: messages.append("Raddrizza la testa")
    else:
        distance_label = "non stimabile"; messages.append("Occhi non rilevati/stimati bene")
    lum_score = 20 if brightness_status == "ok" else 8
    if brightness_status != "ok": messages.append("Regola la luce")
    total_score = min(100, alignment_score + lum_score + int(blur_score * 0.20))
    icon, label = traffic_light(total_score)
    if not messages: messages.append("Acquisizione ben allineata")
    return {"brightness": round(brightness,1), "brightness_status": brightness_status, "distance_label": distance_label, "alignment_score": alignment_score, "sharpness_score": blur_score, "sharpness_label": blur_label, "total_score": total_score, "quality_icon": icon, "quality_label": label, "messages": messages[:5]}

def segment_pupil_numpy(eye_rgb):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2)
    h, w = gray.shape
    if h < 10 or w < 10:
        return {"mask": np.zeros((h,w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}
    y1 = int(h*0.18); y2 = int(h*0.82); x1 = int(w*0.18); x2 = int(w*0.82)
    core = gray[y1:y2, x1:x2]
    if core.size == 0:
        return {"mask": np.zeros((h,w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}
    threshold = np.percentile(core, 18)
    raw_mask = (gray <= threshold).astype(np.uint8)
    central_mask = np.zeros_like(raw_mask); central_mask[y1:y2, x1:x2] = 1
    raw_mask = raw_mask * central_mask
    ys, xs = np.where(raw_mask > 0)
    if len(xs) == 0:
        return {"mask": np.zeros((h,w), dtype=np.uint8), "overlay": eye_rgb, "area": 0, "center": None, "confidence": 0.0}
    cx = int(np.mean(xs)); cy = int(np.mean(ys))
    dist = np.sqrt((xs-cx)**2 + (ys-cy)**2)
    keep = dist <= max(6, min(h,w)*0.18)
    xs2 = xs[keep]; ys2 = ys[keep]
    mask = np.zeros_like(raw_mask, dtype=np.uint8); mask[ys2, xs2] = 1
    area = int(mask.sum())
    overlay = eye_rgb.copy(); overlay[mask > 0] = [0,255,0]
    darkness = float(np.mean(gray[mask > 0])) if area > 0 else 255.0
    global_mean = float(np.mean(gray))
    confidence = 0.0
    if area > 20: confidence = max(0.0, min(1.0, (global_mean - darkness) / 90.0))
    return {"mask": mask, "overlay": overlay, "area": area, "center": (cx,cy) if area > 0 else None, "confidence": confidence}

def reflection_direction(offset_x, offset_y, offset_norm):
    if offset_x is None or offset_y is None or offset_norm is None: return "riflesso poco utile"
    if offset_norm < 0.12: return "riflesso centrale"
    vertical = ""; horizontal = ""
    if offset_y < -2: vertical = "superiore"
    elif offset_y > 2: vertical = "inferiore"
    if offset_x < -2: horizontal = "nasale"
    elif offset_x > 2: horizontal = "temporale"
    if vertical and horizontal: return f"riflesso {vertical}-{horizontal}"
    if vertical: return f"riflesso {vertical}"
    if horizontal: return f"riflesso {horizontal}"
    return "riflesso decentrato lieve" if offset_norm < 0.30 else "riflesso molto decentrato"

def detect_bright_spot_in_pupil(eye_rgb, mask):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2); valid = mask > 0
    if np.sum(valid) == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": eye_rgb, "reflection_score": 0.0, "intensity_ratio": 0.0}
    ys, xs = np.where(valid); pupil_vals = gray[valid]
    if pupil_vals.size == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": eye_rgb, "reflection_score": 0.0, "intensity_ratio": 0.0}
    pupil_mean = float(np.mean(pupil_vals)); thr = np.percentile(pupil_vals, 92)
    bright_mask = ((gray >= thr) & valid); bys, bxs = np.where(bright_mask)
    overlay = eye_rgb.copy()
    if len(bxs) == 0:
        return {"spot_center": None, "spot_intensity": 0.0, "spot_pixels": 0, "offset_x": None, "offset_y": None, "offset_norm": None, "label": "riflesso poco utile", "overlay": overlay, "reflection_score": 0.0, "intensity_ratio": 0.0}
    sx = float(np.mean(bxs)); sy = float(np.mean(bys)); spot_intensity = float(np.mean(gray[bright_mask])); spot_pixels = int(np.sum(bright_mask))
    cy = float(np.mean(ys)); cx = float(np.mean(xs))
    pupil_w = max(1.0, float(xs.max() - xs.min())); pupil_h = max(1.0, float(ys.max() - ys.min()))
    offset_x = float(sx - cx); offset_y = float(sy - cy)
    offset_norm = float(np.sqrt((offset_x / pupil_w) ** 2 + (offset_y / pupil_h) ** 2))
    label = reflection_direction(offset_x, offset_y, offset_norm)
    intensity_ratio = float(spot_intensity / max(1.0, pupil_mean)); size_ratio = float(spot_pixels / max(1, np.sum(valid)))
    reflection_score = 0.0
    reflection_score += min(40.0, max(0.0, (intensity_ratio - 1.0) * 40.0))
    reflection_score += min(30.0, max(0.0, size_ratio * 600.0))
    reflection_score += min(30.0, max(0.0, (1.0 - min(1.0, offset_norm)) * 30.0))
    reflection_score = round(reflection_score, 2)
    overlay[bright_mask] = [255,0,0]
    x0 = max(0, int(round(sx)) - 2); x1 = min(overlay.shape[1], int(round(sx)) + 3)
    y0 = max(0, int(round(sy)) - 2); y1 = min(overlay.shape[0], int(round(sy)) + 3)
    overlay[y0:y1, x0:x1] = [255,255,0]
    return {"spot_center": (float(sx), float(sy)), "spot_intensity": spot_intensity, "spot_pixels": spot_pixels, "offset_x": offset_x, "offset_y": offset_y, "offset_norm": offset_norm, "label": label, "overlay": overlay, "reflection_score": reflection_score, "intensity_ratio": round(intensity_ratio,3)}

def compute_gradients(eye_rgb, mask):
    gray = np.mean(eye_rgb.astype(np.float32), axis=2); valid = mask > 0
    if np.sum(valid) == 0: return {"mean_intensity": 0.0, "horizontal_gradient": 0.0, "vertical_gradient": 0.0}
    ys, xs = np.where(valid); x_min, x_max = xs.min(), xs.max(); y_min, y_max = ys.min(), ys.max()
    pupil = gray[y_min:y_max+1, x_min:x_max+1]; pupil_mask = valid[y_min:y_max+1, x_min:x_max+1]
    values = pupil[pupil_mask]; mean_intensity = float(np.mean(values)) if values.size else 0.0
    h, w = pupil.shape; mid_x = max(1, w // 2); mid_y = max(1, h // 2)
    left_vals = pupil[:, :mid_x][pupil_mask[:, :mid_x]]; right_vals = pupil[:, mid_x:][pupil_mask[:, mid_x:]]
    top_vals = pupil[:mid_y, :][pupil_mask[:mid_y, :]]; bottom_vals = pupil[mid_y:, :][pupil_mask[mid_y:, :]]
    l_mean = float(np.mean(left_vals)) if left_vals.size else 0.0; r_mean = float(np.mean(right_vals)) if right_vals.size else 0.0
    t_mean = float(np.mean(top_vals)) if top_vals.size else 0.0; b_mean = float(np.mean(bottom_vals)) if bottom_vals.size else 0.0
    return {"mean_intensity": mean_intensity, "horizontal_gradient": r_mean - l_mean, "vertical_gradient": b_mean - t_mean}

def refractive_hypothesis(reflection_score, offset_norm, horizontal_gradient, vertical_gradient):
    if reflection_score >= 62 and offset_norm is not None and offset_norm < 0.10 and abs(horizontal_gradient) < 6 and abs(vertical_gradient) < 6:
        return "riflesso abbastanza simmetrico / neutro preliminare"
    if horizontal_gradient > 10 or vertical_gradient > 10:
        return "possibile componente ipermetropica / decentrata da verificare"
    if horizontal_gradient < -10 or vertical_gradient < -10:
        return "possibile componente miopica / decentrata da verificare"
    return "pattern intermedio: utile confronto con refrazione clinica"

def analyze_eye(label, eye_rgb):
    if eye_rgb is None or eye_rgb.size == 0:
        return {"ok": False, "eye_rgb": None, "overlay": None, "area": 0, "confidence": 0.0, "message": f"{label}: ROI non disponibile", "pupil_center": None, "bright_spot": None, "features": None, "refractive_hypothesis": "non interpretabile"}
    seg = segment_pupil_numpy(eye_rgb); bright = detect_bright_spot_in_pupil(eye_rgb, seg["mask"]); feats = compute_gradients(eye_rgb, seg["mask"])
    useful_reflex = seg["area"] > 40 and seg["confidence"] >= 0.18 and bright["spot_center"] is not None and bright["spot_pixels"] > 5
    msg = bright["label"] if useful_reflex else "riflesso poco utile"
    hypo = refractive_hypothesis(bright["reflection_score"], bright["offset_norm"], feats["horizontal_gradient"], feats["vertical_gradient"]) if useful_reflex else "non interpretabile"
    return {"ok": True, "eye_rgb": eye_rgb, "overlay": bright["overlay"], "area": seg["area"], "confidence": seg["confidence"], "message": msg, "pupil_center": seg["center"], "bright_spot": bright, "features": feats, "useful_reflex": useful_reflex, "refractive_hypothesis": hypo}

def analyze_image(img_rgb):
    det = detect_face_and_eyes(img_rgb)
    guide = guidance_feedback(img_rgb, det.get("left_box"), det.get("right_box"))
    left = analyze_eye("Occhio sinistro", det["left_eye"]); right = analyze_eye("Occhio destro", det["right_eye"])
    overlay_img = draw_guidance_overlay(img_rgb, det.get("left_box"), det.get("right_box"))
    delta_h = delta_v = delta_ref = None; symmetry = "non valutabile"
    if left.get("features") and right.get("features"):
        delta_h = abs(left["features"]["horizontal_gradient"] - right["features"]["horizontal_gradient"])
        delta_v = abs(left["features"]["vertical_gradient"] - right["features"]["vertical_gradient"])
        delta_ref = abs(left["bright_spot"]["reflection_score"] - right["bright_spot"]["reflection_score"])
        symmetry = "buona" if (delta_h < 8 and delta_v < 8 and delta_ref < 8) else "asimmetria da approfondire"
    return {"detection": det, "guidance": guide, "overlay_img": overlay_img, "left": left, "right": right, "comparison": {"delta_h": delta_h, "delta_v": delta_v, "delta_ref": delta_ref, "symmetry": symmetry}}
