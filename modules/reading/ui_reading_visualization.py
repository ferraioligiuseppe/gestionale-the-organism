from __future__ import annotations

import json
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components

from .text_layout_utils import build_word_boxes_from_text
from .reading_tracking_engine import compute_advanced_reading_metrics
from .heatmap_utils import build_heatmap_points, build_word_highlight_map


def _build_visual_html(text: str, word_boxes, heatmap_points, word_map) -> str:
    visible_words = []
    idx = 0
    for token in text.splitlines():
        line_words = token.split()
        if not line_words:
            visible_words.append('<div class="line spacer"></div>')
            continue
        line_parts = []
        for w in line_words:
            stat = word_map.get(idx, {})
            hits = stat.get("hits", 0)
            dwell = stat.get("dwell_ms", 0.0)
            revisits = stat.get("revisits", 0)

            cls = "word"
            if hits == 0:
                cls += " skipped"
            elif revisits > 0:
                cls += " revisited"
            elif dwell >= 300:
                cls += " dwell-high"
            elif hits > 0:
                cls += " viewed"

            safe_word = html_lib.escape(w)
            tooltip = html_lib.escape(f"idx={idx} | hits={hits} | dwell_ms={round(dwell,1)} | revisits={revisits}")
            line_parts.append(f'<span class="{cls}" title="{tooltip}" data-idx="{idx}">{safe_word}</span>')
            idx += 1
        visible_words.append('<div class="line">' + " ".join(line_parts) + '</div>')

    payload = {"heatmap_points": heatmap_points}

    html = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
      <meta charset="UTF-8" />
      <style>
        body {{
          margin: 0;
          background: #f8fafc;
          font-family: Arial, Helvetica, sans-serif;
        }}
        .wrap {{
          position: relative;
          padding: 24px;
          background: white;
          border: 1px solid #dbeafe;
          border-radius: 14px;
          min-height: 520px;
          overflow: hidden;
        }}
        .text-layer {{
          position: relative;
          z-index: 2;
          font-size: 30px;
          line-height: 1.8;
          color: #111827;
        }}
        .line {{
          margin-bottom: 8px;
        }}
        .line.spacer {{
          height: 24px;
        }}
        .word {{
          padding: 2px 4px;
          border-radius: 6px;
          transition: background 0.2s ease;
          display: inline-block;
        }}
        .word.viewed {{
          background: rgba(59,130,246,0.16);
        }}
        .word.dwell-high {{
          background: rgba(245,158,11,0.28);
        }}
        .word.revisited {{
          background: rgba(239,68,68,0.24);
        }}
        .word.skipped {{
          background: rgba(148,163,184,0.12);
          border-bottom: 2px dashed rgba(100,116,139,0.6);
        }}
        canvas {{
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          z-index: 1;
          pointer-events: none;
        }}
        .legend {{
          margin-top: 12px;
          font-size: 12px;
          color: #475569;
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }}
        .tag {{
          padding: 4px 8px;
          border-radius: 999px;
          border: 1px solid #cbd5e1;
          background: #f8fafc;
        }}
      </style>
    </head>
    <body>
      <div class="wrap" id="wrap">
        <canvas id="heat"></canvas>
        <div class="text-layer">
          {''.join(visible_words)}
        </div>
      </div>
      <div class="legend">
        <span class="tag">Blu = parola vista</span>
        <span class="tag">Giallo = dwell alto</span>
        <span class="tag">Rosso = rivisitata</span>
        <span class="tag">Grigio tratteggiato = saltata</span>
      </div>

      <script>
        const DATA = {json.dumps(payload)};
        const wrap = document.getElementById("wrap");
        const canvas = document.getElementById("heat");
        const ctx = canvas.getContext("2d");

        function resize() {{
          const rect = wrap.getBoundingClientRect();
          canvas.width = rect.width;
          canvas.height = rect.height;
          drawHeatmap();
        }}

        function drawHeatmap() {{
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          const pts = DATA.heatmap_points || [];
          for (const p of pts) {{
            const x = p.x * canvas.width;
            const y = p.y * canvas.height;
            const r = 26;

            const grad = ctx.createRadialGradient(x, y, 4, x, y, r);
            grad.addColorStop(0, "rgba(239,68,68,0.28)");
            grad.addColorStop(0.5, "rgba(245,158,11,0.18)");
            grad.addColorStop(1, "rgba(245,158,11,0.0)");

            ctx.beginPath();
            ctx.fillStyle = grad;
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fill();
          }}
        }}

        window.addEventListener("resize", resize);
        resize();
      </script>
    </body>
    </html>
    """
    return html


def ui_reading_visualization(paziente_id=None, paziente_label: str = ""):
    st.markdown("---")
    st.subheader("Visualizzazione avanzata: heatmap + parole evidenziate")

    if paziente_label:
        st.caption(f"Paziente: {paziente_label}")

    text_input = st.text_area(
        "Testo di riferimento per visualizzazione",
        height=220,
        key="reading_visual_text_input",
    )

    uploaded_tobii = st.file_uploader(
        "Carica sessione Tobii JSON per visualizzazione",
        type=["json"],
        key="reading_visual_tobii_json",
    )

    if st.button("Genera visualizzazione avanzata", key="btn_generate_visual_reading"):
        if not text_input.strip():
            st.warning("Inserisci prima il testo.")
            return
        if uploaded_tobii is None:
            st.warning("Carica il JSON Tobii.")
            return

        try:
            tobii_payload = json.load(uploaded_tobii)
        except Exception as e:
            st.error(f"Errore lettura JSON Tobii: {e}")
            return

        raw_samples = tobii_payload.get("samples", []) or []
        word_boxes = build_word_boxes_from_text(text_input)
        metrics = compute_advanced_reading_metrics(raw_samples, word_boxes)

        heatmap_points = build_heatmap_points(metrics.get("mapped_points", []))
        word_map = build_word_highlight_map(metrics.get("word_stats", []))

        html = _build_visual_html(
            text=text_input,
            word_boxes=word_boxes,
            heatmap_points=heatmap_points,
            word_map=word_map,
        )

        st.write("Regressioni:", metrics.get("regressions_total"))
        st.write("Parole saltate:", metrics.get("skipped_words_total"))
        st.write("Parole rivisitate:", metrics.get("revisited_words_total"))
        st.write("Transizioni di riga:", metrics.get("line_transition_count"))

        components.html(html, height=760, scrolling=True)

        with st.expander("Parole ad alto dwell"):
            st.json(metrics.get("words_with_high_dwell", []))
