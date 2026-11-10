# -*- coding: utf-8 -*-
"""Il percorso del paziente: a che punto siamo e qual e' il prossimo passo.

Perche' esiste
--------------
Il gestionale ha tante pagine ma nessuna strada: finita l'anamnesi si
tornava al menu senza sapere dove andare. Qui c'e' UNA sequenza, dalla
prima telefonata al controllo, e un solo bottone «Prossimo passo».

Le sei fasi
-----------
  1 Primo contatto   consenso, questionari a casa
  2 Prima visita     anamnesi (o screening adulti)
  3 Valutazione      i passi di filtro_eta.percorso_valutazione per l'eta'
  4 Diagnosi         diagnosi assistita, relazione clinica
  5 Terapia          programma PNEV
  6 Controllo        esiti e follow-up

Un passo risulta «fatto» quando il fascicolo (modules/fascicolo_paziente.py)
trova almeno una voce salvata nelle sue tabelle. I passi senza tabella
nota non hanno spunta e non bloccano il percorso.
"""
from __future__ import annotations

import streamlit as st

# voce di menu → tabelle che provano che il passo e' stato fatto (None = non si puo' sapere)
TABELLE_DEL_PASSO = {
    "🔒 Privacy & Consensi": ("consensi_privacy",),
    "📋 Questionari remoti": ("questionari_links", "questionari_arrivo"),
    "📋 Anamnesi PNEV": ("anamnesi_prima_infanzia", "anamnesi_sviluppo"),
    "🧑 Screening adulti — funzionale": None,
    "🧸 Screening 0-4 anni": ("screening_04",),
    "🎧 Screening uditivo": ("screening_uditivo_pnev", "screening_cuffie_pnev"),
    "🧬 Profilo Neuro-Evolutivo": ("inpp_valutazioni",),
    "👁️ Valutazione visuo-percettiva": ("valutazioni_visive",),
    "📊 Audiometria funzionale": ("audiometrie_tonali", "functional_audiograms"),
    "📚 DSA — Apprendimento": ("dsa_valutazioni",),
    "📝 Diagnosi assistita": ("diagnosi_assistita",),
    "📝 Relazione clinica": ("archivio_relazioni", "relazioni_cliniche"),
    "🧩 Programma PNEV": ("terapia_programma", "terapia_sedute", "pnev_casa", "tmr_programmi",
                          "vis_programmi", "piani_vt"),
    "📈 Esiti / Follow-up": ("esiti_pnev",),
}

VOCE_SCHEDA = "🏠 Dashboard"
AREA_SCHEDA = "👥 Pazienti"


def _area(voce, area=None):
    if area:
        return area
    try:
        from .fascicolo_paziente import _area_di
        return _area_di(voce)
    except Exception:
        return None


def fasi(conn, paz_id) -> list[dict]:
    """Le sei fasi con i loro passi: [{nome, passi: [{nome, area, voce, fatto}]}].
    fatto e' True, False oppure None (non verificabile)."""
    try:
        from .filtro_eta import eta_paziente_attivo, percorso_valutazione
        valut = list(percorso_valutazione(eta_paziente_attivo()))
    except Exception:
        valut = []
    try:
        from .fascicolo_paziente import riepilogo
        presenti = {r["tabella"] for r in riepilogo(conn, paz_id)}
    except Exception:
        presenti = set()

    def passo(nome, voce, area=None):
        tab = TABELLE_DEL_PASSO.get(voce)
        fatto = None if not tab else any(t in presenti for t in tab)
        return {"nome": nome, "area": _area(voce, area), "voce": voce, "fatto": fatto}

    # dal percorso per eta': il primo passo e' la prima visita, l'ultimo la diagnosi
    centro = [p for p in valut if p[2] != "📝 Diagnosi assistita"]
    prima = centro[:1] or [("Anamnesi", None, "📋 Anamnesi PNEV")]
    resto = centro[1:]

    out = [
        {"nome": "Primo contatto", "passi": [passo("Consenso", "🔒 Privacy & Consensi"),
                                             passo("Questionari a casa", "📋 Questionari remoti")]},
        {"nome": "Prima visita", "passi": [passo(n, v, a) for n, a, v in prima]},
        {"nome": "Valutazione", "passi": [passo(n, v, a) for n, a, v in resto]},
        {"nome": "Diagnosi", "passi": [passo("Diagnosi", "📝 Diagnosi assistita"),
                                       passo("Relazione", "📝 Relazione clinica")]},
        {"nome": "Terapia", "passi": [passo("Programma", "🧩 Programma PNEV")]},
        {"nome": "Controllo", "passi": [passo("Esiti e follow-up", "📈 Esiti / Follow-up")]},
    ]
    for f in out:
        f["passi"] = [p for p in f["passi"] if p["area"]]      # solo voci che esistono nel menu
        noti = [p["fatto"] for p in f["passi"] if p["fatto"] is not None]
        f["fatta"] = (all(noti) if noti else None)
    return [f for f in out if f["passi"]]


