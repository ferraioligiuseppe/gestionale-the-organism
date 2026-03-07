# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(
    page_title="The Organism – Gestionale Studio",
    layout="wide"
)

from app_core import main

if __name__ == "__main__":
    main()
