# -*- coding: utf-8 -*-
"""PNEV-Chart — generatori di schede stampabili per il Visual Training.
L'HTML completo è incorporato con components.html (renderizza sempre,
senza dipendere dal content-type dello static serving)."""
import os
import streamlit as st
import streamlit.components.v1 as components

# Percorso del file HTML (in static/pnev_chart/index.html nel repo)
_CANDIDATI = [
    os.path.join("static", "pnev_chart", "index.html"),
    os.path.join(os.path.dirname(__file__), "..", "static", "pnev_chart", "index.html"),
]
# Link diretto per apertura a schermo intero / stampa
CHART_URL = "app/static/pnev_chart/index.html"


def _carica_html() -> str:
    for p in _CANDIDATI:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def render_pnev_chart() -> None:
    st.subheader("📐 PNEV-Chart — Schede Visual Training")
    st.caption("Generatori di schede stampabili in A4 (scala 100%): Hart chart, saccadi, "
              "scansione, inseguimenti, fusion, slap-tap, stereogrammi. Ogni scheda è sempre nuova.")
    st.markdown(
        f'<a href="{CHART_URL}" target="_blank" rel="noopener" '
        'style="display:inline-block;margin-bottom:12px;padding:10px 16px;border-radius:8px;'
        'background:#1D6B44;color:#fff;font-weight:bold;text-decoration:none;'
        'font-size:14px">🖨️ Apri a schermo intero (per stampare)</a>',
        unsafe_allow_html=True)

    html = _carica_html()
    if html:
        components.html(html, height=900, scrolling=True)
    else:
        st.error("File PNEV-Chart non trovato. Verifica che static/pnev_chart/index.html "
                "sia stato caricato su GitHub.")
