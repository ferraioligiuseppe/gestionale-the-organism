# -*- coding: utf-8 -*-
"""PNEV-Chart — generatori di schede stampabili per il Visual Training
(Hart chart, saccadi, scansione, inseguimenti, fusion, slap-tap, stereogrammi).
File statico servito dal repo; qui solo embed + link a schermo intero."""
import streamlit as st

# Servito da /app/static (Streamlit) — stessa logica di pnev_capture.
CHART_URL = "app/static/pnev_chart/index.html"


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
    st.markdown(
        f'<iframe src="{CHART_URL}" style="width:100%;height:900px;'
        'border:1px solid #dce5df;border-radius:12px"></iframe>',
        unsafe_allow_html=True)
