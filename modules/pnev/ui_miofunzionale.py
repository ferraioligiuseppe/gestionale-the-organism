# -*- coding: utf-8 -*-
"""
ui_miofunzionale.py — Terapia Miofunzionale (Ferrante)

Struttura:
  A. Anamnesi MFT (22 domande — scheda Dr. Ferrante)
  B. Esame Obiettivo
     - Osservazione generale (postura, tipologia volto, asimmetrie)
     - Osservazione orale (occlusione, palato, lingua, tonsille)
     - Posizione lingua a riposo
     - Misurazioni (labbra, spinta linguale, massetere)
  C. Valutazione funzionale
     - Deglutizione
     - Respirazione
     - Fonazione
     - Frenulo linguale
  D. Indice disfunzione + diagnosi funzionale

Entry point: render_miofunzionale(data_json, prefix) → (dict, summary)
"""

from __future__ import annotations
from datetime import date
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _g(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k, default)
    return d if d is not None else default

def _cb(label, val, key):
    return st.checkbox(label, value=bool(val), key=key)

def _s(label, opts, val, key):
    idx = opts.index(val) if val in opts else 0
    return st.selectbox(label, opts, index=idx, key=key)

def _t(label, val, key, height=68):
    return st.text_area(label, value=str(val or ""), height=height, key=key)

def _inp(label, val, key):
    return st.text_input(label, value=str(val or ""), key=key)

def _n(label, val, key, min_v=0.0, max_v=100.0, step=0.5, fmt="%.1f"):
    v = max(float(min_v), min(float(max_v), float(val or 0)))
    return st.number_input(label, float(min_v), float(max_v), v, float(step), fmt, key=key)

def _radio(label, opts, val, key):
    idx = opts.index(val) if val in opts else 0
    return st.radio(label, opts, index=idx, key=key, horizontal=True)


