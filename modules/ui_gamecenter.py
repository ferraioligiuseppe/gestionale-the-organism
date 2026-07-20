# -*- coding: utf-8 -*-
"""PNEV Game Center — 11 giochi HTML5 (attenzione, memoria, occhi-mani,
linguaggio, lettura). Ospitati su pnev.it (contenuto pubblico, come i
questionari); qui solo l'embed + link diretto."""
import streamlit as st

GAME_CENTER_URL = "https://www.pnev.it/wp-content/uploads/giochi/index.html"


def render_gamecenter() -> None:
    st.subheader("🕹️ PNEV Game Center")
    st.caption("11 giochi gratuiti (attenzione, memoria, occhi-mani, linguaggio, lettura). "
              "Allenamento e sensibilizzazione — non sono test diagnostici.")
    st.markdown(
        f'<a href="{GAME_CENTER_URL}" target="_blank" rel="noopener" '
        'style="display:inline-block;margin-bottom:12px;padding:10px 16px;border-radius:8px;'
        'background:#1D6B44;color:#fff;font-weight:bold;text-decoration:none;'
        'font-size:14px">🔗 Apri a schermo intero (scheda nuova)</a>',
        unsafe_allow_html=True)
    st.markdown(
        f'<iframe src="{GAME_CENTER_URL}" style="width:100%;height:900px;'
        'border:1px solid #dce5df;border-radius:12px"></iframe>',
        unsafe_allow_html=True)
