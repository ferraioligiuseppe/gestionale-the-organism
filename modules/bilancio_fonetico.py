# -*- coding: utf-8 -*-
"""Bilancio fonetico — repertorio dei fonemi dell'italiano.

Stava dentro il modulo della valutazione visuo-percettiva: funzionava, ma
la fonologia non c'entra con la visione, e chi cercava questa prova non
poteva immaginare di trovarla lì. Ora vive per conto suo ed è richiamata
da Logopedia (tab "Linguaggio/Fonologia"), che è il suo posto.

Uso:
    from .bilancio_fonetico import render_bilancio_fonetico
    esiti = render_bilancio_fonetico(f"logo_{paz_id}", salvato)
"""
from __future__ import annotations

import streamlit as st


_BILANCIO_FONETICO = {
    "Occlusivi": ["p", "b", "t", "d", "k", "g"],
    "Fricativi": ["f", "v", "s", "sc"],
    "Affricati": ["z", "ci", "gi"],
    "Nasali": ["m", "n", "gn"],
    "Liquidi": ["l", "gl", "vibrante r"],
}

_PAROLE_FONEMI = {
    "p": ["pane", "papà", "topo"], "b": ["barca", "bimbo", "sabbia"],
    "t": ["tavolo", "topo", "gatto"], "d": ["dado", "dente", "cadere"],
    "k": ["casa", "cane", "scuola"], "g": ["gatto", "gomma", "fungo"],
    "f": ["foglia", "farfalla", "telefono"], "v": ["vaso", "vela", "uva"],
    "s": ["sole", "sasso", "rosa"], "sc": ["scarpa", "pesce", "scimmia"],
    "z": ["zaino", "pizza", "zucchero"], "ci": ["ciao", "cioccolato", "faccia"],
    "gi": ["giallo", "giraffa", "formaggio"],
    "m": ["mano", "mamma", "gomma"], "n": ["naso", "nonna", "banana"], "gn": ["gnomo", "castagna", "bagno"],
    "l": ["luna", "latte", "palla"], "gl": ["aglio", "famiglia", "coniglio"], "vibrante r": ["rana", "remo", "carota"],
}


def render_bilancio_fonetico(pid_key: str, salvato: dict | None = None):
    """Bilancio fonetico — repertorio dei fonemi dell'italiano, raggruppati
    per categoria articolatoria, con esito presente/assente/distorto per
    ciascuno. Usato in Linguaggio per fotografare velocemente quali suoni
    il bambino produce correttamente."""
    salvato = salvato or {}
    st.caption("Per ogni fonema: chiedi al bambino di dire le parole elencate, poi indica l'esito.")
    esiti = {}
    for categoria, fonemi in _BILANCIO_FONETICO.items():
        st.markdown(f"**{categoria}**")
        cols = st.columns(len(fonemi))
        for i, fon in enumerate(fonemi):
            with cols[i]:
                parole = _PAROLE_FONEMI.get(fon, [])
                st.caption(f"**{fon}** — {', '.join(parole)}" if parole else f"**{fon}**")
                v = st.selectbox(" ", ["✅ Presente", "❌ Assente", "🔁 Distorto/sostituito"],
                                  index=["✅ Presente", "❌ Assente", "🔁 Distorto/sostituito"].index(
                                      salvato.get(fon, "✅ Presente")),
                                  key=f"bf_{pid_key}_{categoria}_{fon}", label_visibility="collapsed")
                esiti[fon] = v
    return esiti