# ─────────────────────────────────────────────────────────────────────────────
# A. ANAMNESI MFT
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_anamnesi(d: dict, px: str) -> dict:
    st.markdown("#### 📋 A — Anamnesi MFT")
    st.caption("Scheda Dr. Antonio Ferrante — 22 domande standard")
    r = {}

    # 1. Parto
    st.markdown("**1. Parto**")
    c = st.columns(4)
    with c[0]: r["parto_tipo"] = _s("Tipo", ["—","Eutocico","Distocico","Cesareo d'urgenza","Cesareo programmato"],
                                     _g(d,"parto_tipo"), f"{px}_parto")
    with c[1]: r["parto_travaglio"] = _cb("Travaglio", _g(d,"parto_travaglio"), f"{px}_travaglio")
    with c[2]: r["parto_cordone"] = _cb("Cordone ombelicale", _g(d,"parto_cordone"), f"{px}_cordone")
    with c[3]: r["parto_note"] = _inp("Note", _g(d,"parto_note"), f"{px}_parto_note")

    # 2. Allattamento
    st.markdown("**2. Allattamento al seno esclusivo**")
    c2 = st.columns(2)
    with c2[0]: r["allattamento_seno"] = _radio("Allattamento seno", ["sì","no","misto"],
                                                  _g(d,"allattamento_seno","no"), f"{px}_all_seno")
    with c2[1]: r["allattamento_seno_durata"] = _inp("Per quanto tempo?",
                                                       _g(d,"allattamento_seno_durata"), f"{px}_all_dur")

    # 3. Biberon / Ciuccio
    st.markdown("**3. Biberon e ciuccio**")
    c3 = st.columns(2)
    with c3[0]: r["biberon_durata"] = _inp("Biberon — quanto tempo?",
                                            _g(d,"biberon_durata"), f"{px}_bib")
    with c3[1]: r["ciuccio"] = _radio("Ciuccio", ["no","sì"], _g(d,"ciuccio","no"), f"{px}_ciuc")

    # 4-5. Coliche / Svezzamento
    c4 = st.columns(2)
    with c4[0]: r["coliche_gassose"] = _radio("4. Coliche gassose", ["no","sì"],
                                               _g(d,"coliche_gassose","no"), f"{px}_coliche")
    with c4[1]: r["eta_svezzamento"] = _inp("5. Età svezzamento",
                                             _g(d,"eta_svezzamento"), f"{px}_svez")

    # 6. Cibi solidi
    r["cibi_solidi_difficolta"] = _radio("6. Difficoltà con cibi solidi",
                                          ["no","sì"], _g(d,"cibi_solidi_difficolta","no"), f"{px}_solidi")

    # 7. Sviluppo motorio e linguaggio
    st.markdown("**7. Sviluppo**")
    c5 = st.columns(3)
    with c5[0]: r["eta_cammino"] = _inp("Età cammino", _g(d,"eta_cammino"), f"{px}_cammino")
    with c5[1]: r["eta_linguaggio"] = _inp("Età prime parole", _g(d,"eta_linguaggio"), f"{px}_ling")
    with c5[2]: r["ha_gattonato"] = _radio("Ha gattonato?", ["sì","no","parzialmente"],
                                            _g(d,"ha_gattonato","sì"), f"{px}_gatt")

    # 8-10. ORL
    st.markdown("**ORL**")
    c6 = st.columns(3)
    with c6[0]: r["otiti"] = _radio("8. Otiti", ["no","sì"], _g(d,"otiti","no"), f"{px}_otiti")
    with c6[1]:
        r["rumori_orecchio"] = _cb("9a. Rumori orecchio chiuso", _g(d,"rumori_orecchio"), f"{px}_rum")
        r["vertigini"] = _cb("9b. Vertigini", _g(d,"vertigini"), f"{px}_vert")
    with c6[2]:
        r["tonsille"] = _radio("10a. Tonsille", ["no","sì"], _g(d,"tonsille","no"), f"{px}_tons")
        r["adenoidi"] = _radio("Adenoidi", ["no","sì"], _g(d,"adenoidi","no"), f"{px}_aden")
        r["operato_orl"] = _cb("Operato ORL", _g(d,"operato_orl"), f"{px}_op_orl")

    # 11-12. Dolori
    st.markdown("**Dolori**")
    c7 = st.columns(2)
    with c7[0]:
        r["mal_di_testa"] = _radio("11. Mal di testa", ["no","sì"], _g(d,"mal_di_testa","no"), f"{px}_cef")
        if r["mal_di_testa"] == "sì":
            r["cefalea_note"] = _inp("Sede/frequenza/gravità", _g(d,"cefalea_note"), f"{px}_cef_n")
    with c7[1]:
        r["dolori_collo"] = _cb("12a. Dolori collo/spalle", _g(d,"dolori_collo"), f"{px}_coll")
        r["dolori_schiena"] = _cb("12b. Dolori schiena", _g(d,"dolori_schiena"), f"{px}_sch")
        r["dolori_gambe"] = _cb("12c. Dolori gambe", _g(d,"dolori_gambe"), f"{px}_gamb")

    # 13. Digestivo
    st.markdown("**13. Apparato digestivo**")
    c8 = st.columns(3)
    with c8[0]:
        r["gonfiore_stomaco"] = _cb("Gonfiore stomaco", _g(d,"gonfiore_stomaco"), f"{px}_gonf")
        r["emette_aria"] = _cb("Emette aria", _g(d,"emette_aria"), f"{px}_aria")
    with c8[1]:
        r["beve_durante_pasto"] = _cb("Beve durante pasto", _g(d,"beve_durante_pasto"), f"{px}_beve")
        r["mangia_carne"] = _radio("Mangia carne", ["sì","no","poco"],
                                   _g(d,"mangia_carne","sì"), f"{px}_carne")
    with c8[2]:
        r["velocita_pasto"] = _s("Velocità pasto", ["—","Normale","Lento","Veloce"],
                                  _g(d,"velocita_pasto","—"), f"{px}_vel")
        r["bocca_aperta_pasto"] = _cb("Bocca aperta durante il pasto", _g(d,"bocca_aperta_pasto"), f"{px}_bap")
        r["difficolta_deglutizione"] = _cb("Difficoltà deglutizione", _g(d,"difficolta_deglutizione"), f"{px}_deg_diff")
        r["colite"] = _cb("Colite", _g(d,"colite"), f"{px}_col")

    # 14. Ciclo (se pertinente)
    with st.expander("14. Ciclo mestruale (se pertinente)", expanded=False):
        r["dismenorrea"] = _radio("Dismenorrea", ["n.a.","no","sì"],
                                   _g(d,"dismenorrea","n.a."), f"{px}_dism")
        if r["dismenorrea"] == "sì":
            c9 = st.columns(4)
            with c9[0]: r["ciclo_intervallo"] = _inp("Intervallo", _g(d,"ciclo_intervallo"), f"{px}_ci")
            with c9[1]: r["ciclo_quantita"] = _inp("Quantità", _g(d,"ciclo_quantita"), f"{px}_cq")
            with c9[2]: r["ciclo_durata"] = _inp("Durata", _g(d,"ciclo_durata"), f"{px}_cd")
            with c9[3]: r["ciclo_dolore"] = _s("Dolore", ["—","Lieve","Moderato","Forte"],
                                                _g(d,"ciclo_dolore","—"), f"{px}_cdol")

    # 15-16. Posture e sonno
    st.markdown("**Postura e sonno**")
    c10 = st.columns(3)
    with c10[0]: r["bocca_aperta_tv"] = _radio("15. Bocca aperta davanti TV",
                                                ["no","sì"], _g(d,"bocca_aperta_tv","no"), f"{px}_tv")
    with c10[1]: r["dorme_bocca_aperta"] = _radio("16a. Dorme bocca aperta",
                                                   ["no","sì"], _g(d,"dorme_bocca_aperta","no"), f"{px}_dba")
    with c10[2]:
        r["russa"] = _cb("16b. Russa", _g(d,"russa"), f"{px}_russa")
        r["bruxismo"] = _cb("16c. Bruxismo", _g(d,"bruxismo"), f"{px}_brux")

    # 17-18. Abitudini viziate
    st.markdown("**17-18. Abitudini viziate**")
    c11 = st.columns(4)
    with c11[0]: r["suzione_pollice"] = _cb("Pollice", _g(d,"suzione_pollice"), f"{px}_poll")
    with c11[1]: r["suzione_labbra"] = _cb("Labbra", _g(d,"suzione_labbra"), f"{px}_lab")
    with c11[2]: r["suzione_lingua"] = _cb("Lingua", _g(d,"suzione_lingua"), f"{px}_ling2")
    with c11[3]: r["mangia_unghie"] = _cb("18. Mangia unghie", _g(d,"mangia_unghie"), f"{px}_ungh")

    # 19. Colonna e arti
    st.markdown("**19. Problemi colonna/arti**")
    c12 = st.columns(4)
    with c12[0]: r["problema_colonna"] = _cb("Colonna", _g(d,"problema_colonna"), f"{px}_col2")
    with c12[1]: r["problema_ginocchia"] = _cb("Ginocchia", _g(d,"problema_ginocchia"), f"{px}_gin")
    with c12[2]: r["problema_caviglie"] = _cb("Caviglie", _g(d,"problema_caviglie"), f"{px}_cav")
    with c12[3]: r["problema_piedi"] = _cb("Piedi", _g(d,"problema_piedi"), f"{px}_pied")

    # 20. Fonazione
    st.markdown("**20. Difficoltà di pronuncia**")
    fon_opts = ["T,D,L,N","Ci,Gi","R","M,P,F,V","Ch,Gh","S,Z,Sh"]
    r["difficolta_pronuncia"] = []
    fon_cols = st.columns(len(fon_opts))
    for i, opt in enumerate(fon_opts):
        with fon_cols[i]:
            if st.checkbox(opt, value=(opt in (_g(d,"difficolta_pronuncia",[]) or [])),
                          key=f"{px}_fon_{i}"):
                r["difficolta_pronuncia"].append(opt)

    # 21. Allergie / Asma
    c13 = st.columns(2)
    with c13[0]: r["raffreddore_allergico"] = _radio("21a. Raffreddore allergico",
                                                      ["no","sì"], _g(d,"raffreddore_allergico","no"), f"{px}_raff")
    with c13[1]: r["asma"] = _radio("21b. Asma", ["no","sì"], _g(d,"asma","no"), f"{px}_asma")

    # 22. Altro
    r["altro_note"] = _t("22. Altro (problemi che potrebbero influire sul trattamento)",
                          _g(d,"altro_note"), f"{px}_altro", height=68)

    return r


