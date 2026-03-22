import json
from pathlib import Path

import streamlit as st

from modules.reading.dom_renderer import build_reading_html
from modules.reading.dom_bbox_bridge import get_dom_bboxes_js
from modules.reading.stimulus_library import (
    list_stimuli,
    load_text_content,
    render_library_manager,
)


def _select_source():
    st.markdown("### Sorgente stimolo")

    mode = st.radio(
        "Seleziona modalità",
        ["Testo libero", "Libreria stimoli"],
        horizontal=True,
        key="reading_dom_source_mode",
    )

    if mode == "Testo libero":
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
        return {
            "mode": mode,
            "stimulus_type": "text",
            "stimulus_id": "free_text",
            "title": "Testo libero",
            "text": text_input,
            "filename": None,
            "path": None,
        }

    items = list_stimuli()
    if not items:
        st.info("La libreria è vuota. Carica dei file nella scheda 'Gestione libreria'.")
        return {
            "mode": mode,
            "stimulus_type": "none",
            "stimulus_id": "empty_library",
            "title": "Libreria vuota",
            "text": "",
            "filename": None,
            "path": None,
        }

    labels = [f"{x['title']} | {x['type']} | {x['filename']}" for x in items]
    idx = st.selectbox(
        "Seleziona file",
        range(len(items)),
        format_func=lambda i: labels[i],
        key="reading_dom_library_idx",
    )
    selected = items[idx]

    result = {
        "mode": mode,
        "stimulus_type": selected.get("type", "none"),
        "stimulus_id": selected.get("id", "unknown_stimulus"),
        "title": selected.get("title", "Stimolo"),
        "text": "",
        "filename": selected.get("filename"),
        "path": selected.get("path"),
    }

    if result["stimulus_type"] == "text" and result["filename"]:
        result["text"] = load_text_content(result["filename"])

    return result


def _preview_non_text(stimulus):
    st.markdown("### Anteprima stimolo")

    path_value = stimulus.get("path")
    if not path_value:
        st.warning("Nessun percorso file disponibile per questo stimolo.")
        return

    fp = Path(path_value)
    if not fp.exists():
        st.error(f"File non trovato: {fp}")
        return

    if stimulus.get("stimulus_type") == "image":
        st.image(str(fp), caption=stimulus.get("filename") or fp.name, use_container_width=True)
        st.info("Le immagini possono essere usate come stimoli visivi, ma non per mapping parola-per-parola.")
        return

    if stimulus.get("stimulus_type") == "pdf":
        with open(fp, "rb") as f:
            st.download_button(
                "Scarica PDF",
                data=f.read(),
                file_name=fp.name,
                mime="application/pdf",
                key=f"download_pdf_{fp.name}",
            )
        st.info("Il PDF è presente in libreria. Per il tracking DOM parola-per-parola conviene usare TXT o JSON.")
        return

    st.warning("Tipo di stimolo non supportato per l'anteprima.")


def ui_reading_dom():
    st.subheader("Lettura Avanzata DOM")
    tab1, tab2 = st.tabs(["Stimolo e analisi", "Gestione libreria"])

    with tab2:
        render_library_manager()

    with tab1:
        stimulus = _select_source()

        col1, col2 = st.columns([2, 1])

        with col2:
            default_stimulus_id = stimulus.get("stimulus_id", "stim_reading_001")
            stimulus_id = st.text_input("Stimulus ID", value=default_stimulus_id)
            font_size_px = st.slider("Font size", 16, 48, 28)
            line_height = st.slider("Line height", 1.0, 2.5, 1.7, 0.1)
            letter_spacing_px = st.slider("Letter spacing", 0.0, 3.0, 0.2, 0.1)
            text_align = st.selectbox("Allineamento", ["left", "center", "justify"], index=0)

        with col1:
            st.markdown(f"**Stimolo selezionato:** {stimulus.get('title', '-')}")
            if stimulus.get("filename"):
                st.caption(stimulus["filename"])

            stimulus_type = stimulus.get("stimulus_type", "none")

            if stimulus_type == "text":
                rendered_html = build_reading_html(
                    text=stimulus.get("text", ""),
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
                acquire = st.button("Acquisisci bounding box reali", type="primary")

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

                if st.checkbox("Mostra HTML generato", value=False):
                    st.code(rendered_html, language="html")

            elif stimulus_type in ("pdf", "image"):
                _preview_non_text(stimulus)

            else:
                st.info("Seleziona un file dalla libreria oppure usa il testo libero.")
