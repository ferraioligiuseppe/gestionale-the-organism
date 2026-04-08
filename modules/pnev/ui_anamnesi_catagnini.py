# -*- coding: utf-8 -*-
"""
Anamnesi strutturata PNEV — Metodo Castagnini (0–2 anni)
Salvataggio dentro pnev_json["anamnesi_castagnini"] (JSONB/TEXT esistente).
Nessuna migrazione DB richiesta.

Struttura JSON prodotta:
{
  "anamnesi_castagnini": {
    "_meta": {"versione": "1.0", "data": "YYYY-MM-DD"},
    "gravidanza": {...},
    "parto": {...},
    "neonatale": {...},
    "sviluppo_motorio": {...},
    "sviluppo_sensoriale": {...},
    "alimentazione_sonno": {...},
    "storia_familiare": {...},
    "motivo_invio": {...}
  }
}
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, Optional, Tuple

import streamlit as st


# ── helpers ──────────────────────────────────────────────────────────────────

def _n(v: Any) -> str:
    return ("" if v is None else str(v)).strip()

def _g(d: dict, key: str, default: Any = "") -> Any:
    return d.get(key, default) if d else default

def _radio(label: str, opts: list, current: str, key: str) -> str:
    idx = opts.index(current) if current in opts else 0
    return st.radio(label, opts, index=idx, horizontal=True, key=key)

def _sel(label: str, opts: list, current: str, key: str) -> str:
    all_opts = [""] + [o for o in opts if o != ""]
    idx = all_opts.index(current) if current in all_opts else 0
    return st.selectbox(label, all_opts, index=idx, key=key)

def _mesi(label: str, current: Any, key: str, min_v: int = 0, max_v: int = 36) -> Optional[int]:
    """Number input per età in mesi, con valore None se 0 (non compilato)."""
    val = int(current) if current else 0
    v = st.number_input(label, min_value=min_v, max_value=max_v, value=val, step=1, key=key)
    return int(v) if v > 0 else None

def _check(label: str, current: bool, key: str) -> bool:
    return st.checkbox(label, value=bool(current), key=key)

def _txt(label: str, current: str, key: str, height: int = 70) -> str:
    return st.text_area(label, value=_n(current), key=key, height=height)

def _inp(label: str, current: str, key: str) -> str:
    return st.text_input(label, value=_n(current), key=key)


# ── default ───────────────────────────────────────────────────────────────────

def _default() -> dict:
    return {
        "_meta": {"versione": "1.0", "data": date.today().isoformat()},
        "gravidanza": {
            "settimane": "",          # termine/pretermine/posttermine
            "settimane_numero": None, # numero settimane se noto
            "tipo": "",               # singola/gemellare/altro
            "complicanze": {
                "ipertensione": False,
                "nausea_grave": False,
                "infezioni": False,
                "stress_emotivo": False,
                "farmaci": False,
                "cadute_traumi": False,
                "altro": False,
                "altro_desc": "",
            },
            "movimenti_fetali": "",   # normali/ridotti/eccessivi
            "controlli_regolari": "", # si/no/parziali
            "note": "",
        },
        "parto": {
            "tipo": "",               # spontaneo/indotto/cesareo_programmato/cesareo_urgenza
            "presentazione": "",      # cefalica/podalica/trasversa
            "durata_travaglio": "",   # rapido/normale/prolungato
            "strumenti": {
                "forcipe": False,
                "ventosa": False,
            },
            "complicanze": {
                "distress_fetale": False,
                "cordone": False,
                "emorragia": False,
                "altro": False,
                "altro_desc": "",
            },
            "apgar_1": None,          # int 0-10
            "apgar_5": None,
            "ospedalizzazione_neonato": "",  # no/si
            "ospedalizzazione_motivo": "",
            "note": "",
        },
        "neonatale": {
            "allattamento": "",           # seno/formula/misto
            "difficolta_suzione": "",     # no/si/lieve/severa
            "coliche": "",                # assenti/lievi/severe
            "sonno": "",                  # regolare/difficolta_addormentamento/risvegli_frequenti
            "pianto": "",                 # normale/inconsolabile/assente
            "tono_nascita": "",           # normale/ipotonico/ipertonico
            "riflessi": {
                "moro": "",               # presente/assente/asimmetrico
                "suzione": "",
                "prensione": "",
                "babinski": "",
                "galant": "",
                "tonic_neck": "",         # RTLN
            },
            "note": "",
        },
        "sviluppo_motorio": {
            # età in mesi (None = non compilato)
            "controllo_capo_mesi": None,
            "rotolamento_mesi": None,
            "rotolamento_fatto": "",          # si/no/parziale
            "stazione_seduta_mesi": None,
            "stazione_seduta_tipo": "",       # con_supporto/senza_supporto
            "gattonamento_fatto": "",         # si/no/strisciamento/saltato
            "gattonamento_mesi": None,
            "posizione_eretta_mesi": None,    # con appoggio
            "primi_passi_mesi": None,
            "qualita_movimento": "",          # asimmetrie, preferenze precoci
            "lateralizzazione_precoce": "",   # no/si_dx/si_sx
            "note": "",
        },
        "sviluppo_sensoriale": {
            "risposta_suoni": "",         # normale/iporeattivo/iperreattivo
            "tracking_visivo": "",        # si/no/parziale
            "tracking_mesi": None,
            "sorriso_sociale_mesi": None,
            "lallazione_mesi": None,
            "prime_parole_mesi": None,
            "contatto_oculare": "",       # normale/ridotto/assente
            "risposta_nome_mesi": None,
            "imitazione": "",             # presente/assente/parziale
            "note": "",
        },
        "alimentazione_sonno": {
            "svezzamento_mesi": None,
            "svezzamento_difficolta": "",   # no/si
            "masticazione": "",             # normale/difficoltosa
            "selettivita_alimentare": "",   # no/si
            "selettivita_desc": "",
            "sonno_ore_notte": None,
            "sonnellini": "",               # si/no/ridotti_precocemente
            "sonno_note": "",
        },
        "storia_familiare": {
            "familiarita_apprendimento": "", # no/si
            "familiarita_dsa_adhd": "",      # no/si
            "familiarita_autismo": "",       # no/si
            "fratelli_difficolta": "",       # no/si
            "nido": "",                      # si/no
            "nido_eta_mesi": None,
            "nido_adattamento": "",          # buono/difficile/molto_difficile
            "lingua_casa": "",               # italiano/bilingue/altro
            "lingua_altro": "",
            "note": "",
        },
        "motivo_invio": {
            "inviante": "",           # pediatra/logopedista/genitore/npi/altro
            "inviante_altro": "",
            "preoccupazione_principale": "",
            "valutazioni_precedenti": "",    # no/si
            "valutazioni_tipo": "",
            "terapie_in_corso": "",          # no/si
            "terapie_tipo": "",
            "note": "",
        },
    }


# ── sezioni UI ────────────────────────────────────────────────────────────────

def _sezione_gravidanza(g: dict, px: str) -> dict:
    st.markdown("#### 🤰 Gravidanza")

    col1, col2 = st.columns(2)
    with col1:
        g["settimane"] = _radio(
            "Termine gestazionale",
            ["termine (38–42 sett.)", "pre-termine (<38 sett.)", "post-termine (>42 sett.)"],
            g.get("settimane", ""),
            f"{px}_grav_sett",
        )
    with col2:
        sett_n = g.get("settimane_numero")
        v = st.number_input("N° settimane (se noto)", 20, 45,
                            int(sett_n) if sett_n else 40, 1, key=f"{px}_grav_sett_n")
        g["settimane_numero"] = int(v)

    g["tipo"] = _radio("Tipo gravidanza",
                        ["singola", "gemellare", "altro"],
                        g.get("tipo", "singola"), f"{px}_grav_tipo")

    st.markdown("**Complicanze in gravidanza** (spunta tutto ciò che si è verificato)")
    comp = g.get("complicanze", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        comp["ipertensione"]  = _check("Ipertensione / preeclampsia", comp.get("ipertensione", False), f"{px}_comp_ipert")
        comp["nausea_grave"]  = _check("Nausea / vomito grave",        comp.get("nausea_grave", False),  f"{px}_comp_nausea")
    with c2:
        comp["infezioni"]     = _check("Infezioni",                   comp.get("infezioni", False),     f"{px}_comp_inf")
        comp["stress_emotivo"]= _check("Stress emotivo / lutto",       comp.get("stress_emotivo", False),f"{px}_comp_stress")
    with c3:
        comp["farmaci"]       = _check("Farmaci / sostanze",           comp.get("farmaci", False),       f"{px}_comp_farm")
        comp["cadute_traumi"] = _check("Cadute / traumi addominali",   comp.get("cadute_traumi", False), f"{px}_comp_traumi")
    comp["altro"]             = _check("Altro",                        comp.get("altro", False),         f"{px}_comp_altro")
    if comp.get("altro"):
        comp["altro_desc"] = _inp("Specificare (altro complicanze)", comp.get("altro_desc", ""), f"{px}_comp_altro_desc")
    g["complicanze"] = comp

    col3, col4 = st.columns(2)
    with col3:
        g["movimenti_fetali"] = _radio("Movimenti fetali",
                                        ["normali", "ridotti", "eccessivi", "non valutabili"],
                                        g.get("movimenti_fetali", "normali"), f"{px}_mov_fetali")
    with col4:
        g["controlli_regolari"] = _radio("Controlli prenatali",
                                          ["regolari", "parziali", "assenti"],
                                          g.get("controlli_regolari", "regolari"), f"{px}_ctrl_prena")

    g["note"] = _txt("Note gravidanza", g.get("note", ""), f"{px}_grav_note", height=80)
    return g


def _sezione_parto(p: dict, px: str) -> dict:
    st.markdown("#### 🏥 Parto")

    col1, col2 = st.columns(2)
    with col1:
        p["tipo"] = _sel("Tipo di parto",
                          ["spontaneo", "indotto", "cesareo programmato", "cesareo d'urgenza"],
                          p.get("tipo", ""), f"{px}_parto_tipo")
        p["presentazione"] = _radio("Presentazione",
                                     ["cefalica", "podalica", "trasversa", "non noto"],
                                     p.get("presentazione", "cefalica"), f"{px}_present")
    with col2:
        p["durata_travaglio"] = _radio("Durata travaglio",
                                        ["rapido (<2h)", "normale", "prolungato (>12h)", "non noto"],
                                        p.get("durata_travaglio", "normale"), f"{px}_durata_trav")

    st.markdown("**Strumenti utilizzati**")
    strm = p.get("strumenti", {})
    c1, c2 = st.columns(2)
    with c1:
        strm["forcipe"] = _check("Forcipe", strm.get("forcipe", False), f"{px}_forcipe")
    with c2:
        strm["ventosa"] = _check("Ventosa",  strm.get("ventosa", False),  f"{px}_ventosa")
    p["strumenti"] = strm

    st.markdown("**Complicanze al parto**")
    comp = p.get("complicanze", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        comp["distress_fetale"] = _check("Distress fetale", comp.get("distress_fetale", False), f"{px}_dist_feto")
    with c2:
        comp["cordone"]         = _check("Problemi cordone", comp.get("cordone", False),         f"{px}_cordone")
    with c3:
        comp["emorragia"]       = _check("Emorragia",         comp.get("emorragia", False),       f"{px}_emor")
    comp["altro"]               = _check("Altro",              comp.get("altro", False),            f"{px}_parto_altro")
    if comp.get("altro"):
        comp["altro_desc"] = _inp("Specificare (altro parto)", comp.get("altro_desc", ""), f"{px}_parto_altro_d")
    p["complicanze"] = comp

    st.markdown("**APGAR** (se noto)")
    ca, cb = st.columns(2)
    with ca:
        a1 = p.get("apgar_1")
        v1 = st.number_input("APGAR 1° minuto", 0, 10, int(a1) if a1 is not None else 9, 1, key=f"{px}_apgar1")
        p["apgar_1"] = int(v1)
    with cb:
        a5 = p.get("apgar_5")
        v5 = st.number_input("APGAR 5° minuto", 0, 10, int(a5) if a5 is not None else 10, 1, key=f"{px}_apgar5")
        p["apgar_5"] = int(v5)

    p["ospedalizzazione_neonato"] = _radio("Ospedalizzazione neonato dopo il parto",
                                            ["no", "sì"], p.get("ospedalizzazione_neonato", "no"), f"{px}_osped")
    if p.get("ospedalizzazione_neonato") == "sì":
        p["ospedalizzazione_motivo"] = _inp("Motivo ospedalizzazione", p.get("ospedalizzazione_motivo", ""), f"{px}_osped_mot")

    p["note"] = _txt("Note parto", p.get("note", ""), f"{px}_parto_note", height=80)
    return p


def _sezione_neonatale(n: dict, px: str) -> dict:
    st.markdown("#### 👶 Periodo neonatale (0–3 mesi)")

    col1, col2 = st.columns(2)
    with col1:
        n["allattamento"] = _radio("Allattamento",
                                    ["seno", "formula", "misto"],
                                    n.get("allattamento", "seno"), f"{px}_allatt")
        n["difficolta_suzione"] = _radio("Difficoltà di suzione",
                                          ["no", "lieve", "severa"],
                                          n.get("difficolta_suzione", "no"), f"{px}_suzione")
        n["coliche"] = _radio("Coliche",
                               ["assenti", "lievi", "severe"],
                               n.get("coliche", "assenti"), f"{px}_coliche")
    with col2:
        n["sonno"] = _radio("Sonno neonatale",
                             ["regolare", "difficoltà addormentamento", "risvegli frequenti"],
                             n.get("sonno", "regolare"), f"{px}_sonno_neo")
        n["pianto"] = _radio("Tipo di pianto",
                              ["normale", "inconsolabile", "scarso/assente"],
                              n.get("pianto", "normale"), f"{px}_pianto")
        n["tono_nascita"] = _radio("Tono muscolare alla nascita",
                                    ["normale", "ipotonico", "ipertonico", "non valutato"],
                                    n.get("tono_nascita", "normale"), f"{px}_tono_nasc")

    st.markdown("**Riflessi neonatali** (stato al momento della valutazione o riferito dai genitori)")
    rifl = n.get("riflessi", {})
    opts_rifl = ["presente", "assente", "asimmetrico", "non valutato"]
    c1, c2, c3 = st.columns(3)
    with c1:
        rifl["moro"]        = _radio("Riflesso di Moro",        opts_rifl, rifl.get("moro", "presente"),        f"{px}_moro")
        rifl["suzione"]     = _radio("Suzione non nutritiva",   opts_rifl, rifl.get("suzione", "presente"),     f"{px}_suzione_r")
    with c2:
        rifl["prensione"]   = _radio("Prensione palmare",       opts_rifl, rifl.get("prensione", "presente"),   f"{px}_prens")
        rifl["babinski"]    = _radio("Babinski",                 opts_rifl, rifl.get("babinski", "presente"),    f"{px}_babinsk")
    with c3:
        rifl["galant"]      = _radio("Galant (incurvamento)",   opts_rifl, rifl.get("galant", "non valutato"),  f"{px}_galant")
        rifl["tonic_neck"]  = _radio("RTLN (collo tonico)",     opts_rifl, rifl.get("tonic_neck", "non valutato"), f"{px}_rtln")
    n["riflessi"] = rifl

    n["note"] = _txt("Note periodo neonatale", n.get("note", ""), f"{px}_neo_note", height=80)
    return n


def _sezione_sviluppo_motorio(sm: dict, px: str) -> dict:
    st.markdown("#### 🏃 Sviluppo motorio (0–24 mesi) — Castagnini")
    st.caption("Inserire l'età in mesi in cui la tappa è stata raggiunta. Lasciare 0 se non compilato.")

    c1, c2, c3 = st.columns(3)
    with c1:
        sm["controllo_capo_mesi"] = _mesi("Controllo capo (mesi)", sm.get("controllo_capo_mesi"), f"{px}_capo_mesi")
    with c2:
        sm["rotolamento_fatto"] = _radio("Rotolamento",
                                          ["sì", "no", "parziale"],
                                          sm.get("rotolamento_fatto", "sì"), f"{px}_rotol_fatto")
    with c3:
        if sm.get("rotolamento_fatto") == "sì":
            sm["rotolamento_mesi"] = _mesi("Età rotolamento (mesi)", sm.get("rotolamento_mesi"), f"{px}_rotol_mesi")

    c1, c2, c3 = st.columns(3)
    with c1:
        sm["stazione_seduta_mesi"] = _mesi("Stazione seduta (mesi)", sm.get("stazione_seduta_mesi"), f"{px}_seduta_mesi")
    with c2:
        sm["stazione_seduta_tipo"] = _radio("Tipo stazione seduta",
                                             ["con supporto", "senza supporto"],
                                             sm.get("stazione_seduta_tipo", "senza supporto"), f"{px}_seduta_tipo")

    c1, c2, c3 = st.columns(3)
    with c1:
        sm["gattonamento_fatto"] = _radio("Gattonamento",
                                           ["sì", "no", "strisciamento", "saltato"],
                                           sm.get("gattonamento_fatto", "sì"), f"{px}_gatto_fatto")
    with c2:
        if sm.get("gattonamento_fatto") == "sì":
            sm["gattonamento_mesi"] = _mesi("Età gattonamento (mesi)", sm.get("gattonamento_mesi"), f"{px}_gatto_mesi")
    with c3:
        sm["posizione_eretta_mesi"] = _mesi("Posizione eretta con appoggio (mesi)",
                                             sm.get("posizione_eretta_mesi"), f"{px}_eretta_mesi")

    c1, c2 = st.columns(2)
    with c1:
        sm["primi_passi_mesi"] = _mesi("Primi passi autonomi (mesi)", sm.get("primi_passi_mesi"), f"{px}_passi_mesi")
    with c2:
        sm["lateralizzazione_precoce"] = _radio("Lateralizzazione precoce (prima del 12° mese)",
                                                 ["no", "sì – destra", "sì – sinistra", "non osservata"],
                                                 sm.get("lateralizzazione_precoce", "no"), f"{px}_later")

    sm["qualita_movimento"] = _txt(
        "Qualità del movimento (asimmetrie, preferenze posturali, difficoltà osservate)",
        sm.get("qualita_movimento", ""), f"{px}_qualita_mov", height=80
    )
    sm["note"] = _txt("Note sviluppo motorio", sm.get("note", ""), f"{px}_sm_note", height=80)
    return sm


def _sezione_sviluppo_sensoriale(ss: dict, px: str) -> dict:
    st.markdown("#### 👁️ Sviluppo sensoriale e comunicativo (0–24 mesi)")

    c1, c2 = st.columns(2)
    with c1:
        ss["risposta_suoni"] = _radio("Risposta ai suoni",
                                       ["normale", "iporeattivo", "iperreattivo", "non valutato"],
                                       ss.get("risposta_suoni", "normale"), f"{px}_risp_suoni")
        ss["contatto_oculare"] = _radio("Contatto oculare",
                                         ["normale", "ridotto", "assente", "non valutato"],
                                         ss.get("contatto_oculare", "normale"), f"{px}_cont_ocul")
        ss["imitazione"] = _radio("Imitazione (gesti, espressioni)",
                                   ["presente", "parziale", "assente", "non valutato"],
                                   ss.get("imitazione", "presente"), f"{px}_imitaz")
    with c2:
        ss["tracking_visivo"] = _radio("Tracking visivo (segue oggetti)",
                                        ["sì", "no", "parziale"],
                                        ss.get("tracking_visivo", "sì"), f"{px}_tracking")
        if ss.get("tracking_visivo") == "sì":
            ss["tracking_mesi"] = _mesi("Età tracking (mesi)", ss.get("tracking_mesi"), f"{px}_track_mesi", max_v=12)

    st.markdown("**Tappe comunicative** (età in mesi — lasciare 0 se non raggiunta o non nota)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ss["sorriso_sociale_mesi"]  = _mesi("Sorriso sociale",  ss.get("sorriso_sociale_mesi"),  f"{px}_sorriso",  max_v=12)
    with c2:
        ss["lallazione_mesi"]       = _mesi("Lallazione",        ss.get("lallazione_mesi"),       f"{px}_lallaz",   max_v=18)
    with c3:
        ss["prime_parole_mesi"]     = _mesi("Prime parole",      ss.get("prime_parole_mesi"),     f"{px}_parole",   max_v=30)
    with c4:
        ss["risposta_nome_mesi"]    = _mesi("Risposta al nome",  ss.get("risposta_nome_mesi"),    f"{px}_nome",     max_v=18)

    ss["note"] = _txt("Note sviluppo sensoriale/comunicativo", ss.get("note", ""), f"{px}_ss_note", height=80)
    return ss


def _sezione_alimentazione_sonno(als: dict, px: str) -> dict:
    st.markdown("#### 🍼 Alimentazione e sonno (0–24 mesi)")

    c1, c2 = st.columns(2)
    with c1:
        als["svezzamento_mesi"] = _mesi("Svezzamento (mesi)", als.get("svezzamento_mesi"), f"{px}_svez_mesi", min_v=0, max_v=24)
        als["svezzamento_difficolta"] = _radio("Difficoltà nello svezzamento",
                                                ["no", "sì"], als.get("svezzamento_difficolta", "no"), f"{px}_svez_diff")
        als["masticazione"] = _radio("Masticazione",
                                      ["normale", "difficoltosa"],
                                      als.get("masticazione", "normale"), f"{px}_masticz")
    with c2:
        als["selettivita_alimentare"] = _radio("Selettività alimentare",
                                                ["no", "lieve", "severa"],
                                                als.get("selettivita_alimentare", "no"), f"{px}_selettiv")
        if als.get("selettivita_alimentare") != "no":
            als["selettivita_desc"] = _inp("Descrivi selettività", als.get("selettivita_desc", ""), f"{px}_selettiv_d")

    st.markdown("**Sonno**")
    cs1, cs2, cs3 = st.columns(3)
    with cs1:
        ore = als.get("sonno_ore_notte")
        v_ore = st.number_input("Ore di sonno notturno (media)", 0.0, 14.0,
                                 float(ore) if ore else 9.0, 0.5, key=f"{px}_sonno_ore")
        als["sonno_ore_notte"] = float(v_ore)
    with cs2:
        als["sonnellini"] = _radio("Sonnellini diurni",
                                    ["sì", "no", "ridotti precocemente"],
                                    als.get("sonnellini", "sì"), f"{px}_sonnell")
    with cs3:
        als["sonno_note"] = _inp("Note sonno", als.get("sonno_note", ""), f"{px}_sonno_note")

    return als


def _sezione_storia_familiare(sf: dict, px: str) -> dict:
    st.markdown("#### 👨‍👩‍👧 Storia familiare e contesto")

    c1, c2, c3 = st.columns(3)
    with c1:
        sf["familiarita_apprendimento"] = _radio("Familiarità difficoltà apprendimento",
                                                  ["no", "sì", "sospetta"],
                                                  sf.get("familiarita_apprendimento", "no"), f"{px}_fam_appr")
        sf["familiarita_dsa_adhd"] = _radio("Familiarità DSA / ADHD",
                                             ["no", "sì", "sospetta"],
                                             sf.get("familiarita_dsa_adhd", "no"), f"{px}_fam_dsa")
    with c2:
        sf["familiarita_autismo"] = _radio("Familiarità disturbi autistici",
                                            ["no", "sì", "sospetta"],
                                            sf.get("familiarita_autismo", "no"), f"{px}_fam_aut")
        sf["fratelli_difficolta"] = _radio("Fratelli/sorelle con difficoltà simili",
                                            ["no", "sì"],
                                            sf.get("fratelli_difficolta", "no"), f"{px}_fratelli")
    with c3:
        sf["nido"] = _radio("Frequenta / ha frequentato nido", ["no", "sì"],
                             sf.get("nido", "no"), f"{px}_nido")
        if sf.get("nido") == "sì":
            sf["nido_eta_mesi"] = _mesi("Età ingresso nido (mesi)", sf.get("nido_eta_mesi"), f"{px}_nido_eta", min_v=0, max_v=36)
            sf["nido_adattamento"] = _radio("Adattamento al nido",
                                             ["buono", "difficile", "molto difficile"],
                                             sf.get("nido_adattamento", "buono"), f"{px}_nido_adatt")

    c1, c2 = st.columns(2)
    with c1:
        sf["lingua_casa"] = _radio("Lingua parlata in casa",
                                    ["italiano", "bilingue", "altra lingua"],
                                    sf.get("lingua_casa", "italiano"), f"{px}_lingua_casa")
        if sf.get("lingua_casa") in ("bilingue", "altra lingua"):
            sf["lingua_altro"] = _inp("Specifica lingua(e)", sf.get("lingua_altro", ""), f"{px}_lingua_altro")

    sf["note"] = _txt("Note storia familiare / contesto", sf.get("note", ""), f"{px}_sf_note", height=80)
    return sf


def _sezione_motivo_invio(mi: dict, px: str) -> dict:
    st.markdown("#### 📋 Motivo dell'invio / domanda clinica")

    c1, c2 = st.columns(2)
    with c1:
        mi["inviante"] = _radio("Chi ha inviato",
                                 ["genitore", "pediatra", "logopedista", "NPI", "altro"],
                                 mi.get("inviante", "genitore"), f"{px}_inviant")
        if mi.get("inviante") == "altro":
            mi["inviante_altro"] = _inp("Specificare inviante", mi.get("inviante_altro", ""), f"{px}_inviant_altro")
    with c2:
        mi["valutazioni_precedenti"] = _radio("Valutazioni precedenti",
                                               ["no", "sì"], mi.get("valutazioni_precedenti", "no"), f"{px}_val_prec")
        if mi.get("valutazioni_precedenti") == "sì":
            mi["valutazioni_tipo"] = _inp("Tipo di valutazioni precedenti", mi.get("valutazioni_tipo", ""), f"{px}_val_tipo")

        mi["terapie_in_corso"] = _radio("Terapie in corso",
                                         ["no", "sì"], mi.get("terapie_in_corso", "no"), f"{px}_ter_corso")
        if mi.get("terapie_in_corso") == "sì":
            mi["terapie_tipo"] = _inp("Tipo di terapie in corso", mi.get("terapie_tipo", ""), f"{px}_ter_tipo")

    mi["preoccupazione_principale"] = _txt(
        "Preoccupazione principale dei genitori (testo libero)",
        mi.get("preoccupazione_principale", ""), f"{px}_preoccup", height=100
    )
    mi["note"] = _txt("Note aggiuntive", mi.get("note", ""), f"{px}_mi_note", height=80)
    return mi


# ── summary ───────────────────────────────────────────────────────────────────

def _build_summary(data: dict) -> str:
    """Genera un testo riassuntivo compatto dei punti salienti."""
    lines = []

    def add(label: str, val: Any):
        v = _n(val)
        if v and v not in ("0", "no", "normale", "regolari", "assenti",
                            "presente", "singola", "termine (38–42 sett.)",
                            "cefalica", "normale", "sì"):
            lines.append(f"{label}: {v}")

    g = data.get("gravidanza", {})
    if g.get("settimane") and "pre" in g.get("settimane", "").lower():
        lines.append(f"Gravidanza: {g.get('settimane')} ({g.get('settimane_numero', '?')} sett.)")
    comp_g = [k for k, v in g.get("complicanze", {}).items() if v is True]
    if comp_g:
        lines.append("Complicanze gravidanza: " + ", ".join(comp_g))

    p = data.get("parto", {})
    if p.get("tipo") and p.get("tipo") != "spontaneo":
        lines.append(f"Parto: {p.get('tipo')}")
    if p.get("strumenti", {}).get("forcipe"):
        lines.append("Parto con forcipe")
    if p.get("strumenti", {}).get("ventosa"):
        lines.append("Parto con ventosa")
    a1 = p.get("apgar_1")
    a5 = p.get("apgar_5")
    if a1 is not None and int(a1) < 7:
        lines.append(f"APGAR basso: 1'={a1}, 5'={a5}")
    comp_p = [k for k, v in p.get("complicanze", {}).items() if v is True]
    if comp_p:
        lines.append("Complicanze parto: " + ", ".join(comp_p))

    n = data.get("neonatale", {})
    add("Allattamento", n.get("allattamento"))
    if n.get("difficolta_suzione") not in ("", "no"):
        lines.append(f"Difficoltà suzione: {n.get('difficolta_suzione')}")
    if n.get("coliche") not in ("", "assenti"):
        lines.append(f"Coliche: {n.get('coliche')}")
    if n.get("tono_nascita") not in ("", "normale"):
        lines.append(f"Tono nascita: {n.get('tono_nascita')}")
    rifl_anom = [k for k, v in n.get("riflessi", {}).items()
                  if v in ("assente", "asimmetrico") and k != "_"]
    if rifl_anom:
        lines.append("Riflessi anomali: " + ", ".join(rifl_anom))

    sm = data.get("sviluppo_motorio", {})
    if sm.get("gattonamento_fatto") in ("no", "saltato"):
        lines.append(f"Gattonamento: {sm.get('gattonamento_fatto')}")
    if sm.get("primi_passi_mesi") and int(sm.get("primi_passi_mesi", 0)) > 15:
        lines.append(f"Primi passi tardivi: {sm.get('primi_passi_mesi')} mesi")
    if sm.get("lateralizzazione_precoce") not in ("", "no", "non osservata"):
        lines.append(f"Lateralizzazione precoce: {sm.get('lateralizzazione_precoce')}")
    if sm.get("qualita_movimento"):
        lines.append(f"Qualità movimento: {sm.get('qualita_movimento')}")

    ss = data.get("sviluppo_sensoriale", {})
    if ss.get("risposta_suoni") not in ("", "normale"):
        lines.append(f"Risposta suoni: {ss.get('risposta_suoni')}")
    if ss.get("contatto_oculare") not in ("", "normale"):
        lines.append(f"Contatto oculare: {ss.get('contatto_oculare')}")
    if ss.get("prime_parole_mesi") and int(ss.get("prime_parole_mesi", 0)) > 14:
        lines.append(f"Prime parole tardive: {ss.get('prime_parole_mesi')} mesi")
    if ss.get("imitazione") not in ("", "presente"):
        lines.append(f"Imitazione: {ss.get('imitazione')}")

    als = data.get("alimentazione_sonno", {})
    if als.get("selettivita_alimentare") not in ("", "no"):
        lines.append(f"Selettività alimentare: {als.get('selettivita_alimentare')}")

    sf = data.get("storia_familiare", {})
    fam = [k.replace("familiarita_", "") for k in ("familiarita_apprendimento", "familiarita_dsa_adhd", "familiarita_autismo")
           if sf.get(k) == "sì"]
    if fam:
        lines.append("Familiarità: " + ", ".join(fam))

    mi = data.get("motivo_invio", {})
    if mi.get("preoccupazione_principale"):
        lines.append(f"Motivo invio: {mi.get('preoccupazione_principale')[:120]}")
    if mi.get("terapie_in_corso") == "sì":
        lines.append(f"Terapie in corso: {mi.get('terapie_tipo', '?')}")

    return "\n".join(lines) if lines else ""


# ── entry point principale ────────────────────────────────────────────────────

def render_anamnesi_castagnini(
    pnev_json: Dict[str, Any],
    prefix: str,
    readonly: bool = False,
) -> Tuple[Dict[str, Any], str]:
    """
    Renderizza l'anamnesi strutturata Castagnini 0–2 anni.

    Args:
        pnev_json: dict caricato da pnev_load() — verrà modificato in-place
                   nella chiave "anamnesi_castagnini".
        prefix:    prefisso univoco per i widget Streamlit (es. "new" o str(anamnesi_id))
        readonly:  se True, mostra solo il summary testuale (no widget)

    Returns:
        (pnev_json aggiornato, summary_text)
    """
    if pnev_json is None:
        pnev_json = {}

    # Carica o inizializza sotto-chiave
    raw_cat = pnev_json.get("anamnesi_castagnini")
    if isinstance(raw_cat, str):
        try:
            raw_cat = json.loads(raw_cat)
        except Exception:
            raw_cat = {}
    cat: dict = raw_cat if isinstance(raw_cat, dict) else _default()

    # Merge default (aggiunge chiavi mancanti senza sovrascrivere)
    defaults = _default()
    for k, v in defaults.items():
        if k not in cat:
            cat[k] = v

    if readonly:
        summary = _build_summary(cat)
        if summary:
            st.markdown("**Sintesi anamnesi Castagnini:**")
            for line in summary.split("\n"):
                st.markdown(f"- {line}")
        else:
            st.caption("Anamnesi Castagnini non compilata.")
        return pnev_json, summary

    st.markdown("## 📋 Anamnesi PNEV — Castagnini (0–2 anni)")
    st.caption("Tutti i campi sono facoltativi. I dati vengono salvati in pnev_json senza migrazioni DB.")

    px = f"cat_{prefix}"

    with st.expander("1️⃣ Gravidanza", expanded=True):
        cat["gravidanza"] = _sezione_gravidanza(cat.get("gravidanza", {}), px)

    with st.expander("2️⃣ Parto", expanded=False):
        cat["parto"] = _sezione_parto(cat.get("parto", {}), px)

    with st.expander("3️⃣ Periodo neonatale (0–3 mesi)", expanded=False):
        cat["neonatale"] = _sezione_neonatale(cat.get("neonatale", {}), px)

    with st.expander("4️⃣ Sviluppo motorio (0–24 mesi)", expanded=False):
        cat["sviluppo_motorio"] = _sezione_sviluppo_motorio(cat.get("sviluppo_motorio", {}), px)

    with st.expander("5️⃣ Sviluppo sensoriale e comunicativo", expanded=False):
        cat["sviluppo_sensoriale"] = _sezione_sviluppo_sensoriale(cat.get("sviluppo_sensoriale", {}), px)

    with st.expander("6️⃣ Alimentazione e sonno", expanded=False):
        cat["alimentazione_sonno"] = _sezione_alimentazione_sonno(cat.get("alimentazione_sonno", {}), px)

    with st.expander("7️⃣ Storia familiare e contesto", expanded=False):
        cat["storia_familiare"] = _sezione_storia_familiare(cat.get("storia_familiare", {}), px)

    with st.expander("8️⃣ Motivo dell'invio / domanda clinica", expanded=False):
        cat["motivo_invio"] = _sezione_motivo_invio(cat.get("motivo_invio", {}), px)

    # Aggiorna timestamp
    cat["_meta"] = {"versione": "1.0", "data": date.today().isoformat()}

    # Scrivi nel pnev_json principale
    pnev_json["anamnesi_castagnini"] = cat

    summary = _build_summary(cat)

    # Anteprima summary collassata
    with st.expander("📄 Anteprima sintesi anamnesi", expanded=False):
        if summary:
            for line in summary.split("\n"):
                st.markdown(f"- {line}")
        else:
            st.caption("Nessun elemento saliente da evidenziare (tutti i valori sono nella norma attesa).")

    return pnev_json, summary
# Alias per compatibilità con app_core.py (typo storico)
render_anamnesi_catagnini = render_anamnesi_castagnini
