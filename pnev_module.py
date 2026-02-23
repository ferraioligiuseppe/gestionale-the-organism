
"""
PNEV module (Psico‑Neuro‑Evolutivo) for The Organism.

Design goals:
- Store structured data (dict) as JSON (JSONB on Postgres / TEXT on SQLite)
- Generate a printable summary (TEXT) for referti/PDF
- Keep it easy to extend: add new keys without DB migrations
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional, List
import json

import streamlit as st


PNEV_VERSION = 1


def _norm(s: Any) -> str:
    return ("" if s is None else str(s)).strip()


def _sel(label: str, options: List[str], value: str, key: str) -> str:
    # keeps current even if not in list
    opts = options[:]
    if value and value not in opts:
        opts = [value] + opts
    if "" not in opts:
        opts = [""] + opts
    idx = 0
    if value in opts:
        idx = opts.index(value)
    return st.selectbox(label, opts, index=idx, key=key)


def pnev_default() -> Dict[str, Any]:
    return {
        "v": PNEV_VERSION,
        "domanda_clinica": {"invio": "", "motivo": "", "obiettivi": "", "punti_chiave": ""},
        "profilo_neuroevolutivo": {"sviluppo": "", "linguaggio": "", "autonomie": "", "regolazione": "", "rischi_protezioni": ""},
        "sensoriale": {
            "tattile": {"profilo": "", "note": ""},
            "vestibolare": {"profilo": "", "note": ""},
            "propriocettiva": {"profilo": "", "note": ""},
            "uditiva": {"profilo": "", "note": ""},
            "visiva": {"profilo": "", "note": ""},
            "interocezione": {"profilo": "", "note": ""},
            "arousal": {"profilo": "", "note": "", "strategie": ""},
        },
        "visione_funzionale": {"impatto": "", "ponte_pnev": ""},
        "motorio_prassico": {"tono": "", "equilibrio": "", "coordinazione": "", "prassie": "", "respirazione": "", "note": ""},
        "neurocognitivo": {"attenzione": "", "memoria_lavoro": "", "pianificazione": "", "flessibilita": "", "inibizione": "", "note": ""},
        "partecipazione": {"scuola": "", "relazioni": "", "famiglia": "", "interessi": "", "note": ""},
        "ipotesi": {"pattern": "", "meccanismi": "", "mantenenti": ""},
        "piano": {"obiettivi_breve": "", "obiettivi_medio": "", "interventi": "", "indicazioni_scuola": "", "followup": ""},
        "red_flags": {"presenti": False, "note": "", "invii": ""},
    }


def pnev_load(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return pnev_default()
    if isinstance(raw, dict):
        base = pnev_default()
        # shallow merge
        for k, v in raw.items():
            base[k] = v
        return base
    s = _norm(raw)
    if not s:
        return pnev_default()
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return pnev_load(obj)
    except Exception:
        pass
    return pnev_default()


def pnev_dump(obj: Dict[str, Any]) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))


def pnev_pack_visita(**kwargs) -> Dict[str, Any]:
    """
    Minimal snapshot of the *current* visual visit.
    Keep it stable and non-identifying: no CF, no email, no address.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def pnev_collect_ui(prefix: str, visita: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], str]:
    """
    Render PNEV UI. Returns (pnev_dict, summary_text).

    prefix: unique key prefix for Streamlit widget keys.
    visita: snapshot of current visual visit (dict).
    existing: previously saved pnev dict (optional).
    """
    data = pnev_load(existing)

    st.markdown("### 🧠 Valutazione PNEV (Psico‑Neuro‑Evolutivo)")
    st.caption("Strutturata • salvata come JSON • facilmente estendibile (scalabile)")

    with st.expander("1) Domanda clinica", expanded=True):
        data["domanda_clinica"]["invio"] = st.text_input("Invio / provenienza (genitori, scuola, NPI, …)", _norm(data["domanda_clinica"].get("invio")), key=f"{prefix}_invio")
        data["domanda_clinica"]["motivo"] = st.text_area("Motivo della consultazione", _norm(data["domanda_clinica"].get("motivo")), key=f"{prefix}_motivo", height=80)
        data["domanda_clinica"]["obiettivi"] = st.text_area("Obiettivi della valutazione", _norm(data["domanda_clinica"].get("obiettivi")), key=f"{prefix}_obiettivi", height=80)
        data["domanda_clinica"]["punti_chiave"] = st.text_area("Punti chiave (bullet o frasi brevi)", _norm(data["domanda_clinica"].get("punti_chiave")), key=f"{prefix}_punti", height=80)

    with st.expander("2) Profilo neuroevolutivo", expanded=False):
        data["profilo_neuroevolutivo"]["sviluppo"] = st.text_area("Sviluppo motorio / tappe / coordinazione", _norm(data["profilo_neuroevolutivo"].get("sviluppo")), key=f"{prefix}_sviluppo", height=90)
        data["profilo_neuroevolutivo"]["linguaggio"] = st.text_area("Linguaggio / comunicazione", _norm(data["profilo_neuroevolutivo"].get("linguaggio")), key=f"{prefix}_lingua", height=80)
        data["profilo_neuroevolutivo"]["autonomie"] = st.text_area("Autonomie (sonno, alimentazione, routine…)", _norm(data["profilo_neuroevolutivo"].get("autonomie")), key=f"{prefix}_autonomie", height=80)
        data["profilo_neuroevolutivo"]["regolazione"] = st.text_area("Regolazione emotiva / comportamentale", _norm(data["profilo_neuroevolutivo"].get("regolazione")), key=f"{prefix}_regolazione", height=80)
        data["profilo_neuroevolutivo"]["rischi_protezioni"] = st.text_area("Fattori di rischio / protezione", _norm(data["profilo_neuroevolutivo"].get("rischi_protezioni")), key=f"{prefix}_rp", height=80)

    with st.expander("3) Integrazione sensoriale + arousal", expanded=True):
        prof_opts = ["ipo", "iper", "variabile", "disorganizzata", "non valutato"]
        cols = st.columns(2)
        def _sens(block_key: str, label: str, col):
            with col:
                bk = data["sensoriale"].get(block_key, {}) or {}
                bk["profilo"] = _sel(f"{label} – profilo", prof_opts, _norm(bk.get("profilo")), key=f"{prefix}_{block_key}_prof")
                bk["note"] = st.text_area(f"{label} – note", _norm(bk.get("note")), key=f"{prefix}_{block_key}_note", height=70)
                data["sensoriale"][block_key] = bk

        _sens("tattile", "Tattile", cols[0])
        _sens("vestibolare", "Vestibolare", cols[1])
        cols = st.columns(2)
        _sens("propriocettiva", "Propriocettiva", cols[0])
        _sens("uditiva", "Uditiva", cols[1])
        cols = st.columns(2)
        _sens("visiva", "Visiva", cols[0])
        _sens("interocezione", "Interocezione", cols[1])

        st.markdown("**Arousal / soglia / autoregolazione**")
        ar = data["sensoriale"].get("arousal", {}) or {}
        ar["profilo"] = _sel("Profilo arousal", ["basso", "alto", "variabile", "disregolato", "non valutato"], _norm(ar.get("profilo")), key=f"{prefix}_arousal_prof")
        ar["note"] = st.text_area("Trigger / segnali / osservazioni", _norm(ar.get("note")), key=f"{prefix}_arousal_note", height=80)
        ar["strategie"] = st.text_area("Strategie che funzionano / co‑regolazione", _norm(ar.get("strategie")), key=f"{prefix}_arousal_strat", height=80)
        data["sensoriale"]["arousal"] = ar

    with st.expander("4) Visione funzionale (integrata con la visita attuale)", expanded=True):
        st.caption("I dati sotto arrivano dalla visita visiva attuale (read‑only).")
        st.code(json.dumps(visita or {}, ensure_ascii=False, indent=2), language="json")
        data["visione_funzionale"]["impatto"] = st.text_area("Impatto funzionale visivo (fatica, evitamento, lettura, postura…)", _norm(data["visione_funzionale"].get("impatto")), key=f"{prefix}_vf_imp", height=90)
        data["visione_funzionale"]["ponte_pnev"] = st.text_area("Collegamento con pattern PNEV (ipotesi/integrazione)", _norm(data["visione_funzionale"].get("ponte_pnev")), key=f"{prefix}_vf_ponte", height=90)

    with st.expander("5) Motorio / prassico / postura", expanded=False):
        mp = data["motorio_prassico"]
        mp["tono"] = st.text_area("Tono (ipo/iper/variabile) e qualità", _norm(mp.get("tono")), key=f"{prefix}_tono", height=70)
        mp["equilibrio"] = st.text_area("Equilibrio / sicurezza gravitazionale", _norm(mp.get("equilibrio")), key=f"{prefix}_equil", height=70)
        mp["coordinazione"] = st.text_area("Coordinazione bilaterale / ritmo", _norm(mp.get("coordinazione")), key=f"{prefix}_coord", height=70)
        mp["prassie"] = st.text_area("Prassie / pianificazione motoria", _norm(mp.get("prassie")), key=f"{prefix}_prassie", height=70)
        mp["respirazione"] = st.text_area("Respirazione / pattern (se rilevante)", _norm(mp.get("respirazione")), key=f"{prefix}_resp", height=60)
        mp["note"] = st.text_area("Note aggiuntive", _norm(mp.get("note")), key=f"{prefix}_mp_note", height=70)

    with st.expander("6) Neurocognitivo (osservazione clinica)", expanded=False):
        nc = data["neurocognitivo"]
        nc["attenzione"] = st.text_area("Attenzione (sostenuta/selettiva/shifting)", _norm(nc.get("attenzione")), key=f"{prefix}_att", height=70)
        nc["memoria_lavoro"] = st.text_area("Memoria di lavoro", _norm(nc.get("memoria_lavoro")), key=f"{prefix}_ml", height=60)
        nc["pianificazione"] = st.text_area("Pianificazione/organizzazione", _norm(nc.get("pianificazione")), key=f"{prefix}_plan", height=60)
        nc["flessibilita"] = st.text_area("Flessibilità", _norm(nc.get("flessibilita")), key=f"{prefix}_flex", height=60)
        nc["inibizione"] = st.text_area("Inibizione", _norm(nc.get("inibizione")), key=f"{prefix}_inh", height=60)
        nc["note"] = st.text_area("Note", _norm(nc.get("note")), key=f"{prefix}_nc_note", height=70)

    with st.expander("7) Partecipazione / contesto (ICF‑like)", expanded=False):
        p = data["partecipazione"]
        p["scuola"] = st.text_area("Scuola (lettura/scrittura/compiti/attenzione)", _norm(p.get("scuola")), key=f"{prefix}_scuola", height=80)
        p["relazioni"] = st.text_area("Relazioni (pari/adulti)", _norm(p.get("relazioni")), key=f"{prefix}_rel", height=70)
        p["famiglia"] = st.text_area("Famiglia / routine / risorse", _norm(p.get("famiglia")), key=f"{prefix}_fam", height=70)
        p["interessi"] = st.text_area("Interessi / partecipazione (sport, hobby…)", _norm(p.get("interessi")), key=f"{prefix}_int", height=60)
        p["note"] = st.text_area("Note", _norm(p.get("note")), key=f"{prefix}_p_note", height=70)

    with st.expander("8) Ipotesi PNEV integrata (pattern)", expanded=True):
        ip = data["ipotesi"]
        ip["pattern"] = st.text_area("Pattern principale (1–3 frasi chiare)", _norm(ip.get("pattern")), key=f"{prefix}_pattern", height=90)
        ip["meccanismi"] = st.text_area("Meccanismi plausibili (arousal, gating, oculomotricità, tono…)", _norm(ip.get("meccanismi")), key=f"{prefix}_mecc", height=90)
        ip["mantenenti"] = st.text_area("Fattori mantenenti (ambiente, sonno, richieste, stress…)", _norm(ip.get("mantenenti")), key=f"{prefix}_mant", height=80)

    with st.expander("9) Obiettivi e piano", expanded=True):
        pl = data["piano"]
        pl["obiettivi_breve"] = st.text_area("Obiettivi 0–4 settimane (max 3)", _norm(pl.get("obiettivi_breve")), key=f"{prefix}_ob_breve", height=80)
        pl["obiettivi_medio"] = st.text_area("Obiettivi 2–3 mesi (max 3)", _norm(pl.get("obiettivi_medio")), key=f"{prefix}_ob_medio", height=80)
        pl["interventi"] = st.text_area("Interventi consigliati (The Organism, home program…)", _norm(pl.get("interventi")), key=f"{prefix}_interv", height=90)
        pl["indicazioni_scuola"] = st.text_area("Indicazioni scuola (3 punti pratici)", _norm(pl.get("indicazioni_scuola")), key=f"{prefix}_scuola_ind", height=80)
        pl["followup"] = st.text_area("Follow‑up (quando e cosa rivalutare)", _norm(pl.get("followup")), key=f"{prefix}_follow", height=70)

    with st.expander("10) Red flags / invii", expanded=False):
        rf = data["red_flags"]
        rf["presenti"] = st.checkbox("Red flags presenti", value=bool(rf.get("presenti", False)), key=f"{prefix}_rf_presenti")
        rf["note"] = st.text_area("Note red flags", _norm(rf.get("note")), key=f"{prefix}_rf_note", height=80)
        rf["invii"] = st.text_area("Invii consigliati (NPI/logopedia/audiologia…)", _norm(rf.get("invii")), key=f"{prefix}_rf_invii", height=80)

    summary = pnev_summary_from_json(data, visita=visita)
    return data, summary


