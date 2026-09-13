# -*- coding: utf-8 -*-
"""Bottone riusabile "Apri/aggiorna nel secondo monitor": apre (o aggiorna,
se già aperta) una finestra separata con lo stimolo del test in caratteri
grandi su sfondo scuro — da spostare sul secondo monitor rivolto verso il
paziente, così vede lo stesso stimolo dell'operatore.

Uso in qualunque modulo:
    from .finestra_bambino import bottone_secondo_monitor
    bottone_secondo_monitor("<b>A</b>", key="nsuco_target")
"""
import streamlit as st
import streamlit.components.v1 as components


def bottone_secondo_monitor(html_inner: str, key: str, etichetta: str = "🖥️ Apri/aggiorna nel secondo monitor"):
    """Bottone che apre/aggiorna la finestra 'finestra_screening_bambino'
    (nome condiviso: tutti i test del gestionale riusano la stessa finestra,
    così non se ne accumulano tante aperte)."""
    if st.button(etichetta, key=f"win_{key}"):
        safe = (html_inner or "").replace("`", "'").replace("</", "<\\/")
        js = f"""<script>
        (function(){{
          var w = window.open('', 'finestra_screening_bambino');
          if (w) {{
            w.document.open();
            w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8">
            <title>The Organism · Schermo paziente</title><style>
            body{{margin:0;background:#0f1512;color:#fff;display:flex;align-items:center;
            justify-content:center;min-height:100vh;font-family:sans-serif;}}
            .c{{font-size:4.4vw;text-align:center;padding:40px;letter-spacing:.12em;
            line-height:1.5;font-weight:600;}}
            </style></head><body><div class="c">{safe}</div></body></html>`);
            w.document.close();
            w.focus();
          }} else {{
            alert('Il browser ha bloccato la finestra popup: consenti i popup per questo sito.');
          }}
        }})();
        </script>"""
        components.html(js, height=0, width=0)
        st.caption("Apri il popup una volta e spostalo sul secondo monitor: da qui in poi ogni "
                   "clic aggiorna la stessa finestra, senza aprirne altre.")
