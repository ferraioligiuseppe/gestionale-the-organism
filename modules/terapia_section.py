# -*- coding: utf-8 -*-
"""Sezione Terapia: contenitore dei protocolli terapeutici."""

import streamlit as st

from .slap_tap.ui_slap_tap import ui_slap_tap


def render_terapia_section(conn=None):
    st.title("🧠 Terapia")
    st.caption("Area dedicata ai protocolli terapeutici")

    modulo = st.radio(
        "Seleziona protocollo",
        ["SLAP TAP"],
        horizontal=True,
        key="terapia_protocollo",
    )

    if modulo == "SLAP TAP":
        ui_slap_tap(conn=conn)
