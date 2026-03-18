from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from .webcam_browser_v3_embed import get_webcam_browser_v3_html


def ui_webcam_browser_v3(
    paziente_id: int | None = None,
    paziente_label: str | None = None,
    height: int = 1100,
) -> None:
    st.subheader("Webcam AI Browser V3")
    st.caption("Modulo browser-based integrato nel gestionale: volto, occhi, bocca, asse del capo, stima sguardo, export JSON.")

    with st.expander("Contesto sessione", expanded=True):
        st.write(f"**Paziente ID:** {paziente_id if paziente_id is not None else '-'}")
        st.write(f"**Paziente:** {paziente_label or '-'}")
        st.info(
            "Questa versione gira direttamente nel browser tramite componente HTML/JS. "
            "Non usa MediaPipe Python sul server, quindi evita i problemi di deploy cloud."
        )

    html = get_webcam_browser_v3_html(
        paziente_id=paziente_id,
        paziente_label=paziente_label,
    )
    components.html(html, height=height, scrolling=True)
