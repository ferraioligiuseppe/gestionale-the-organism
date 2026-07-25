# -*- coding: utf-8 -*-
"""PNEV Metronomo — esercizi ritmici, integrazione bilaterale, timing.
Stesso file usato sul gestionale e su pnev.it (un solo strumento, due canali)."""
import os
import streamlit as st
import streamlit.components.v1 as components

_CANDIDATI = [
    os.path.join("static", "pnev_metronomo", "index.html"),
    os.path.join(os.path.dirname(__file__), "..", "static", "pnev_metronomo", "index.html"),
]
# Copia pubblica su pnev.it (per pazienti e lavoro a casa)
URL_PUBBLICO = "https://www.pnev.it/wp-content/uploads/pnev-metronomo/index.html"


def _carica_html() -> str:
    for p in _CANDIDATI:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def render_pnev_metronomo() -> None:
    st.subheader("🥁 PNEV Metronomo")
    st.caption("Esercizi ritmici, integrazione bilaterale e timing. Alternanza destra/sinistra "
              "in cuffia, suddivisioni, tap tempo, timer di seduta e flash visivo.")

    st.markdown(
        f'<a href="{URL_PUBBLICO}" target="_blank" rel="noopener" '
        'style="display:inline-block;margin-bottom:12px;padding:10px 16px;border-radius:8px;'
        'background:#1D6B44;color:#fff;font-weight:bold;text-decoration:none;font-size:14px">'
        '🔗 Versione per il paziente (pnev.it) — da inviare per il lavoro a casa</a>',
        unsafe_allow_html=True)

    html = _carica_html()
    if html:
        components.html(html, height=820, scrolling=True)
    else:
        st.error("File metronomo non trovato: verifica che static/pnev_metronomo/index.html "
                "sia stato caricato su GitHub.")