# ─────────────────────────────────────────────────────────────────────────────
# B. ESAME OBIETTIVO
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_esame_obiettivo(d: dict, px: str) -> dict:
    st.markdown("#### 🔍 B — Esame Obiettivo")
    r = {}

    # Osservazione generale
    st.markdown("**Osservazione Generale**")
    c = st.columns(3)
    with c[0]:
        r["tipologia_volto"] = _s("Tipologia volto", ["—","Dolicofaciale","Mesofaciale","Brachifaciale"],
                                   _g(d,"tipologia_volto","—"), f"{px}_tvol")
        r["respirazione_orale"] = _cb("Respirazione orale", _g(d,"respirazione_orale"), f"{px}_resp_or")
    with c[1]:
        r["atteggiamento_posturale"] = _t("Atteggiamento posturale",
                                           _g(d,"atteggiamento_posturale"), f"{px}_post", height=68)
    with c[2]:
        r["asimmetrie"] = []
        for asm in ["Orecchio più alto","Occhio più alto","Spalla più alta","Arto inferiore più corto"]:
            if st.checkbox(asm, value=(asm in (_g(d,"asimmetrie",[]) or [])),
                          key=f"{px}_asm_{asm[:4]}"):
                r["asimmetrie"].append(asm)

    c2 = st.columns(2)
    with c2[0]:
        r["masseteri_ipertrofici"] = _cb("Masseteri ipertrofici", _g(d,"masseteri_ipertrofici"), f"{px}_mass")
        r["smorfia_deglutizione"] = _cb("Smorfia in deglutizione", _g(d,"smorfia_deglutizione"), f"{px}_smorf")
    with c2[1]:
        r["competenza_labiale"] = _radio("Competenza labiale",
                                          ["Sì","No","Parziale"], _g(d,"competenza_labiale","Sì"), f"{px}_comp_lab")

    # Osservazione orale
    st.markdown("**Osservazione Orale**")
    col1, col2, col3 = st.columns(3)
    with col1:
        r["overjet"] = _n("1. Overjet (mm)", _g(d,"overjet"), f"{px}_overjet", -5, 20, 0.5, "%.1f")
        r["overbite"] = _n("2. Overbite (mm)", _g(d,"overbite"), f"{px}_overbite", -10, 15, 0.5, "%.1f")
        r["classe_dentaria"] = _s("3. Classe dentaria", ["—","I","II/1","II/2","III"],
                                   _g(d,"classe_dentaria","—"), f"{px}_classe")
    with col2:
        r["morso"] = _s("4. Morso", ["—","Normale","Aperto","Coperto"],
                         _g(d,"morso","—"), f"{px}_morso")
        r["morso_crociato"] = _s("5. Morso crociato", ["No","Monolaterale","Bilaterale"],
                                  _g(d,"morso_crociato","No"), f"{px}_mc")
        r["morso_inverso"] = _s("6. Morso inverso", ["No","Anteriore","Totale"],
                                 _g(d,"morso_inverso","No"), f"{px}_mi")
    with col3:
        r["mandibola"] = _s("7. Mandibola", ["—","Normale","Retrusa","Protrusa","Deviata DX","Deviata SX"],
                             _g(d,"mandibola","—"), f"{px}_mand")
        r["dimensione_verticale"] = _s("8. Dimensione verticale",
                                        ["Normale","Aumentata","Diminuita"],
                                        _g(d,"dimensione_verticale","Normale"), f"{px}_dv")

    col4, col5 = st.columns(2)
    with col4:
        r["affollamento"] = _radio("9. Affollamento dentario", ["No","Sì"], _g(d,"affollamento","No"), f"{px}_aff")
        r["diastemi"] = _cb("Diastemi", _g(d,"diastemi"), f"{px}_dias")
        r["palato"] = _s("10. Palato", ["Normale","Ristretto","Fortemente contratto"],
                          _g(d,"palato","Normale"), f"{px}_palato")
        r["depressione_molare"] = _s("11-12. Depressione molare",
                                      ["No","Monolaterale","Bilaterale"],
                                      _g(d,"depressione_molare","No"), f"{px}_depr")
    with col5:
        r["tonsille_obiettivo"] = _s("13. Tonsille", ["Normali","Ipertrofiche","Molto ipertrofiche","Assenti"],
                                      _g(d,"tonsille_obiettivo","Normali"), f"{px}_tons_obj")
        r["lingua_dimensione"] = _s("14a. Lingua dimensione", ["Normale","Macroglossia","Microglossia","Con impronte"],
                                     _g(d,"lingua_dimensione","Normale"), f"{px}_ling_dim")
        r["frenulo"] = _s("14b. Frenulo", ["Normale","Corto","Teso","Anchilotico"],
                           _g(d,"frenulo","Normale"), f"{px}_fren")

    # Posizione lingua a riposo
    st.markdown("**Posizione della Lingua a Riposo**")
    r["lingua_riposo"] = _s("Posizione",
                             ["—",
                              "1 — Tra i denti anteriori/laterali",
                              "2 — Contro i denti superiori",
                              "3 — Contro i denti inferiori",
                              "4 — Affondata nell'arcata inferiore (Spot OK)"],
                             _g(d,"lingua_riposo","—"), f"{px}_ling_rip")

    r["lingua_riposo_note"] = _inp("Note posizione lingua", _g(d,"lingua_riposo_note"), f"{px}_ling_n")

    # Misurazioni (dinamometria)
    st.markdown("**Misurazioni** (kg/forza)")
    c_mis = st.columns(5)
    for i, (label, key) in enumerate([
        ("Labbra dinam.", "mis_labbra_din"),
        ("Labbra compress.", "mis_labbra_comp"),
        ("Spinta linguale", "mis_spinta_ling"),
        ("Massetere DX", "mis_mass_dx"),
        ("Massetere SX", "mis_mass_sx"),
    ]):
        with c_mis[i]:
            r[key] = _n(label, _g(d, key), f"{px}_{key}", 0, 30, 0.5, "%.1f")

    return r


