# -*- coding: utf-8 -*-
"""Protocollo di valutazione — versione app HTML (import dal file preparato
con un altro assistente). Impaginazione A4 fedele al PDF, calcolatori con
indici automatici (PCC, %SS, ecc.), export/import JSON, stampa diretta.

Limiti da sapere:
- Il salvataggio "Salva"/"Riapri" della app usa il localStorage del BROWSER,
  non il database dei pazienti: è legato al dispositivo/browser usato in
  quel momento, non al paziente nel gestionale. Per conservarlo nel
  fascicolo del paziente, usa "Esporta" (scarica un file .json) e poi carica
  quel file in un secondo momento con "Importa" — anche da un altro
  dispositivo.
- Il bottone "Bozza di sintesi assistita" chiama l'API Anthropic
  DIRETTAMENTE dal browser con una chiave API incollata dall'utente: la
  chiave resta solo nella sessione del browser (si cancella chiudendo la
  scheda) e non passa dal gestionale. Se preferite non inserire chiavi API
  personali qui, usate invece "Genera relazione" nel modulo Screening o nel
  Protocollo di valutazione (tabelle), che usa l'AI già configurata nel
  gestionale.
"""
from __future__ import annotations
import os
import streamlit as st
import streamlit.components.v1 as components

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static_protocollo",
                          "PNEV_protocollo_app_MASTER.html")


def render_protocollo_pdf_app(conn=None, paz_id=None, paziente=None) -> None:
    st.header("📋 Protocollo di valutazione — app stampabile")
    st.caption("Versione a impaginazione A4 fedele al documento, con calcolatori automatici "
               "(PCC, %SS, indici) e stampa diretta.")
    st.warning("⚠️ Salvataggio: usa **Esporta** per scaricare i dati come file, e **Importa** per "
               "riaprirli — così restano legati al paziente indipendentemente dal browser usato. "
               "\"Salva\"/\"Riapri\" nella barra della app usano solo la memoria di questo browser.")

    try:
        with open(_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        st.error(f"File del protocollo non trovato: {e}")
        return

    components.html(html, height=1400, scrolling=True)
