# -*- coding: utf-8 -*-
"""Anamnesi PNEV da compilare a casa (link pubblico dei questionari).

app_core cercava questo modulo per il questionario «ANAMNESI_PNEV», ma il
file non esisteva: il link inviato alle famiglie mostrava solo l'errore
«No module named modules.pnev.ui_anamnesi_pnev».

Usa gli STESSI campi dell'anamnesi unica del gestionale
(modules/anamnesi_unica.py): quello che la famiglia scrive a casa ha le
stesse chiavi di quello che si compila in studio.
"""
from __future__ import annotations

import streamlit as st

from modules.anamnesi_unica import GRUPPI, GRUPPI_FINALI, _widget, _righe
from modules.anamnesi_sviluppo import SEZIONI as SEZIONI_SVILUPPO


def _sezione(titolo, campi, salvati, px, out):
    with st.expander(titolo, expanded=False):
        cols = st.columns(2)
        i = 0
        for k, label, tipo, opts in campi:
            if tipo in ("area", "multi", "scala"):
                out[k] = _widget(label, tipo, opts, salvati.get(k), f"{px}_{k}")
                i = 0
                continue
            with cols[i % 2]:
                out[k] = _widget(label, tipo, opts, salvati.get(k), f"{px}_{k}")
            i += 1


def anamnesi_pnev_collect_ui(prefix: str = "pub_anampnev", existing: dict | None = None):
    """Disegna l'anamnesi. Ritorna (dati, sintesi_testo)."""
    existing = existing or {}
    pi_salv = existing.get("prima_infanzia") or {}
    sv_salv = existing.get("sviluppo") or {}

    st.caption("Apri una sezione alla volta e compila quello che ricordi: tutti i campi sono "
               "facoltativi. Se un dato non lo sai, lascialo vuoto. Alla fine premi «INVIA».")

    pi, sv = {}, {}
    for gruppo, sezioni in GRUPPI:
        st.markdown(f"**{gruppo}**")
        for titolo, campi in sezioni:
            _sezione(titolo, campi, pi_salv, prefix, pi)

    st.markdown("**Dopo i 2 anni**")
    for titolo, campi in SEZIONI_SVILUPPO:
        _sezione(titolo, campi, sv_salv, f"{prefix}_sv", sv)

    st.markdown("**Famiglia e motivo della visita**")
    for titolo, campi in GRUPPI_FINALI:
        _sezione(titolo, campi, pi_salv, prefix, pi)

    righe = _righe([s for _g, sez in GRUPPI for s in sez], pi)
    try:
        from modules.anamnesi_sviluppo import sintesi_anamnesi_sviluppo
        righe += sintesi_anamnesi_sviluppo(sv)
    except Exception:
        pass
    righe += _righe(GRUPPI_FINALI, pi)
    sintesi = "\n".join(r[2:] if r.startswith("- ") else r for r in righe)
    return {"prima_infanzia": pi, "sviluppo": sv, "origine": "compilata a casa"}, sintesi
