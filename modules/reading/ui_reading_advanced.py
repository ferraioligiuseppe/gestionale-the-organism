from __future__ import annotations

import json
import streamlit as st

from .text_layout_utils import build_word_boxes_from_text
from .reading_tracking_engine import compute_advanced_reading_metrics


def ui_reading_advanced(paziente_id=None, paziente_label: str = ""):
    st.markdown("---")
    st.subheader("Analisi avanzata lettura: riga per riga / parola per parola")

    if paziente_label:
        st.caption(f"Paziente: {paziente_label}")

    text_input = st.text_area(
        "Testo di riferimento",
        height=220,
        key="reading_advanced_text_input",
        help="Inserisci qui il testo standardizzato usato nello stimolo paziente.",
    )

    uploaded_tobii = st.file_uploader(
        "Carica sessione Tobii JSON",
        type=["json"],
        key="reading_advanced_tobii_json",
    )

    if st.button("Genera mappa parole", key="btn_generate_word_boxes"):
        if not text_input.strip():
            st.warning("Inserisci prima il testo.")
        else:
            word_boxes = build_word_boxes_from_text(text_input)
            st.session_state["reading_word_boxes"] = word_boxes
            st.success(f"Mappa parole generata: {len(word_boxes)} parole.")
            st.json(word_boxes[:40])

    if st.button("Analizza sessione Tobii su testo", key="btn_analyze_tobii_on_text"):
        if not text_input.strip():
            st.warning("Inserisci il testo di riferimento.")
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

        st.session_state["reading_advanced_metrics"] = metrics

        st.success("Analisi avanzata completata.")
        st.write("Campioni validi:", metrics.get("samples_valid"))
        st.write("Durata (sec):", round(metrics.get("duration_sec", 0), 2))
        st.write("Regressioni:", metrics.get("regressions_total"))
        st.write("Parole saltate:", metrics.get("skipped_words_total"))
        st.write("Parole rivisitate:", metrics.get("revisited_words_total"))
        st.write("Transizioni di riga:", metrics.get("line_transition_count"))

        with st.expander("Statistiche per parola"):
            st.json(metrics.get("word_stats", []))

        with st.expander("Reading path"):
            st.json(metrics.get("reading_path", []))

        with st.expander("Mapped points"):
            st.json(metrics.get("mapped_points", [])[:300])
