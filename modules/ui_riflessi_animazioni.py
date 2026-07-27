# -*- coding: utf-8 -*-
"""
modules/ui_riflessi_animazioni.py

Animazioni dei riflessi primitivi — 12 sequenze animate con segni e sintomi
della mancata integrazione.

Le animazioni sono ospitate su pnev.it (contenuto pubblico, come i giochi):
qui c'è l'elenco con l'apertura diretta, da usare durante la valutazione per
mostrare al paziente o al genitore cosa si sta cercando.

Le stesse pagine servono anche a PNEV Academy: stesso indirizzo, nessuna
duplicazione.
"""

import streamlit as st

BASE = "https://www.pnev.it/wp-content/uploads/riflessi/"

RIFLESSI = [
    ("moro.html",       "Riflesso di Moro",       "Allarme e soglia allo stress",      "2-4 mesi"),
    ("palmare.html",    "Riflesso Palmare",       "Presa della mano, scrittura",       "4-6 mesi"),
    ("plantare.html",   "Riflesso Plantare",      "Appoggio del piede, andatura",      "7-9 mesi"),
    ("ricerca.html",    "Riflesso di Ricerca",    "Rooting, orientamento orale",       "3-4 mesi"),
    ("suzione.html",    "Riflesso di Suzione",    "Suzione, deglutizione, linguaggio", "3-4 mesi"),
    ("atnr.html",       "ATNR",                   "Tonico asimmetrico del collo",      "6 mesi"),
    ("stnr.html",       "STNR",                   "Tonico simmetrico del collo",       "9-11 mesi"),
    ("tlr.html",        "TLR",                    "Tonico labirintico, postura",       "3½ anni"),
    ("galant.html",     "Riflesso di Galant",     "Fianco, irrequietezza da seduti",   "3-9 mesi"),
    ("landau.html",     "Riflesso di Landau",     "Estensione, tono posturale",        "3 anni"),
    ("paracadute.html", "Reazione di Paracadute", "Protezione, equilibrio",            "resta per la vita"),
    ("babkin.html",     "Riflesso di Babkin",     "Sincinesie mano-bocca",             "3-4 mesi"),
]


def _card(file, titolo, sottotitolo, eta):
    st.markdown(
        f'<div style="border:1px solid #dfe7e2;border-radius:11px;padding:13px 16px;'
        f'margin-bottom:9px;background:#fff">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">'
        f'<div><div style="font-weight:700;font-size:15px;color:#123c7a">{titolo}</div>'
        f'<div style="font-size:12.5px;color:#5a7a68;margin-top:2px">{sottotitolo}'
        f' · <span style="color:#8a988f">integrazione {eta}</span></div></div>'
        f'<a href="{BASE}{file}" target="_blank" rel="noopener" '
        f'style="background:#f07d1a;color:#fff;text-decoration:none;border-radius:999px;'
        f'padding:9px 18px;font-size:12px;font-weight:700;white-space:nowrap">'
        f'Apri animazione →</a>'
        f'</div></div>', unsafe_allow_html=True)


def render_riflessi_animazioni(mostra_indice=True):
    st.subheader("🧬 Animazioni dei riflessi primitivi")
    st.caption("Dodici sequenze animate con i segni della mancata integrazione. "
              "Aprile durante la valutazione per mostrare al paziente o al "
              "genitore cosa stai cercando.")

    if mostra_indice:
        st.markdown(
            f'<a href="{BASE}index.html" target="_blank" rel="noopener" '
            f'style="display:inline-block;margin-bottom:14px;padding:11px 20px;'
            f'border-radius:9px;background:#123c7a;color:#fff;font-weight:700;'
            f'text-decoration:none;font-size:14px">📖 Apri l\'indice completo</a>',
            unsafe_allow_html=True)

    for file, titolo, sotto, eta in RIFLESSI:
        _card(file, titolo, sotto, eta)

    st.caption("Le animazioni si aprono in una scheda nuova: puoi girare lo "
              "schermo verso il paziente senza perdere la valutazione in corso.")
