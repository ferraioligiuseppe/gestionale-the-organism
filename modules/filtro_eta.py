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
    "🩺 Screening breve (20 min)":      (None, 16),   # cinque fasce, dalla nascita ai 16 anni
    "🧑 Screening adulti — funzionale":  (17, None),   # anche over 65
    "🧠 Screening adulti — neurologico": (17, None),
    "🧑 Valutazione adulti — funzionale completa": (17, None),
    "🧠 Valutazione adulti — neurologica completa": (17, None),
    "🩺 Screening completo":            (6, None),

    # Apprendimenti: richiedono che il bambino sia scolarizzato
    "📚 DSA — Apprendimento":           (6, None),
    "📖 Lettura avanzata":              (6, None),
    "🔢 DEM interattivo":               (6, None),   # va letto a voce alta

    # Questionari tarati su adulti
    "🌐 WHODAS 2.0":                    (18, None),

    # Materiali per bambini
    "🕹️ PNEV Game Center":              (None, 16),
    "🎮 Esercizi Wordwall":             (None, 16),
    "🎬 Animazioni dei riflessi":       (None, 14),

    # Sport Vision: serve capire la consegna e reggere il ritmo
    "🏃 PNEV Sport Vision":             (8, None),

    # Visiva: test con norme per l'età evolutiva
    "👁️ Getman (manipolazione visiva)":  (None, 14),
    "👁️ Groffman (visual tracing)":      (7, None),

    # Bambini scolarizzati / età evolutiva
    "✍️ Giochiamo imparando (prove touch)": (None, 12),
    "🔤 MAPS-Read":                     (6, None),
    "📚 Strumenti open":                (6, None),
    "🤸 Psicomotricità funzionale":      (None, 12),
    "🔤 Impostazione fonemi":           (None, 12),
}

# ── Fasce d'età e percorso di valutazione consigliato ──────────────────
# Il percorso compare in cima alle schermate di valutazione (pulsanti
# 1 · … 2 · …) e guida il «Passo successivo» in fondo alla pagina.
# Ogni passo: (nome breve, area del menu, voce del menu, età minima).

def fascia_eta(eta: int | None) -> str | None:
    if eta is None:
        return None
    if eta <= 4:
        return "0-4"
    if eta <= 16:
        return "bambino"
    if eta <= 64:
        return "adulto"
    return "over65"


NOME_FASCIA = {"0-4": "0–4 anni", "bambino": "5–16 anni",
               "adulto": "17–64 anni", "over65": "over 65"}


def percorso_valutazione(eta: int | None) -> list[tuple[str, str, str]]:
    """[(nome breve, area, voce)] del percorso consigliato per l'età."""
    from .app_menu import AREA_PNEV, AREA_SCREENING
    A = "👥 Pazienti"
    diagnosi = ("Diagnosi", A, "📝 Diagnosi assistita")
    neuro = ("Neuro-evolutivo", AREA_PNEV, "🧬 Profilo Neuro-Evolutivo")
    visiva = ("Visiva", AREA_PNEV, "👁️ Valutazione visuo-percettiva")
    uditiva = ("Uditiva", AREA_PNEV, "📊 Audiometria funzionale")
    anamnesi = ("Anamnesi", AREA_PNEV, "📋 Anamnesi PNEV")
    fascia = fascia_eta(eta)
    if fascia == "0-4":
        return [anamnesi, ("Screening 0-4", AREA_SCREENING, "🧸 Screening 0-4 anni"),
                neuro, ("Screening uditivo", AREA_SCREENING, "🎧 Screening uditivo"), diagnosi]
    if fascia == "bambino":
        passi = [anamnesi, neuro, visiva, uditiva]
        if eta >= 6:
            passi.append(("Apprendimenti", AREA_PNEV, "📚 DSA — Apprendimento"))
        return passi + [diagnosi]
    if fascia in ("adulto", "over65"):
        return [("Screening adulti", AREA_SCREENING, "🧑 Screening adulti — funzionale"),
                neuro, visiva, uditiva, diagnosi]
    # età sconosciuta: percorso classico
    return [anamnesi, neuro, visiva, uditiva, diagnosi]


# ── Questionari per età ────────────────────────────────────────────────
# Codici dei questionari (link e cartacei). I cartacei aggiuntivi usano i
# prefissi B_ (bambini) e A_ (adulti). Quelli non elencati valgono per tutti.
QUESTIONARI_BAMBINI = {"INPPS", "MELILLO_BAMBINI", "FISHER", "VISIONE_BAMBINI"}
QUESTIONARI_ADULTI = {"INPPS_ADULTI", "MELILLO_ADULTI", "VISIONE_ADULTI"}


def questionario_pertinente(codice: str, eta: int | None) -> bool:
    if eta is None:
        return True
    adulto = eta >= 17
    if codice in QUESTIONARI_BAMBINI or codice.startswith("B_"):
        return not adulto
    if codice in QUESTIONARI_ADULTI or codice.startswith("A_"):
        return adulto
    return True


def eta_da_data(dn) -> int | None:
    if dn is None or dn == "":
        return None
    if isinstance(dn, str):
        try:
            dn = datetime.date.fromisoformat(dn[:10])
        except Exception:
            return None
    if isinstance(dn, datetime.datetime):
        dn = dn.date()
    if not isinstance(dn, datetime.date):
        return None
    oggi = datetime.date.today()
    anni = oggi.year - dn.year - ((oggi.month, oggi.day) < (dn.month, dn.day))
    return anni if 0 <= anni <= 120 else None


def eta_paziente(conn, paz_id) -> int | None:
    """Età di un paziente qualsiasi letta dal database."""
    if not paz_id:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT data_nascita FROM pazienti WHERE id=%s", (int(paz_id),))
        row = cur.fetchone()
        if not row:
            return None
        return eta_da_data(row["data_nascita"] if isinstance(row, dict) else row[0])
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None

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
