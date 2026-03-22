import json
import streamlit as st
import streamlit.components.v1 as components

from modules.reading.dom_renderer import build_reading_html
from modules.reading.dom_bbox_bridge import get_dom_bboxes_js


def _build_bbox_component(rendered_html: str) -> str:
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
    </head>
    <body style="margin:0; padding:0; background:#f8fbf8;">
      {rendered_html}
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

    st.markdown("### Preview testo DOM")
    components.html(_build_bbox_component(rendered_html), height=700, scrolling=True)

    st.markdown("### Bounding Box Reali (DOM)")
    if st.button("Acquisisci bounding box reali"):
        data = get_dom_bboxes_js()

        if data:
            st.success(f"{len(data['bbox_items'])} parole rilevate")
            st.session_state["reading_dom_bbox"] = data
            st.json(data)

            st.download_button(
                "Scarica bbox JSON",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name=f"{stimulus_id}_bbox.json",
                mime="application/json",
            )
        else:
            st.error("Errore acquisizione DOM")

    if st.button("Mostra HTML generato"):
        st.code(rendered_html, language="html")
