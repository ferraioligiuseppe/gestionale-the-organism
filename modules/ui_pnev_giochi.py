# -*- coding: utf-8 -*-
"""PNEV · Segui la pallina — attenzione e inseguimento visivo (multiple object tracking).

Due versioni dello stesso gioco:
  A · i numeri compaiono solo all'inizio e alla fine: inseguimento visivo puro
  B · i numeri restano sempre visibili: il bambino si aiuta col numero

Stessi file usati sul gestionale e su pnev.it (come il metronomo): un solo
strumento, due canali. I file sono offuscati: il sorgente resta nell'archivio
privato del titolare.
"""
import os
import streamlit as st
import streamlit.components.v1 as components

_CARTELLA = "pnev_giochi"
URL_PUBBLICO = "https://www.pnev.it/wp-content/uploads/pnev_giochi/"

VERSIONI = {
    "A · inseguimento visivo puro": ("seguipallina-A.html",
        "I numeri compaiono solo all'inizio e alla fine."),
    "B · con l'aiuto dei numeri": ("seguipallina-B.html",
        "I numeri restano sempre visibili: più facile, utile per iniziare."),
    "C · Sport Vision": ("seguipallina-C.html",
        "Per atleti: velocità adattiva, 2–4 bersagli su 12–20, doppio compito, storico."),
}


def _carica(nome: str) -> str:
    for base in ("static", os.path.join(os.path.dirname(__file__), "..", "static")):
        try:
            with open(os.path.join(base, _CARTELLA, nome), "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def render_segui_pallina() -> None:
    st.subheader("🎯 Segui la pallina")
    st.caption("Attenzione e inseguimento visivo. All'inizio alcune palline sono rosse: si "
               "memorizzano, poi si mescolano, e alla fine si toccano quelle giuste.")

    scelta = st.radio("Versione", list(VERSIONI), horizontal=True, key="sp_versione")
    file, nota = VERSIONI[scelta]
    st.caption(nota)

    st.markdown(
        f'<a href="{URL_PUBBLICO}{file}" target="_blank" rel="noopener" '
        'style="display:inline-block;margin-bottom:12px;padding:10px 16px;border-radius:8px;'
        'background:#1D6B44;color:#fff;font-weight:bold;text-decoration:none;font-size:14px">'
        '🔗 Versione per il paziente (pnev.it) — da inviare per il lavoro a casa</a>',
        unsafe_allow_html=True)

    html = _carica(file)
    if not html:
        st.error(f"File non trovato: verifica che static/{_CARTELLA}/{file} sia su GitHub.")
        return
    # Il link «← Giochi» porta a index.html, che dentro il gestionale non c'è:
    # qui lo si nasconde, sul sito resta e riporta all'elenco dei giochi.
    html = html.replace("</head>",
        "<style>a[href='index.html']{display:none!important}</style></head>", 1)
    components.html(html, height=860, scrolling=True)
    st.caption("A fine partita usa «Copia risultati» e incollali nel diario della seduta.")