# ─────────────────────────────────────────────────────────────────────────────
# C. VALUTAZIONE FUNZIONALE
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_funzionale(d: dict, px: str) -> dict:
    st.markdown("#### ⚙️ C — Valutazione Funzionale")
    r = {}

    tab_deg, tab_resp, tab_fon, tab_fren = st.tabs([
        "Deglutizione", "Respirazione", "Fonazione", "Frenulo"
    ])

    with tab_deg:
        st.markdown("**Deglutizione**")
        r["deglutizione_tipo"] = _s("Tipo deglutizione",
                                     ["—","Corretta","Atipica con interposizione anteriore",
                                      "Atipica con interposizione laterale DX",
                                      "Atipica con interposizione laterale SX",
                                      "Atipica bilaterale","Con contrazione mimici"],
                                     _g(d,"deglutizione_tipo","—"), f"{px}_deg_tipo")
        c = st.columns(2)
        with c[0]:
            r["deglutizione_rumore"] = _cb("Rumore durante deglutizione", _g(d,"deglutizione_rumore"), f"{px}_deg_rum")
            r["deglutizione_sforzo"] = _cb("Sforzo visibile", _g(d,"deglutizione_sforzo"), f"{px}_deg_sf")
            r["deglutizione_mentale"] = _cb("Contrazione mentale", _g(d,"deglutizione_mentale"), f"{px}_deg_men")
        with c[1]:
            r["deglutizione_labiale"] = _cb("Contrazione labiale", _g(d,"deglutizione_labiale"), f"{px}_deg_lab")
            r["deglutizione_testa"] = _cb("Movimento testa", _g(d,"deglutizione_testa"), f"{px}_deg_test")
        r["deglutizione_note"] = _t("Note deglutizione", _g(d,"deglutizione_note"), f"{px}_deg_n")

    with tab_resp:
        st.markdown("**Respirazione**")
        c2 = st.columns(2)
        with c2[0]:
            r["respirazione_tipo"] = _s("Tipo",
                                         ["—","Nasale","Orale","Mista prevalentemente nasale",
                                          "Mista prevalentemente orale"],
                                         _g(d,"respirazione_tipo","—"), f"{px}_resp_tipo")
            r["respirazione_modo"] = _s("Modo",
                                         ["—","Costale superiore","Costale inferiore","Diaframmatica","Mista"],
                                         _g(d,"respirazione_modo","—"), f"{px}_resp_modo")
        with c2[1]:
            r["capacita_nasale"] = _radio("Capacità nasale DX",
                                          ["Normale","Ridotta","Assente"], _g(d,"capacita_nasale","Normale"), f"{px}_nas_dx")
            r["capacita_nasale_sx"] = _radio("Capacità nasale SX",
                                             ["Normale","Ridotta","Assente"], _g(d,"capacita_nasale_sx","Normale"), f"{px}_nas_sx")
        r["respirazione_note"] = _t("Note respirazione", _g(d,"respirazione_note"), f"{px}_resp_n")

    with tab_fon:
        st.markdown("**Fonazione e Pronuncia**")
        r["fonazione_voce"] = _s("Qualità voce",
                                  ["—","Normale","Nasalizzata","Iponasale","Roca","Soffiata"],
                                  _g(d,"fonazione_voce","—"), f"{px}_voce")
        st.markdown("Errori articolatori presenti:")
        fon_err = _g(d,"fonazione_errori",[]) or []
        errori = []
        cols_fon = st.columns(3)
        for i, fon in enumerate(["T/D","L/N","R","S/Z","Ci/Gi","Ch/Gh","M/P/F/V","Sh","Altro"]):
            with cols_fon[i%3]:
                if st.checkbox(fon, value=(fon in fon_err), key=f"{px}_ferr_{i}"):
                    errori.append(fon)
        r["fonazione_errori"] = errori
        r["fonazione_note"] = _t("Note fonazione", _g(d,"fonazione_note"), f"{px}_fon_n")

    with tab_fren:
        st.markdown("**Frenulo Linguale**")
        r["frenulo_classificazione"] = _s("Classificazione",
                                           ["—","Normale","Grado 1 (lievemente corto)",
                                            "Grado 2 (moderatamente corto)",
                                            "Grado 3 (corto con limitazione funzionale)",
                                            "Grado 4 (anchiloglossia totale)"],
                                           _g(d,"frenulo_classificazione","—"), f"{px}_fren_cl")
        c3 = st.columns(2)
        with c3[0]:
            r["frenulo_elevazione"] = _radio("Elevazione lingua al palato",
                                             ["Normale","Ridotta","Impossibile"],
                                             _g(d,"frenulo_elevazione","Normale"), f"{px}_fren_el")
            r["frenulo_protrusione"] = _radio("Protrusione oltre labbro",
                                              ["Normale","Ridotta","Impossibile"],
                                              _g(d,"frenulo_protrusione","Normale"), f"{px}_fren_pr")
        with c3[1]:
            r["frenulo_spot"] = _radio("Raggiunge lo spot palatino",
                                        ["Sì","No","Parzialmente"],
                                        _g(d,"frenulo_spot","Sì"), f"{px}_fren_sp")
            r["frenulo_intervento"] = _radio("Intervento indicato",
                                              ["No","Frenulotomia","Frenuloplastica","Da valutare"],
                                              _g(d,"frenulo_intervento","No"), f"{px}_fren_int")
        r["frenulo_note"] = _t("Note frenulo", _g(d,"frenulo_note"), f"{px}_fren_n")

    return r


