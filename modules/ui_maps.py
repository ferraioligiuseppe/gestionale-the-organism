# -*- coding: utf-8 -*-
"""
MAPS — Stimolazione uditiva adattiva (motore browser).

Sostituisce il vecchio motore di stimolazione lato server.
Il file del motore vero e proprio è assets/maps.html; qui lo carichiamo
e lo mostriamo dentro la pagina Streamlit con components.html.
"""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components


def ui_maps():
    st.header("🎧 MAPS — Stimolazione uditiva adattiva")
    st.caption(
        "Music · Adapted · Psychacustic · System — "
        "due bascule, tornante che salta, transcranico, binaurale, parto sonoro, fase attiva. "
        "Ascolto in cuffia stereo."
    )

    # Il motore MAPS sta in assets/maps.html (alla radice del progetto).
    html_path = Path(__file__).resolve().parent.parent / "assets" / "maps.html"

    if not html_path.exists():
        st.error(f"File MAPS non trovato: {html_path}")
        st.info("Carica assets/maps.html nel repository, poi ricarica la pagina.")
        return

    html = html_path.read_text(encoding="utf-8")
    components.html(html, height=1700, scrolling=True)