def _tutti(fs):
    return [p for f in fs for p in f["passi"]]


def prossimo(fs, dopo_voce=None):
    """Il primo passo non fatto. Con dopo_voce, il primo non fatto DOPO
    quella pagina; se dopo non ce ne sono, il primo non fatto in assoluto."""
    passi = _tutti(fs)
    da_fare = [p for p in passi if p["fatto"] is False]
    if dopo_voce:
        voci = [p["voce"] for p in passi]
        if dopo_voce in voci:
            i = voci.index(dopo_voce)
            for p in passi[i + 1:]:
                if p["fatto"] is False:
                    return p
            da_fare = [p for p in da_fare if p["voce"] != dopo_voce]
    return da_fare[0] if da_fare else None


def _vai(p, paz_id):
    st.session_state["goto_area"] = p["area"]
    st.session_state["goto_sotto"] = p["voce"]
    st.session_state["paziente_attivo_id"] = paz_id
    st.rerun()


def render_percorso(conn, paz_id, chiave="perc") -> None:
    """In cima alla scheda del paziente: le sei fasi e il bottone «Prossimo passo»."""
    if conn is None or not paz_id:
        return
    fs = fasi(conn, paz_id)
    if not fs:
        return
    prox = prossimo(fs)
    with st.container(border=True):
        st.markdown("**A che punto siamo**")
        cols = st.columns(len(fs))
        for i, f in enumerate(fs):
            attuale = bool(prox) and any(p is prox for p in f["passi"])
            segno = "✅" if f["fatta"] else ("▶️" if attuale else "⚪")
            righe = [f"{segno} **{i + 1} · {f['nome']}**"]
            for p in f["passi"]:
                s = "✓" if p["fatto"] else ("·" if p["fatto"] is None else "○")
                righe.append(f"<span style='font-size:.82rem;color:#55606e'>{s} {p['nome']}</span>")
            cols[i].markdown("<br>".join(righe), unsafe_allow_html=True)

        if prox:
            if st.button(f"▶ Prossimo passo: {prox['nome']}", key=f"{chiave}_prox",
                         type="primary", use_container_width=True):
                _vai(prox, paz_id)
        else:
            st.success("Tutti i passi verificabili del percorso sono stati fatti.")

        with st.expander("Vai a un altro passo", expanded=False):
            passi = _tutti(fs)
            cc = st.columns(4)
            for j, p in enumerate(passi):
                s = "✓ " if p["fatto"] else ""
                if cc[j % 4].button(f"{s}{p['nome']}", key=f"{chiave}_vai_{j}", use_container_width=True):
                    _vai(p, paz_id)
        st.caption("✓ fatto · ○ da fare · il punto (·) indica un passo che il gestionale non sa verificare da solo.")


def bottone_in_fondo(conn, sotto) -> None:
    """In fondo a ogni pagina del percorso: avanti al prossimo passo, o indietro alla scheda."""
    paz_id = st.session_state.get("paziente_attivo_id")
    if conn is None or not paz_id or not sotto or sotto == VOCE_SCHEDA:
        return
    fs = fasi(conn, paz_id)
    if sotto not in [p["voce"] for p in _tutti(fs)]:
        return
    prox = prossimo(fs, dopo_voce=sotto)
    st.markdown("---")
    a, b = st.columns([3, 1])
    if prox:
        if a.button(f"▶ Prossimo passo: {prox['nome']}", key="perc_fondo_prox",
                    type="primary", use_container_width=True):
            _vai(prox, paz_id)
    else:
        a.caption("Non ci sono altri passi da fare dopo questo.")
    if b.button("🏠 Scheda del paziente", key="perc_fondo_scheda", use_container_width=True):
        _vai({"area": AREA_SCHEDA, "voce": VOCE_SCHEDA}, paz_id)