# ─────────────────────────────────────────────────────────────────────────────
# D. DIAGNOSI FUNZIONALE E INDICE
# ─────────────────────────────────────────────────────────────────────────────

def _diagnosi_miofunzionale(anam: dict, obj: dict, funz: dict) -> list[dict]:
    """Genera ipotesi diagnostiche dai dati compilati."""
    diagnosi = []

    # Disfunzione deglutizione atipica
    deg = funz.get("deglutizione_tipo", "")
    if deg and "Atipica" in deg:
        criteri = [f"Deglutizione: {deg}"]
        if funz.get("smorfia_deglutizione") or obj.get("smorfia_deglutizione"):
            criteri.append("Smorfia mimica in deglutizione")
        if obj.get("morso") and obj["morso"] in ("Aperto","Coperto"):
            criteri.append(f"Morso {obj['morso']}")
        diagnosi.append({
            "titolo": "Deglutizione Atipica",
            "livello": "alta",
            "criteri": criteri,
            "note": "Indicato trattamento miofunzionale per rieducazione deglutitoria"
        })

    # Respirazione orale
    resp = funz.get("respirazione_tipo", "")
    if resp and "Orale" in resp:
        criteri = [f"Respirazione: {resp}"]
        if obj.get("lingua_riposo") and "Anteriore" in obj.get("lingua_riposo",""):
            criteri.append("Posizione lingua a riposo bassa/anteriore")
        if anam.get("tonsille") == "sì" or anam.get("adenoidi") == "sì":
            criteri.append("Ipertrofia tonsille/adenoidi in anamnesi")
        diagnosi.append({
            "titolo": "Respirazione Orale / Intercettazione",
            "livello": "alta" if len(criteri)>=2 else "media",
            "criteri": criteri,
            "note": "Valutare con ORL. Rieducazione respiratoria nasale."
        })

    # Frenulo corto
    fren = funz.get("frenulo_classificazione", "")
    if fren and "Grado" in fren:
        grado = int(fren.split("Grado ")[1][0]) if "Grado" in fren else 0
        diagnosi.append({
            "titolo": f"Frenulo Linguale Corto ({fren})",
            "livello": "alta" if grado >= 3 else "media",
            "criteri": [fren,
                        f"Elevazione: {funz.get('frenulo_elevazione','—')}",
                        f"Spot: {funz.get('frenulo_spot','—')}"],
            "note": f"Intervento indicato: {funz.get('frenulo_intervento','da valutare')}"
        })

    # Ipotono labiale
    if obj.get("competenza_labiale") in ("No","Parziale"):
        criteri = [f"Competenza labiale: {obj['competenza_labiale']}"]
        if anam.get("bocca_aperta_tv") == "sì": criteri.append("Bocca aperta davanti TV")
        if anam.get("dorme_bocca_aperta") == "sì": criteri.append("Dorme a bocca aperta")
        diagnosi.append({
            "titolo": "Ipotono / Incompetenza Labiale",
            "livello": "media",
            "criteri": criteri,
            "note": "Esercizi di rinforzo orbicolare"
        })

    # Bruxismo
    if anam.get("bruxismo"):
        diagnosi.append({
            "titolo": "Bruxismo",
            "livello": "media",
            "criteri": ["Bruxismo riferito in anamnesi"],
            "note": "Valutare correlazione con disfunzione ATM e postura"
        })

    # Disfunzione ATM / Dolori
    if anam.get("dolori_collo") or anam.get("dolori_schiena"):
        criteri = []
        if anam.get("dolori_collo"): criteri.append("Dolori collo/spalle")
        if anam.get("dolori_schiena"): criteri.append("Dolori schiena")
        if obj.get("mandibola") != "Normale": criteri.append(f"Mandibola {obj.get('mandibola')}")
        if criteri:
            diagnosi.append({
                "titolo": "Possibile Componente Posturale / Disfunzione ATM",
                "livello": "media",
                "criteri": criteri,
                "note": "Valutazione posturologica integrata"
            })

    return diagnosi


