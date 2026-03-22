import json
import streamlit as st

from modules.reading.dom_renderer import build_reading_html
from modules.reading.dom_bbox_bridge import get_dom_bboxes_js
from modules.reading.test_loader import load_tests


def ui_reading_dom():
    st.subheader("Lettura Avanzata DOM")

    st.warning("VERSIONE NUOVA ATTIVA")  # DEBUG

    mode = st.radio("Modalità", ["Testo libero", "Libreria test"])

    if mode == "Libreria test":
        tests = load_tests()
        titles = [t["title"] for t in tests]
        selected = st.selectbox("Seleziona test", titles)
        selected_test = next(t for t in tests if t["title"] == selected)
        text_input = selected_test["content"]
    else:
        text_input = st.text_area(
            "Testo",
            value="Il bambino legge lentamente il testo e osserva le parole.",
            height=200,
        )

    stimulus_id = st.text_input("Stimulus ID", "test_001")

    rendered_html = build_reading_html(text_input, stimulus_id)

    st.markdown("### TESTO RENDERIZZATO")

    # 🔥 QUESTA È LA RIGA GIUSTA
    st.markdown(rendered_html, unsafe_allow_html=True)

    st.markdown("### ACQUISIZIONE")

    if st.button("Acquisisci bounding box"):
        data = get_dom_bboxes_js()

        if data and isinstance(data, dict) and data.get("ok"):
            st.success(f"{len(data['bbox_items'])} parole trovate")
            st.json(data)
        else:
            st.error("Errore acquisizione DOM")
