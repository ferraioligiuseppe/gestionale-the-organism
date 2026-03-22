from __future__ import annotations

from typing import Any, Dict, List


def build_word_boxes_from_text(text: str) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    boxes: List[Dict[str, Any]] = []
    global_index = 0
    total_lines = len(lines)

    top_margin = 0.18
    usable_height = 0.62
    line_step = usable_height / max(total_lines, 1)

    for line_idx, line in enumerate(lines, start=1):
        words = line.split()
        if not words:
            continue

        left_margin = 0.08
        usable_width = 0.84
        word_slot = usable_width / max(len(words), 1)
        y_center = top_margin + (line_idx - 0.5) * line_step

        for word_idx, word in enumerate(words):
            x_center = left_margin + (word_idx + 0.5) * word_slot
            boxes.append({
                "index": global_index,
                "word": word,
                "line": line_idx,
                "x_center": x_center,
                "y_center": y_center,
                "width": word_slot,
                "height": line_step,
            })
            global_index += 1

    return boxes
