# -*- coding: utf-8 -*-
"""Filtro per età — il menu mostra solo ciò che ha senso per quel paziente.

PNEV copre tutto l'arco di vita, dal neonato con lo Screening 0-4 fino
all'anziano con PNEV Argento. Il menu però era identico per un bimbo di due
anni e per un over 65: toccava a te ricordare a memoria quali strumenti
fossero pertinenti, e intanto le voci inutili occupavano spazio e attenzione.

Qui stanno le regole. Una voce compare solo se l'età del paziente attivo
rientra nel suo intervallo; senza paziente selezionato si vede tutto.

Come modificare una regola: cambia i numeri qui sotto, niente altro. Le
voci non elencate non hanno vincoli e compaiono sempre.

L'operatore può comunque disattivare il filtro dalla barra laterale
("Mostra tutte le voci"): nessuno strumento è mai irraggiungibile.
"""
from __future__ import annotations

import datetime

import streamlit as st

# voce di menu → (età minima, età massima). None = nessun limite da quel lato.
REGOLE_ETA: dict[str, tuple[int | None, int | None]] = {
    # Screening: la fascia è nel nome, seguirla è il minimo
    "🧸 Screening 0-4 anni":            (None, 5),
    "🩺 Screening breve (15 min)":      (6, None),
    "🩺 Screening completo":            (6, None),

    # Apprendimenti: richiedono che il bambino sia scolarizzato
    "📚 DSA — Apprendimento":           (6, None),
    "📖 Lettura avanzata":              (6, None),
    "🧪 Apprendimento PNEV":            (5, None),
    "🔢 DEM interattivo":               (6, None),   # va letto a voce alta

    # Questionari tarati su adulti
    "🌐 WHODAS 2.0":                    (18, None),

    # Materiali per bambini
    "🕹️ PNEV Game Center":              (None, 16),
    "🎮 Esercizi Wordwall":             (None, 16),
    "🎬 Animazioni dei riflessi":       (None, 14),

    # Sport Vision: serve capire la consegna e reggere il ritmo
    "🏃 PNEV Sport Vision":             (8, None),
}

CHIAVE_BYPASS = "menu_mostra_tutto"


def eta_paziente_attivo() -> int | None:
    """Età in anni compiuti del paziente attivo, o None se non ricavabile."""
    try:
        from .paziente_attivo import paziente_attivo_record
        rec = paziente_attivo_record()
    except Exception:
        return None
    if not isinstance(rec, dict):
        return None

    dn = None
    for chiave in ("data_nascita", "Data_nascita", "DataNascita", "data_di_nascita"):
        if rec.get(chiave):
            dn = rec[chiave]
            break
    if dn is None:
        return None

    if isinstance(dn, str):
        try:
            dn = datetime.date.fromisoformat(dn[:10])
        except Exception:
            return None
    if hasattr(dn, "date") and not isinstance(dn, datetime.date):
        dn = dn.date()
    if not isinstance(dn, datetime.date):
        return None

    oggi = datetime.date.today()
    anni = oggi.year - dn.year - ((oggi.month, oggi.day) < (dn.month, dn.day))
    return anni if 0 <= anni <= 120 else None


def voce_pertinente(voce: str, eta: int | None) -> bool:
    if eta is None:
        return True
    minimo, massimo = REGOLE_ETA.get(voce, (None, None))
    if minimo is not None and eta < minimo:
        return False
    if massimo is not None and eta > massimo:
        return False
    return True


def filtra_per_eta(voci: list[str], eta: int | None) -> list[str]:
    if eta is None or st.session_state.get(CHIAVE_BYPASS):
        return voci
    return [v for v in voci if voce_pertinente(v, eta)]


def _conta_nascoste(eta: int | None) -> int:
    if eta is None:
        return 0
    return sum(1 for v in REGOLE_ETA if not voce_pertinente(v, eta))


def interruttore_laterale(eta: int | None) -> None:
    """Riga in fondo al menu: dice quante voci sono nascoste e perché,
    e permette di rivederle tutte. Senza questa riga il filtro sarebbe
    una sparizione silenziosa — e una voce che sparisce senza spiegazione
    fa dubitare del programma, non dell'età."""
    if eta is None:
        return
    nascoste = _conta_nascoste(eta)
    if not nascoste and not st.session_state.get(CHIAVE_BYPASS):
        return

    st.sidebar.markdown("---")
    if st.session_state.get(CHIAVE_BYPASS):
        st.sidebar.caption("Filtro per età disattivato — vedi tutte le voci.")
        if st.sidebar.button("🎯 Mostra solo ciò che serve a questa età",
                              key="menu_riattiva_filtro", use_container_width=True):
            st.session_state[CHIAVE_BYPASS] = False
            st.rerun()
    else:
        st.sidebar.caption(
            f"Paziente di {eta} anni: {nascoste} voci non pertinenti sono nascoste.")
        if st.sidebar.button("👁️ Mostra tutte le voci", key="menu_mostra_tutto_btn",
                              use_container_width=True):
            st.session_state[CHIAVE_BYPASS] = True
            st.rerun()
