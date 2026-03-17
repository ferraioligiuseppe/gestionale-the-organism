
from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

FACE_OUTLINE = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]
MOUTH_RING = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291]
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [263, 387, 385, 362, 380, 373]


def _draw_polyline(draw: ImageDraw.ImageDraw, points: dict[int, tuple[float, float]], indexes: list[int], color: str, closed: bool = False, width: int = 2):
    coords = [points[i] for i in indexes if i in points]
    if len(coords) < 2:
        return
    if closed:
        coords = coords + [coords[0]]
    draw.line(coords, fill=color, width=width)


def draw_face_analysis_overlay(image: Image.Image, points: dict[int, tuple[float, float]], metrics: dict[str, Any] | None = None) -> bytes:
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)

    _draw_polyline(draw, points, FACE_OUTLINE, "#00FF88", closed=True, width=2)
    _draw_polyline(draw, points, LEFT_EYE, "#00B7FF", closed=True, width=2)
    _draw_polyline(draw, points, RIGHT_EYE, "#00B7FF", closed=True, width=2)
    _draw_polyline(draw, points, MOUTH_RING, "#FF7A00", closed=True, width=2)

    for idx in LEFT_IRIS + RIGHT_IRIS:
        if idx in points:
            x, y = points[idx]
            r = 2
            draw.ellipse((x-r, y-r, x+r, y+r), fill="#FFD400")

    for key in ("left_iris_center", "right_iris_center"):
        center = (metrics or {}).get(key)
        if center:
            x, y = center
            r = 5
            draw.ellipse((x-r, y-r, x+r, y+r), outline="#FF0055", width=2)

    if 10 in points and 152 in points:
        draw.line([points[10], points[152]], fill="#FFFFFF", width=2)

    text_y = 12
    text_lines = []
    if metrics:
        text_lines.append(f"Gaze: {metrics.get('gaze_direction_label', '-')}")
        text_lines.append(f"Head tilt: {metrics.get('head_tilt_deg', '-')}")
        text_lines.append(f"Oral: {metrics.get('oral_state', '-')}")
        text_lines.append(f"Asym: {metrics.get('palpebral_asymmetry', '-')}")
    for line in text_lines:
        draw.text((12, text_y), line, fill="#FFFFFF")
        text_y += 16

    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