def pnev_summary_from_json(pnev: Dict[str, Any], visita: Optional[Dict[str, Any]] = None) -> str:
    """
    Compact printable summary: only filled fields are included.
    """
    p = pnev or {}
    lines: List[str] = []
    def add(title: str, body: str):
        b = _norm(body)
        if b:
            lines.append(f"{title}: {b}")

    dc = p.get("domanda_clinica", {}) or {}
    add("Invio", dc.get("invio",""))
    add("Motivo", dc.get("motivo",""))
    add("Obiettivi", dc.get("obiettivi",""))
    add("Punti chiave", dc.get("punti_chiave",""))

    pn = p.get("profilo_neuroevolutivo", {}) or {}
    add("Profilo sviluppo", pn.get("sviluppo",""))
    add("Linguaggio", pn.get("linguaggio",""))
    add("Autonomie", pn.get("autonomie",""))
    add("Regolazione", pn.get("regolazione",""))
    add("Rischi/Protezioni", pn.get("rischi_protezioni",""))

    sens = p.get("sensoriale", {}) or {}
    def sens_line(k: str, lab: str):
        bk = sens.get(k, {}) or {}
        prof = _norm(bk.get("profilo",""))
        note = _norm(bk.get("note",""))
        if prof or note:
            if note:
                lines.append(f"{lab}: {prof} – {note}".strip(" –"))
            else:
                lines.append(f"{lab}: {prof}".strip())
    sens_line("tattile","Sensoriale Tattile")
    sens_line("vestibolare","Sensoriale Vestibolare")
    sens_line("propriocettiva","Sensoriale Propriocettiva")
    sens_line("uditiva","Sensoriale Uditiva")
    sens_line("visiva","Sensoriale Visiva")
    sens_line("interocezione","Sensoriale Interocezione")
    ar = sens.get("arousal", {}) or {}
    if _norm(ar.get("profilo","")) or _norm(ar.get("note","")) or _norm(ar.get("strategie","")):
        lines.append("Arousal: " + " | ".join([x for x in [_norm(ar.get("profilo","")), _norm(ar.get("note","")), _norm(ar.get("strategie",""))] if x]))

    vf = p.get("visione_funzionale", {}) or {}
    add("Visione funzionale – impatto", vf.get("impatto",""))
    add("Visione funzionale – ponte PNEV", vf.get("ponte_pnev",""))

    mp = p.get("motorio_prassico", {}) or {}
    add("Tono/Postura", mp.get("tono",""))
    add("Equilibrio", mp.get("equilibrio",""))
    add("Coordinazione", mp.get("coordinazione",""))
    add("Prassie", mp.get("prassie",""))
    add("Respirazione", mp.get("respirazione",""))
    add("Motorio – note", mp.get("note",""))

    nc = p.get("neurocognitivo", {}) or {}
    add("Attenzione", nc.get("attenzione",""))
    add("Memoria lavoro", nc.get("memoria_lavoro",""))
    add("Pianificazione", nc.get("pianificazione",""))
    add("Flessibilità", nc.get("flessibilita",""))
    add("Inibizione", nc.get("inibizione",""))
    add("Neurocognitivo – note", nc.get("note",""))

    pa = p.get("partecipazione", {}) or {}
    add("Scuola", pa.get("scuola",""))
    add("Relazioni", pa.get("relazioni",""))
    add("Famiglia", pa.get("famiglia",""))
    add("Interessi", pa.get("interessi",""))
    add("Partecipazione – note", pa.get("note",""))

    ip = p.get("ipotesi", {}) or {}
    add("Ipotesi – pattern", ip.get("pattern",""))
    add("Ipotesi – meccanismi", ip.get("meccanismi",""))
    add("Ipotesi – mantenenti", ip.get("mantenenti",""))

    pl = p.get("piano", {}) or {}
    add("Obiettivi breve", pl.get("obiettivi_breve",""))
    add("Obiettivi medio", pl.get("obiettivi_medio",""))
    add("Interventi", pl.get("interventi",""))
    add("Indicazioni scuola", pl.get("indicazioni_scuola",""))
    add("Follow‑up", pl.get("followup",""))

    rf = p.get("red_flags", {}) or {}
    if bool(rf.get("presenti", False)) or _norm(rf.get("note","")) or _norm(rf.get("invii","")):
        lines.append("Red flags: " + ("PRESENTI" if bool(rf.get("presenti", False)) else "assenti/ND"))
        add("Red flags – note", rf.get("note",""))
        add("Invii", rf.get("invii",""))

    # Add a short "visita snapshot" line (optional)
    if visita:
        # keep it short: only acuità + cover + ppc if present
        av = []
        for k in ("Acuita_Nat_OD","Acuita_Nat_OS","Acuita_Corr_OD","Acuita_Corr_OS","Cover_Test","PPC"):
            if k in visita and _norm(visita.get(k)):
                av.append(f"{k}={_norm(visita.get(k))}")
        if av:
            lines.append("Visita attuale (estratto): " + ", ".join(av[:8]))

    return "\n".join(lines).strip()
