"""
PNEV AI helper (STUB) for The Organism.

Goals:
- Provide a stable interface that can be upgraded later (OpenAI, local LLM, etc.)
- Work only with the *current* visual visit snapshot + current PNEV JSON
- Never write directly to DB: the app applies suggestions to Streamlit session_state keys

This is a SAFE stub:
- No external calls
- Deterministic, rule-based hints
"""

from __future__ import annotations

from typing import Any, Dict


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _get_visita(visita: Dict[str, Any], key: str, default: Any = "") -> Any:
    return visita.get(key, default) if isinstance(visita, dict) else default


def _num(v: Any) -> float | None:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


def _profile_from_notes(pnev: Dict[str, Any]) -> str:
    # quick heuristic based on sensory/arousal fields
    sens = (pnev or {}).get("sensoriale", {}) if isinstance(pnev, dict) else {}
    ar = sens.get("arousal", {}) if isinstance(sens, dict) else {}
    ar_prof = _s(ar.get("profilo"))
    if ar_prof:
        return f"Arousal: {ar_prof}."
    return ""


def generate_hypothesis(visita_snapshot: Dict[str, Any], pnev_json: Dict[str, Any]) -> Dict[str, str]:
    """
    Returns a dict with keys that the app can apply:
    - pattern, meccanismi, mantenenti (ipotesi)
    - vf_imp, vf_ponte (visione_funzionale) when helpful
    """
    ppc = _num(_get_visita(visita_snapshot, "PPC"))
    cover = _s(_get_visita(visita_snapshot, "Cover_Test"))
    mot = _s(_get_visita(visita_snapshot, "Motilita"))
    stereo = _s(_get_visita(visita_snapshot, "Stereopsi"))

    # Visual hints
    vis_hint = []
    if ppc is not None and ppc >= 10:
        vis_hint.append(f"PPC aumentato ({ppc:.1f} cm) compatibile con possibile affaticamento/convergenza inefficiente.")
    if cover:
        vis_hint.append(f"Cover test: {cover}.")
    if stereo:
        vis_hint.append(f"Stereopsi: {stereo}.")
    if mot:
        vis_hint.append(f"Motilità oculare: {mot}.")

    vis_text = " ".join(vis_hint).strip()

    profile = _profile_from_notes(pnev_json)

    pattern = "Difficoltà di autoregolazione con possibile componente sensoriale e sovraccarico, con impatto funzionale su attenzione e partecipazione."
    if ppc is not None and ppc >= 10:
        pattern = "Pattern di affaticamento visivo e instabilità attentiva, con possibile componente di integrazione sensoriale e autoregolazione variabile."

    meccanismi = "Ipotesi di interazione tra soglia sensoriale/arousal e richiesta ambientale (scuola/routine), con possibili ricadute su funzioni esecutive e tolleranza allo sforzo."
    if vis_text:
        meccanismi = f"{meccanismi}\n\nPonte visivo: {vis_text}"

    if profile:
        meccanismi = f"{profile}\n{meccanismi}"

    mantenenti = "Fattori mantenenti possibili: carico scolastico elevato, sonno/routine non stabili, richieste visive prolungate, ambiente rumoroso, scarsa pausa/recupero."

    vf_imp = ""
    vf_ponte = ""
    if vis_text:
        vf_imp = "Possibile affaticamento visivo durante compiti prolungati (lettura/scrittura/schermi) con calo prestazione e aumentata irritabilità/evitamento."
        vf_ponte = "Integrare la componente visiva nel pattern PNEV: qualità dell’input visivo + arousal possono modulare attenzione e partecipazione."

    return {
        "pattern": pattern,
        "mecc": meccanismi,
        "mant": mantenenti,
        "vf_imp": vf_imp,
        "vf_ponte": vf_ponte,
    }


def generate_plan(visita_snapshot: Dict[str, Any], pnev_json: Dict[str, Any]) -> Dict[str, str]:
    """
    Returns a dict with keys that the app can apply:
    - ob_breve, ob_medio, interv, scuola_ind, follow (piano)
    """
    ppc = _num(_get_visita(visita_snapshot, "PPC"))

    ob_breve = "- Stabilizzare autoregolazione (routine/pause)\n- Ridurre affaticamento durante compiti visivi\n- Aumentare tolleranza allo sforzo con micro-obiettivi"
    ob_medio = "- Migliorare partecipazione scolastica e autonomia\n- Consolidare strategie sensoriali efficaci\n- Migliorare efficienza visuo-motoria e resistenza"

    interv = "Interventi suggeriti (bozza):\n- Programma multisensoriale graduato (propriocezione/vestibolare/tattile in base al profilo)\n- Igiene dell’arousal: pause, respirazione, prevedibilità\n- Se indicato, training visivo funzionale (convergenza/inseguimenti) integrato con compiti reali"
    if ppc is not None and ppc >= 10:
        interv += "\n- Considerare focus specifico su convergenza/affaticamento (PPC alto) e gestione carico visivo (20-20-20)."

    scuola_ind = "Indicazioni scuola (bozza):\n- Ridurre carico visivo continuativo (pause programmate)\n- Alternare canali (orale/visivo)\n- Postazione con riduzione distrattori\n- Tempi aggiuntivi per lettura/copia quando necessario"

    follow = "Follow-up (bozza): rivalutazione a 4–6 settimane su autoregolazione + tolleranza ai compiti; rivalutazione visiva funzionale se sintomi persistono."

    return {
        "ob_breve": ob_breve,
        "ob_medio": ob_medio,
        "interv": interv,
        "scuola_ind": scuola_ind,
        "follow": follow,
    }


def apply_to_session(prefix: str, suggestions: Dict[str, str]) -> None:
    """
    Convert suggestions dict into the Streamlit widget keys used by pnev_module.pnev_collect_ui,
    and assign into st.session_state.

    We keep this mapping here so future changes stay centralized.
    """
    import streamlit as st

    if not prefix:
        return

    # ipotesi
    if _s(suggestions.get("pattern")):
        st.session_state[f"{prefix}_pattern"] = suggestions["pattern"]
    if _s(suggestions.get("mecc")):
        st.session_state[f"{prefix}_mecc"] = suggestions["mecc"]
    if _s(suggestions.get("mant")):
        st.session_state[f"{prefix}_mant"] = suggestions["mant"]

    # visione funzionale
    if _s(suggestions.get("vf_imp")):
        st.session_state[f"{prefix}_vf_imp"] = suggestions["vf_imp"]
    if _s(suggestions.get("vf_ponte")):
        st.session_state[f"{prefix}_vf_ponte"] = suggestions["vf_ponte"]

    # piano
    if _s(suggestions.get("ob_breve")):
        st.session_state[f"{prefix}_ob_breve"] = suggestions["ob_breve"]
    if _s(suggestions.get("ob_medio")):
        st.session_state[f"{prefix}_ob_medio"] = suggestions["ob_medio"]
    if _s(suggestions.get("interv")):
        st.session_state[f"{prefix}_interv"] = suggestions["interv"]
    if _s(suggestions.get("scuola_ind")):
        st.session_state[f"{prefix}_scuola_ind"] = suggestions["scuola_ind"]
    if _s(suggestions.get("follow")):
        st.session_state[f"{prefix}_follow"] = suggestions["follow"]