def _NON_USATA_telebinocular_quick_test(pid, salvate: dict):
    # Spostata in ui_valutazione_visuo_percettiva.py, dove viene usata.
    # Questa copia resta inerte: rimuovila pure al prossimo giro di pulizia.
    """14 test Telebinocular (struttura reale dello strumento: percezione
    simultanea, foria lontano/vicino su scala graduata, identificazione
    lettere/forme/numeri per la soppressione) — con secondo monitor per
    mostrare lo stimolo al bambino. Stimoli originali (non le schede
    proprietarie Keystone/Bernell) per evitare qualunque problema di
    copyright, mantenendo lo stesso principio di misura."""
    try:
        from .finestra_bambino import bottone_secondo_monitor
    except Exception:
        bottone_secondo_monitor = None

    st.caption("🔴🔵 Richiede gli occhialini anaglifici rosso/ciano. 14 test, pochi secondi ciascuno. "
               "Stimoli originali dello studio (non le schede proprietarie dello strumento).")
    risposte = {}
    n_fuori_norma = 0
    for t in _TB_14:
        with st.expander(t["titolo"], expanded=False):
            st.caption(t["desc"])
            c1, c2 = st.columns([1, 1])
            with c1:
                if t["tipo"] == "foria":
                    html_stim = ("<div style='font-size:2.4rem'>┃</div>"
                                 "<div style='letter-spacing:.4em;font-size:1.6rem'>● ● ● ●</div>")
                elif t["tipo"] == "lettere":
                    html_stim = "<div style='font-size:3rem;letter-spacing:.3em'>L&nbsp;&nbsp;B&nbsp;&nbsp;T&nbsp;&nbsp;R</div>"
                elif t["tipo"] == "forme":
                    html_stim = "<div style='font-size:2.6rem;letter-spacing:.3em'>✚&nbsp;&nbsp;●&nbsp;&nbsp;✳&nbsp;&nbsp;■&nbsp;&nbsp;♡</div>"
                else:
                    html_stim = "<div style='font-size:2.6rem;letter-spacing:.3em'>32&nbsp;&nbsp;&nbsp;79&nbsp;&nbsp;&nbsp;23</div>"
                st.markdown(f"<div style='text-align:center;padding:10px'>{html_stim}</div>", unsafe_allow_html=True)
                if bottone_secondo_monitor:
                    bottone_secondo_monitor(html_stim, key=f"tb14_{pid}_{t['n']}")
            with c2:
                if t["tipo"] == "foria":
                    prec = salvate.get(f"t{t['n']}", "Nei limiti")
                    risp = st.select_slider("Esito", _TB_SCALA_FORIA,
                                             value=prec if prec in _TB_SCALA_FORIA else "Nei limiti",
                                             key=f"tb14q_{pid}_{t['n']}")
                    fuori = risp not in ("Nei limiti", "Ottimale")
                elif t["tipo"] in ("lettere", "forme"):
                    opzioni = ["Vede tutto (entrambi gli occhi)"] + t["extra_opzioni"] + ["Solo alcuni elementi"]
                    if not t["extra_opzioni"]:
                        opzioni = ["Vede tutto (entrambi gli occhi)", "Solo OS", "Solo OD", "Solo alcuni elementi"]
                    prec = salvate.get(f"t{t['n']}", opzioni[0])
                    risp = st.radio("Esito", opzioni, index=opzioni.index(prec) if prec in opzioni else 0,
                                    key=f"tb14q_{pid}_{t['n']}")
                    fuori = risp != opzioni[0]
                else:
                    opzioni = ["Tutti i numeri (fusione buona)", "Solo alcuni numeri", "Nessuno / soppressione"]
                    prec = salvate.get(f"t{t['n']}", opzioni[0])
                    risp = st.radio("Esito", opzioni, index=opzioni.index(prec) if prec in opzioni else 0,
                                    key=f"tb14q_{pid}_{t['n']}")
                    fuori = risp != opzioni[0]
                risposte[f"t{t['n']}"] = risp
                if fuori:
                    st.caption("🔴 Fuori norma")
                    n_fuori_norma += 1
                else:
                    st.caption("🟢 Nella norma")
    if n_fuori_norma:
        st.warning(f"{n_fuori_norma}/14 test fuori norma — coerente con un possibile deficit di integrazione binoculare.")
    else:
        st.success("14/14 test nella norma.")
    return risposte
