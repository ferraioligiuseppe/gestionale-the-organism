import json
import streamlit as st
import streamlit.components.v1 as components

from modules.reading.dom_renderer import build_reading_html


def _build_bbox_component(rendered_html: str, height: int = 700) -> str:
    """
    Incapsula HTML + JS in un unico componente Streamlit.
    Il JS misura i box e li invia al parent Streamlit.
    """
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body style="margin:0; padding:0; background:#f8fbf8;">
      {rendered_html}

      <script>
        function collectWordBoxes() {{
          const root = document.getElementById("reading-dom-text");
          if (!root) return [];

          const rootRect = root.getBoundingClientRect();
          const nodes = Array.from(root.querySelectorAll(".reading-word"));

          const items = nodes.map((el) => {{
            const r = el.getBoundingClientRect();

            return {{
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
              x_center: r.left + (r.width / 2),
              y_center: r.top + (r.height / 2),

              rel_x: r.left - rootRect.left,
              rel_y: r.top - rootRect.top,
              rel_x_center: (r.left - rootRect.left) + (r.width / 2),
              rel_y_center: (r.top - rootRect.top) + (r.height / 2),

              root_x: rootRect.left,
              root_y: rootRect.top,
              root_width: rootRect.width,
              root_height: rootRect.height
            }};
          }});

          return items;
        }}

        function postToStreamlit() {{
          const payload = {{
            bbox_items: collectWordBoxes(),
            stimulus_id: window.READING_STIMULUS_ID || null,
            timestamp: Date.now()
          }};

          const streamlitEvent = new CustomEvent("streamlit:setComponentValue", {{
            detail: payload
          }});
          window.parent.document.dispatchEvent(streamlitEvent);
        }}

        function safeInit() {{
          setTimeout(postToStreamlit, 300);
          setTimeout(postToStreamlit, 800);
          setTimeout(postToStreamlit, 1500);
        }}

        window.addEventListener("load", safeInit);
        window.addEventListener("resize", postToStreamlit);
      </script>
    </body>
    </html>
    """


def ui_reading_dom():
    st.subheader("Lettura Avanzata DOM")

    st.write("Render HTML parola per parola con raccolta bounding box reali del browser.")

    col1, col2 = st.columns([2, 1])

    with col1:
        default_text = (
            "Il bambino osserva la figura e poi inizia a leggere lentamente il testo.\n"
            "Durante la lettura si possono osservare fissazioni, regressioni e salti di riga.\n"
            "L'obiettivo è associare il gaze alle parole reali mostrate sullo schermo."
        )

        text_input = st.text_area(
            "Testo clinico / stimolo",
            value=default_text,
            height=220,
            key="reading_dom_text_input",
        )

    with col2:
        stimulus_id = st.text_input("Stimulus ID", value="stim_reading_001")
        font_size_px = st.slider("Font size", 16, 48, 28)
        line_height = st.slider("Line height", 1.0, 2.5, 1.7, 0.1)
        letter_spacing_px = st.slider("Letter spacing", 0.0, 3.0, 0.2, 0.1)
        text_align = st.selectbox("Allineamento", ["left", "center", "justify"], index=0)

    rendered_html = build_reading_html(
        text=text_input,
        stimulus_id=stimulus_id,
        font_size_px=font_size_px,
        line_height=line_height,
        letter_spacing_px=letter_spacing_px,
        text_align=text_align,
    )

    st.markdown("### Preview e raccolta box DOM")

    components.html(
        _build_bbox_component(rendered_html),
        height=700,
        scrolling=True,
    )

    st.info(
        "Questa prima versione renderizza il testo in DOM reale. "
        "Per ricevere i bounding box in Python serve un piccolo bridge JS↔Streamlit "
        "(custom component o streamlit-javascript)."
    )

    if st.button("Mostra HTML generato"):
        st.code(rendered_html, language="html")

    st.markdown("### Prossimo output atteso")
    st.code(
        json.dumps(
            {
                "stimulus_id": stimulus_id,
                "bbox_items": [
                    {
                        "token_id": "tok_0",
                        "word_index": 0,
                        "word_text": "Il",
                        "line_index_declared": 0,
                        "x": 120.4,
                        "y": 245.8,
                        "width": 18.2,
                        "height": 28.0,
                        "x_center": 129.5,
                        "y_center": 259.8,
                        "rel_x": 12.0,
                        "rel_y": 20.0,
                        "rel_x_center": 21.1,
                        "rel_y_center": 34.0,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        language="json",
    )
