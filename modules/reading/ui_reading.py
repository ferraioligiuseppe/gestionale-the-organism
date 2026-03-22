from __future__ import annotations

import streamlit as st

from .db_reading import ensure_reading_tables, get_stimuli, get_stimulus, save_stimulus
from .reading_engine import prepare_text
from .stimuli_manager import parse_json_file, parse_txt


def ui_reading(conn, paziente_id=None, paziente_label: str = ""):
    ensure_reading_tables(conn)

    st.title("📖 Lettura Standardizzata")
    if paziente_label:
        st.caption(f"Paziente selezionato: {paziente_label}")

    st.subheader("Carica nuovo stimolo")
    uploaded = st.file_uploader(
        "Carica file (.txt o .json)",
        type=["txt", "json"],
        key="reading_uploaded_stimulus",
    )

    parsed_data = None
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".txt"):
                text = uploaded.read().decode("utf-8")
                parsed_data = parse_txt(text)
            else:
                parsed_data = parse_json_file(uploaded)
            st.success("Stimolo letto correttamente.")
        except Exception as e:
            st.error(f"Errore lettura file: {e}")
            parsed_data = None

    with st.form("reading_save_stimulus_form"):
        title = st.text_input("Titolo stimolo", value=(parsed_data or {}).get("title", ""))
        category = st.text_input("Categoria", value=(parsed_data or {}).get("category", "trial_clinico"))
        language = st.text_input("Lingua", value=(parsed_data or {}).get("language", "it"))
        school_level = st.text_input("Livello scolastico", value=(parsed_data or {}).get("school_level", ""))

        submitted = st.form_submit_button("Salva stimolo")
        if submitted:
            if parsed_data is None:
                st.warning("Carica prima un file TXT o JSON.")
            else:
                payload = dict(parsed_data)
                payload["title"] = title
                payload["category"] = category
                payload["language"] = language
                payload["school_level"] = school_level
                try:
                    save_stimulus(conn, payload)
                    st.success("Stimolo salvato nel DB.")
                except Exception as e:
                    st.error(f"Errore salvataggio stimolo: {e}")

    st.markdown("---")
    st.subheader("Seleziona stimolo")

    stimuli = get_stimuli(conn)
    if not stimuli:
        st.info("Nessuno stimolo disponibile.")
        return

    labels = [s[1] for s in stimuli]
    label_to_id = {s[1]: s[0] for s in stimuli}
    selected_label = st.selectbox("Stimolo", labels, key="reading_selected_label")
    stimulus = get_stimulus(conn, label_to_id[selected_label])

    if not stimulus:
        st.warning("Stimolo non trovato.")
        return

    text = prepare_text(stimulus)

    st.subheader("Configurazione")
    reading_mode = st.radio("Modalità", ["silenziosa", "ad alta voce"], key="reading_mode")
    device = st.radio("Dispositivo", ["webcam", "tobii", "ibrido"], key="reading_device")
    font_size = st.slider("Dimensione font", 16, 40, 24, key="reading_font_size")
    line_spacing = st.slider("Spaziatura righe", 1.0, 2.5, 1.5, 0.1, key="reading_line_spacing")

    st.markdown("---")
    st.subheader("Stimolo paziente")
    safe_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )

    st.markdown(
        f'''
        <div style="
            font-size:{font_size}px;
            line-height:{line_spacing};
            background:white;
            color:black;
            padding:20px;
            border-radius:10px;
            border:1px solid #ddd;
        ">
        {safe_text}
        </div>
        ''',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Avvia sessione", key="reading_start_session"):
            st.session_state["reading_active"] = True
            st.success(f"Sessione avviata • modalità: {reading_mode} • dispositivo: {device}")
    with col2:
        if st.button("⏹️ Termina sessione", key="reading_stop_session"):
            st.session_state["reading_active"] = False
            st.success("Sessione terminata")
