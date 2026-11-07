# -*- coding: utf-8 -*-
"""
modules/pei/fonti_icf.py — propone codici ICF-CY a partire dai dati che lo
studio ha già nei moduli del gestionale.

Ogni «fonte» è una funzione (conn, paz_id) -> list[proposta], dove
proposta = {"codice", "performance", "capacita", "note"} come le righe della
tabella icf_funzionamento di pei_core. Per aggiungere un modulo basta scrivere
una funzione e metterla in FONTI.

Le proposte sono sempre da confermare: si inseriscono solo i codici scelti,
e i codici già presenti nel documento non vengono toccati.

Studio The Organism - Dott. Giuseppe Ferraioli
"""
from __future__ import annotations

import streamlit as st

from ..pei_core import db as pei_db
from ..pei_core.icf import (CAMPO_FUNZIONAMENTO, QUALIFICATORI, aggiungi_righe, etichetta,
                            qualificatore_da_percentuale)
from ..pei_core.ui import azzera_widget
from .fonti_pnev import _esiste, _fmt, _righe, ultimo_profilo

# --------------------------------------------------------------------------
# 1. Profilo Neuro-Evolutivo PNEV (inpp_valutazioni)
#    percentuale di disfunzione della sezione -> qualificatore ICF
# --------------------------------------------------------------------------
SEZIONE_ICF = {
    "coordinazione_equilibrio": "b235",   # funzioni vestibolari (equilibrio)
    "schemi_sviluppo": "b147",            # funzioni psicomotorie
    "cerebellare": "b760",                # controllo del movimento volontario
    "disdiadococinesia": "b176",          # sequenza dei movimenti complessi
    "orientamento_propriocezione": "b260",  # propriocezione
    "riflessi": "b750",                   # riflesso motorio (riflessi primitivi)
    "oculomotori": "b215",                # motilità oculare
    "visuo_percettivi": "b156",           # funzioni percettive
}


def da_profilo_pnev(conn, paz_id) -> list[dict]:
    prof = ultimo_profilo(conn, paz_id)
    if not prof or not prof.get("riepilogo"):
        return []
    data = _fmt(prof.get("data_valutazione"))
    out = {}
    for sez_id, r in prof["riepilogo"].items():
        cod = SEZIONE_ICF.get(sez_id)
        if not cod or not isinstance(r, dict):
            continue
        perc = float(r.get("perc") or 0)
        nota = f"{r.get('label', sez_id)}: {perc:g}% di disfunzione (Profilo Neuro-Evolutivo PNEV del {data})"
        prec = out.get(cod)
        if prec is None or perc > prec["_perc"]:
            out[cod] = {"codice": etichetta(cod), "performance": qualificatore_da_percentuale(perc),
                        "capacita": "", "note": nota, "_perc": perc}
    return [{k: v for k, v in r.items() if k != "_perc"} for r in out.values()]


# --------------------------------------------------------------------------
# 2. Audiometria tonale (audiometrie_tonali): PTA dell'orecchio migliore
#    gradi OMS: <=25 dB 0 · 26-40 1 · 41-60 2 · 61-80 3 · >80 4
# --------------------------------------------------------------------------
def _grado_pta(db: float) -> str:
    i = 0 if db <= 25 else 1 if db <= 40 else 2 if db <= 60 else 3 if db <= 80 else 4
    return QUALIFICATORI[i]


def da_audiometria(conn, paz_id) -> list[dict]:
    if not _esiste(conn, "audiometrie_tonali"):
        return []
    r = _righe(conn, """SELECT pta_od, pta_os, creato_il FROM audiometrie_tonali
                        WHERE paziente_id=%s AND (pta_od IS NOT NULL OR pta_os IS NOT NULL)
                        ORDER BY creato_il DESC, id DESC LIMIT 1""", (int(paz_id),))
    if not r:
        return []
    od, os_ = r[0].get("pta_od"), r[0].get("pta_os")
    valori = [float(v) for v in (od, os_) if v is not None]
    migliore = min(valori)
    nota = (f"PTA OD {od if od is not None else '—'} dB, OS {os_ if os_ is not None else '—'} dB "
            f"(audiometria tonale del {_fmt(r[0].get('creato_il'))}); qualificatore sull'orecchio migliore. "
            f"Da confermare con esame audiometrico clinico.")
    return [{"codice": etichetta("b230"), "performance": _grado_pta(migliore), "capacita": "", "note": nota}]


FONTI = [
    ("Profilo Neuro-Evolutivo PNEV", da_profilo_pnev),
    ("Audiometria tonale", da_audiometria),
]


def proposte(conn, paz_id) -> list[tuple[str, dict]]:
    out = []
    for nome, f in FONTI:
        try:
            out += [(nome, p) for p in f(conn, paz_id)]
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    return out


# --------------------------------------------------------------------------
# Pannello Streamlit (da usare con pagina_pei(prima_del_modulo=...))
# --------------------------------------------------------------------------
def pannello(conn, paz_id, utente, tenant_id):
    def disegna(doc, pref):
        if doc.tipo not in ("PDF", "PEI", "PF", "RICF"):
            return
        with st.expander("🧩 Proposte ICF-CY dai moduli dello studio"):
            st.caption("Codici e qualificatori calcolati dalle valutazioni già fatte. Scegli quali inserire: "
                       "i codici già presenti nel documento non vengono toccati. Salva prima le modifiche in corso.")
            lista = proposte(conn, paz_id)
            if not lista:
                st.caption("Nessun dato utilizzabile nei moduli collegati (Profilo Neuro-Evolutivo, audiometria).")
                return
            scelte = []
            for i, (fonte, p) in enumerate(lista):
                q = p["performance"].split(" (")[0]
                if st.checkbox(f"**{p['codice']}** — {q}", value=True, key=f"{pref}_icfp_{i}",
                               help=f"{fonte}: {p['note']}"):
                    scelte.append(p)
                st.caption(f"{fonte} · {p['note']}")
            if st.button("Inserisci nel profilo ICF-CY", key=f"{pref}_icfp_go", disabled=not scelte):
                agg, salt = aggiungi_righe(doc.contenuto, CAMPO_FUNZIONAMENTO, scelte)
                if agg:
                    pei_db.salva_documento(conn, doc, "paziente", int(paz_id), utente, tenant_id)
                    azzera_widget(pref)
                    st.session_state[f"{pref}_icfp_msg"] = (
                        f"Inseriti {agg} codici" + (f", {salt} già presenti" if salt else "") + ".")
                    st.rerun()
                st.info("Tutti i codici scelti sono già nel documento.")
        msg = st.session_state.pop(f"{pref}_icfp_msg", None)
        if msg:
            st.success(msg)
    return disegna
