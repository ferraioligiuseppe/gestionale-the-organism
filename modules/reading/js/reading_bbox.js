function collectReadingWordBoxes(rootSelector = "#reading-dom-text") {
  const root = document.querySelector(rootSelector);
  if (!root) return [];

  const rootRect = root.getBoundingClientRect();
  const nodes = Array.from(root.querySelectorAll(".reading-word"));

  return nodes.map((el) => {
    const r = el.getBoundingClientRect();

    return {
      stimulus_id: window.READING_STIMULUS_ID || null,
      token_id: el.dataset.tokenId || null,
      word_index: Number(el.dataset.wordIndex),
      line_index_declared: Number(el.dataset.lineIndexDeclared),
      token_type: el.dataset.tokenType || "word",
      word_text: (el.textContent || "").trim(),

      x: r.left,
      y: r.top,
      width: r.width,
      height: r.height,
      x_center: r.left + r.width / 2,
      y_center: r.top + r.height / 2,

      rel_x: r.left - rootRect.left,
      rel_y: r.top - rootRect.top,
      rel_x_center: (r.left - rootRect.left) + r.width / 2,
      rel_y_center: (r.top - rootRect.top) + r.height / 2,

      root_x: rootRect.left,
      root_y: rootRect.top,
      root_width: rootRect.width,
      root_height: rootRect.height
    };
  });
}


function inferVisualLines(bboxItems, yTolerance = 12) {
  const items = [...bboxItems].sort((a, b) => {
    if (Math.abs(a.rel_y - b.rel_y) > yTolerance) return a.rel_y - b.rel_y;
    return a.rel_x - b.rel_x;
  });

  let currentLine = 0;
  let currentY = null;

  for (const item of items) {
    if (currentY === null) {
      currentY = item.rel_y;
      item.visual_line_index = currentLine;
      continue;
    }

    if (Math.abs(item.rel_y - currentY) <= yTolerance) {
      item.visual_line_index = currentLine;
    } else {
      currentLine += 1;
      currentY = item.rel_y;
      item.visual_line_index = currentLine;
    }
  }

  return items;
}


function buildReadingDomPayload() {
  const raw = collectReadingWordBoxes("#reading-dom-text");
  const withLines = inferVisualLines(raw, 12);

  return {
    stimulus_id: window.READING_STIMULUS_ID || null,
    bbox_items: withLines,
    timestamp: Date.now()
  };
}
