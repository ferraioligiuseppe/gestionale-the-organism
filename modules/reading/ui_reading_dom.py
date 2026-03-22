import json
import streamlit as st

from modules.reading.dom_renderer import build_reading_html
from modules.reading.dom_bbox_bridge import get_dom_bboxes_js
from modules.reading.test_loader import load_tests


def _get_text_from_source():
    st.markdown("### Sorgente stimolo")

    mode = st.radio(
        "Seleziona modalità",
        ["Testo libero", "Libreria test"],
        horizontal=True,
        key="reading_dom_source_mode",
    )

    if mode == "Libreria test":
        tests = load_tests()
        if not tests:
            st.warning("Nessun test disponibile nella libreria.")
            return ""

        labels = [f"{t.get('title', t.get('test_id', 'Test'))} · {t.get('category', '')}" for t in tests]
        idx = st.selectbox("Seleziona test", range(len(tests)), format_func=lambda i: labels[i], key="reading_dom_test_idx")
        selected_test = tests[idx]

        st.caption(
            f"Categoria: {selected_test.get('category', '-') } | "
            f"Difficoltà: {selected_test.get('difficulty', '-')}"
        )
        return selected_test.get("content", "")

    default_text = (
        "Il bambino osserva la figura e poi inizia a leggere lentamente il testo.\n"
        "Durante la lettura si possono osservare fissazioni, regressioni e salti di riga.\n"
        "L'obiettivo è associare il gaze alle parole reali mostrate sullo schermo."
    )
    return st.text_area(
        "Testo clinico / stimolo",
        value=default_text,
        height=220,
        key="reading_dom_text_input",
    )


def ui_reading_dom():
    st.subheader("Lettura Avanzata DOM")
    st.write("Render HTML parola per parola con raccolta bounding box reali del browser.")

    col1, col2 = st.columns([2, 1])

    with col1:
        text_input = _get_text_from_source()

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

    st.markdown("### Preview DOM reale")
    preview_wrap = f'''
    <div style="background:#f8fbf8;padding:16px;border-radius:12px;border:1px solid #d9e2d9;">
        {rendered_html}
    </div>
    '''
    st.markdown(preview_wrap, unsafe_allow_html=True)

    st.markdown("### Bounding Box reali (DOM)")
    st.caption("Il pulsante legge i box direttamente dal DOM della pagina Streamlit.")

    c1, c2 = st.columns([1, 1])
    with c1:
        acquire = st.button("Acquisisci bounding box reali", type="primary")
    with c2:
        show_html = st.checkbox("Mostra HTML generato", value=False)

    if acquire:
        data = get_dom_bboxes_js()

        if data and isinstance(data, dict) and data.get("ok"):
            st.success(f"{len(data.get('bbox_items', []))} token rilevati")
            st.session_state["reading_dom_bbox"] = data
            st.json(data)

            st.download_button(
                "Scarica JSON bbox",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name=f"{stimulus_id}_bbox.json",
                mime="application/json",
            )
        else:
            err = data.get("error", "Errore acquisizione DOM") if isinstance(data, dict) else "Errore acquisizione DOM"
            st.error(err)

    if show_html:
        st.code(rendered_html, language="html")