def _render_diagnosi_mft(diagnosi: list):
    st.markdown("#### 🩺 D — Diagnosi Funzionale")
    if not diagnosi:
        st.success("✅ Nessun pattern disfunzionale rilevato dai dati inseriti.")
        return
    for d in diagnosi:
        ico = {"alta":"🔴","media":"🟡","bassa":"🟢"}.get(d["livello"],"ℹ️")
        tipo = {"alta":"error","media":"warning","bassa":"info"}.get(d["livello"],"info")
        getattr(st, tipo)(f"{ico} **{d['titolo']}** — {d['livello'].upper()}")
        for c in d.get("criteri",[]):
            st.markdown(f"  ✓ {c}")
        if d.get("note"):
            st.caption(f"💡 {d['note']}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_miofunzionale(
    data_json: dict | None,
    prefix: str,
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Entry point — Terapia Miofunzionale completa.
    data_json: dict salvato in pnev_json["miofunzionale"] o {}
    """
    if data_json is None:
        data_json = {}

    st.markdown("## 👄 Valutazione Miofunzionale")
    st.caption("Scheda Dr. Antonio Ferrante — Anamnesi MFT + Esame Obiettivo + Valutazione Funzionale")

    tabs = st.tabs([
        "📋 A — Anamnesi",
        "🔍 B — Esame Obiettivo",
        "⚙️ C — Valutazione Funzionale",
        "🩺 D — Diagnosi",
    ])

    nuovi = dict(data_json)

    with tabs[0]:
        nuovi["anamnesi"] = _sezione_anamnesi(data_json.get("anamnesi",{}), f"{prefix}_a")

    with tabs[1]:
        nuovi["esame_obiettivo"] = _sezione_esame_obiettivo(data_json.get("esame_obiettivo",{}), f"{prefix}_b")

    with tabs[2]:
        nuovi["funzionale"] = _sezione_funzionale(data_json.get("funzionale",{}), f"{prefix}_c")

    with tabs[3]:
        diag = _diagnosi_miofunzionale(
            nuovi.get("anamnesi",{}),
            nuovi.get("esame_obiettivo",{}),
            nuovi.get("funzionale",{}),
        )
        _render_diagnosi_mft(diag)
        nuovi["diagnosi"] = diag

    nuovi["_meta"] = {"data": date.today().isoformat(), "versione": "mft_v1"}

    # Summary
    deg = nuovi.get("funzionale",{}).get("deglutizione_tipo","—")
    resp = nuovi.get("funzionale",{}).get("respirazione_tipo","—")
    fren = nuovi.get("funzionale",{}).get("frenulo_classificazione","—")
    n_diag = len(diag)
    summary = f"MFT: Deg={deg[:20] if deg!='—' else 'nd'} | Resp={resp[:15] if resp!='—' else 'nd'}"
    if fren and fren != "—": summary += f" | {fren[:20]}"
    if n_diag: summary += f" | {n_diag} diagnosi"

    return nuovi, summary
