
from __future__ import annotations

from typing import Iterable

from PIL import Image, ImageDraw


DEFAULT_POINTS = [33, 133, 159, 145, 362, 263, 386, 374, 61, 291, 13, 14, 10, 152, 1]



def draw_landmarks_on_image(image: Image.Image, landmarks_px: dict[int, tuple[float, float]], point_ids: Iterable[int] | None = None) -> Image.Image:
    out = image.copy().convert("RGB")
    draw = ImageDraw.Draw(out)
    point_ids = list(point_ids or DEFAULT_POINTS)

    for idx in point_ids:
        if idx not in landmarks_px:
            continue
        x, y = landmarks_px[idx]
        r = 4
        draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 64, 64), width=2)
        draw.text((x + 6, y - 6), str(idx), fill=(32, 64, 255))

    return out
