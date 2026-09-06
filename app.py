# -*- coding: utf-8 -*-
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="The Organism – Gestionale Studio",
    layout="wide"
)

def load_css():
    css_path = Path(__file__).parent / "assets" / "ui.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS non trovato: {css_path}")

load_css()

from modules.app_core import main

if __name__ == "__main__":
    main()
