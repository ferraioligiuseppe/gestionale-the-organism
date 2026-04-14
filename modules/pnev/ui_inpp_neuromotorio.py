# -*- coding: utf-8 -*-
"""
ui_inpp_neuromotorio.py — Valutazione Neurologica INPP (Goddard Blythe)
Implementa la scheda diagnostica completa INPP (ISND 2009-2022)

Struttura:
  A. Coordinazione grosso-motoria ed equilibrio (test 1-10)
  B. Schemi di sviluppo motorio (striscio, carponi)
  C. Test funzionalità cerebellare (tallone-tibia, disdiadococinesia)
  D. Riflessi primitivi (RTAC/ATNR, RTSC/STNR, RTL/TLR, Moro, Galant, ...)
  E. Riflessi posturali (Landau, Anfibio, Rotazione segmentaria, Sostegno cefalico)
  F. Riflessi orali (Rooting, Suzione, Prensile)
  G. Lateralità (occhio, mano, piede)
  H. Valutazione oculo-motoria (fissazione, tracking, saccadi)
  INDICE DI DISFUNZIONE → calcolo automatico + interpretazione

Punteggio INPP:
  0 = N.A. (Nessuna Anomalia)
  1 = Disfunzione 25%
  2 = Disfunzione 50%
  3 = Disfunzione 75%
  4 = Disfunzione 100%
  (Per riflessi posturali: il punteggio si inverte)
"""

from __future__ import annotations
from datetime import date
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

SCORE_OPTS = ["0 — N.A.", "1 — 25%", "2 — 50%", "3 — 75%", "4 — 100%"]
LATO_OPTS  = ["—", "DX", "SX", "Bilaterale", "Non testabile"]
SCHEMA_OPTS = ["—", "Omologo", "Omolaterale", "Incrociato", "Incrociato non sincronizzato"]

def _g(d, *keys, default=0):
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k, default)
    return d if d is not None else default

def _score(label: str, val: int, key: str, help_txt: str = "") -> int:
    """Selectbox 0-4 con ritorno int."""
    idx = max(0, min(4, int(val or 0)))
    scelta = st.selectbox(label, SCORE_OPTS, index=idx, key=key,
                          help=help_txt if help_txt else None)
    return int(scelta[0])

def _score_row(label: str, val: int, key: str, note_val: str = "", note_key: str = "") -> tuple[int, str]:
    """Riga con score + nota inline."""
    c1, c2 = st.columns([2, 3])
    with c1:
        sc = _score(label, val, key)
    with c2:
        nota = st.text_input("Note", value=str(note_val or ""),
                             key=note_key or f"{key}_nota",
                             label_visibility="collapsed",
                             placeholder="Osservazioni cliniche...")
    return sc, nota

def _lato(label: str, val: str, key: str) -> str:
    idx = LATO_OPTS.index(val) if val in LATO_OPTS else 0
    return st.selectbox(label, LATO_OPTS, index=idx, key=key)

def _interpreta_indice(indice: float) -> tuple[str, str]:
    """Interpreta l'indice di disfunzione INPP (%)."""
    if indice <= 10:  return "✅ Nella norma", "success"
    if indice <= 25:  return "🟡 Lieve disfunzione neuromotoria", "warning"
    if indice <= 50:  return "🟠 Moderata disfunzione neuromotoria", "warning"
    if indice <= 75:  return "🔴 Significativa disfunzione neuromotoria", "error"
    return "🔴🔴 Grave disfunzione neuromotoria", "error"


# ─────────────────────────────────────────────────────────────────────────────
# A. COORDINAZIONE GROSSO-MOTORIA ED EQUILIBRIO
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_coordinazione(d: dict, px: str) -> tuple[dict, list]:
    st.markdown("#### 🏃 A — Coordinazione Grosso-Motoria ed Equilibrio")
    scores = []
    res = {}

    tests = [
        ("rec_supino",    "1. Recupero posizione verticale da supino",
         "Sequenza normale: testa→tronco→mani come appoggio→piedi. C'è posizione W (RTSC)?"),
        ("rec_prono",     "2. Recupero posizione verticale da prono",
         "Sequenza: appoggio su braccia, piega ginocchia, spinge fino ad alzarsi."),
        ("romberg",       "3. Test di Romberg (piedi uniti, occhi chiusi 10s)",
         "Dondolio? Verso quale lato? Aggiustamento posturale?"),
        ("mann",          "4. Test di Mann / Romberg avanzato (tandem, tallone-punta)",
         "Sistema vestibolare adatta al cambio di posizione? Problemi linea media?"),
    ]

    for key, label, help_txt in tests:
        with st.container():
            sc, nota = _score_row(label, _g(d, key, "score"), f"{px}_{key}",
                                  _g(d, key, "nota", default=""), f"{px}_{key}_nota")
            res[key] = {"score": sc, "nota": nota}
            scores.append(sc)

    # Test su un piede (con tempi)
    st.markdown("**5. Test su un solo piede (UPST)** — norme: 6 anni=20s, 8+ anni=30s")
    c = st.columns(4)
    with c[0]: upst_dx = st.number_input("DX (sec)", 0.0, 60.0,
                                          float(_g(d,"upst","dx",default=0)), 0.5, "%.1f",
                                          key=f"{px}_upst_dx")
    with c[1]: upst_sx = st.number_input("SX (sec)", 0.0, 60.0,
                                          float(_g(d,"upst","sx",default=0)), 0.5, "%.1f",
                                          key=f"{px}_upst_sx")
    with c[2]: upst_score = _score("Score", _g(d,"upst","score"), f"{px}_upst_sc")
    with c[3]: upst_nota = st.text_input("Note", _g(d,"upst","nota",default=""),
                                          key=f"{px}_upst_nota", label_visibility="collapsed",
                                          placeholder="Note...")
    res["upst"] = {"dx": upst_dx, "sx": upst_sx, "score": upst_score, "nota": upst_nota}
    scores.append(upst_score)

    # Cammino e mezzo giro
    sc6, n6 = _score_row("6. Cammino e mezzo giro",
                          _g(d,"cammino_giro","score"), f"{px}_cammino_giro",
                          _g(d,"cammino_giro","nota",default=""))
    res["cammino_giro"] = {"score": sc6, "nota": n6}
    scores.append(sc6)
    st.caption("Schema incrociato? Omolaterale dopo il giro? Diventa RTSC nella postura?")

    # Cammino sulle punte (avanti + indietro)
    st.markdown("**7. Cammino sulle punte**")
    c2 = st.columns(3)
    with c2[0]: cp_av = _score("Avanti", _g(d,"punte","avanti"), f"{px}_punte_av")
    with c2[1]: cp_in = _score("Indietro", _g(d,"punte","indietro"), f"{px}_punte_in")
    with c2[2]: cp_n = st.text_input("Note", _g(d,"punte","nota",default=""),
                                      key=f"{px}_punte_nota", label_visibility="collapsed",
                                      placeholder="Riflesso prensile piedi? Deviazione?")
    res["punte"] = {"avanti": cp_av, "indietro": cp_in, "nota": cp_n}
    scores.extend([cp_av, cp_in])

    # Cammino sui talloni
    sc8, n8 = _score_row("8. Cammino sui talloni",
                          _g(d,"talloni","score"), f"{px}_talloni",
                          _g(d,"talloni","nota",default=""))
    res["talloni"] = {"score": sc8, "nota": n8}
    scores.append(sc8)

    # Saltelli su un piede
    st.markdown("**9. Saltelli su un piede**")
    c3 = st.columns(3)
    with c3[0]: salt_dx = _score("DX", _g(d,"saltelli","dx"), f"{px}_salt_dx")
    with c3[1]: salt_sx = _score("SX", _g(d,"saltelli","sx"), f"{px}_salt_sx")
    with c3[2]: salt_n = st.text_input("Note", _g(d,"saltelli","nota",default=""),
                                        key=f"{px}_salt_nota", label_visibility="collapsed",
                                        placeholder="Note saltelli...")
    res["saltelli"] = {"dx": salt_dx, "sx": salt_sx, "nota": salt_n}
    scores.extend([salt_dx, salt_sx])

    # Skip/Galoppo
    sc10, n10 = _score_row("10. Skip / Galoppo",
                            _g(d,"skip","score"), f"{px}_skip",
                            _g(d,"skip","nota",default=""))
    res["skip"] = {"score": sc10, "nota": n10}
    scores.append(sc10)

    return res, scores


# ─────────────────────────────────────────────────────────────────────────────
# B. SCHEMI DI SVILUPPO MOTORIO
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_schemi_motori(d: dict, px: str) -> dict:
    st.markdown("#### 🐛 B — Schemi di Sviluppo Motorio")
    res = {}

    st.markdown("**Striscio** (omologo / omolaterale / incrociato / sincronizzato?)")
    c = st.columns(2)
    with c[0]: str_schema = st.selectbox("Schema", SCHEMA_OPTS,
                                          index=SCHEMA_OPTS.index(_g(d,"striscio","schema","—"))
                                          if _g(d,"striscio","schema","—") in SCHEMA_OPTS else 0,
                                          key=f"{px}_striscio_schema")
    with c[1]: str_nota = st.text_input("Note striscio", _g(d,"striscio","nota",default=""),
                                         key=f"{px}_striscio_nota", label_visibility="collapsed",
                                         placeholder="Osservazioni...")
    res["striscio"] = {"schema": str_schema, "nota": str_nota}

    st.markdown("**Carponi** (schema incrociato? sincronizzato? evidenza RTSC?)")
    c2 = st.columns(2)
    with c2[0]: carp_schema = st.selectbox("Schema", SCHEMA_OPTS,
                                            index=SCHEMA_OPTS.index(_g(d,"carponi","schema","—"))
                                            if _g(d,"carponi","schema","—") in SCHEMA_OPTS else 0,
                                            key=f"{px}_carponi_schema")
    with c2[1]: carp_nota = st.text_input("Note carponi", _g(d,"carponi","nota",default=""),
                                           key=f"{px}_carponi_nota", label_visibility="collapsed",
                                           placeholder="Evidenza RTSC? Passo dell'orso?")
    res["carponi"] = {"schema": carp_schema, "nota": carp_nota}

    return res


# ─────────────────────────────────────────────────────────────────────────────
# C. TEST FUNZIONALITÀ CEREBELLARE
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_cerebellare(d: dict, px: str) -> tuple[dict, list]:
    st.markdown("#### 🧠 C — Test Funzionalità Cerebellare")
    scores = []
    res = {}

    # Tallone su tibia
    st.markdown("**Test Tallone su Tibia**")
    st.caption("Scivolare tallone lungo tibia dall'alto al basso. Atassia? Dissinergia? Si alza il tallone opposto?")
    c = st.columns(3)
    with c[0]: tib_dx, n_dx = _score_row("DX", _g(d,"tallone_tibia","dx"), f"{px}_tib_dx")
    with c[1]: tib_sx, n_sx = _score_row("SX", _g(d,"tallone_tibia","sx"), f"{px}_tib_sx")
    with c[2]: tib_nota = st.text_input("Note", _g(d,"tallone_tibia","nota",default=""),
                                         key=f"{px}_tib_nota", label_visibility="collapsed",
                                         placeholder="Asimmetria? Atassia?")
    res["tallone_tibia"] = {"dx": tib_dx, "sx": tib_sx, "nota": tib_nota}
    scores.extend([tib_dx, tib_sx])

    # Disdiadococinesia
    st.markdown("**Test di Disdiadococinesia** (pronazione/supinazione rapida mani)")
    c2 = st.columns(3)
    with c2[0]: dis_dx = _score("DX", _g(d,"disdiadoco","dx"), f"{px}_dis_dx")
    with c2[1]: dis_sx = _score("SX", _g(d,"disdiadoco","sx"), f"{px}_dis_sx")
    with c2[2]: dis_nota = st.text_input("Note", _g(d,"disdiadoco","nota",default=""),
                                          key=f"{px}_dis_nota", label_visibility="collapsed",
                                          placeholder="Irregolarità? Asimmetria?")
    res["disdiadoco"] = {"dx": dis_dx, "sx": dis_sx, "nota": dis_nota}
    scores.extend([dis_dx, dis_sx])

    # Test di Hoff-Schilder (RTAC)
    st.markdown("**Test di Hoff-Schilder** (braccia tese, occhi chiusi, rotazione testa)")
    st.caption("Si muovono le braccia seguendo la rotazione della testa? (Indicatore RTAC residuo)")
    c3 = st.columns(3)
    with c3[0]: hoff_dx = _score("Rotaz. DX", _g(d,"hoff_schilder","dx"), f"{px}_hoff_dx")
    with c3[1]: hoff_sx = _score("Rotaz. SX", _g(d,"hoff_schilder","sx"), f"{px}_hoff_sx")
    with c3[2]: hoff_nota = st.text_input("Note", _g(d,"hoff_schilder","nota",default=""),
                                           key=f"{px}_hoff_nota", label_visibility="collapsed",
                                           placeholder="Gradi di rotazione braccio?")
    res["hoff_schilder"] = {"dx": hoff_dx, "sx": hoff_sx, "nota": hoff_nota}
    scores.extend([hoff_dx, hoff_sx])

    return res, scores


# ─────────────────────────────────────────────────────────────────────────────
# D. RIFLESSI PRIMITIVI
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_riflessi_primitivi(d: dict, px: str) -> tuple[dict, list]:
    st.markdown("#### 🔄 D — Riflessi Primitivi")
    scores = []
    res = {}

    riflessi = [
        ("rtac_supino",   "RTAC / ATNR — Test Standard (supino)",
         "Rotazione testa → movimento dita/braccio frontale? Inibizione: 3-6/9 mesi."),
        ("rtac_ayres1",   "RTAC / ATNR — Test di Ayres 1 (quadrupede)",
         "In posizione quadrupede: rotazione testa → flessione braccio omolaterale?"),
        ("rtac_ayres2",   "RTAC / ATNR — Test di Ayres 2 (variante)",
         "Come Ayres 1 ma in posizione diversa. Valido dai 4-5 anni."),
        ("rttc",          "RTTC — Riflesso Tonico Trasformato del Collo",
         "Posizione di recupero (recovery position): è comoda? Arti raggiungono posizione corretta?"),
        ("rtsc",          "RTSC / STNR — Test in posizione quadrupede",
         "Flessione/estensione testa → flessione braccia o abbassamento bacino?"),
        ("rtl_supino",    "RTL / TLR — Test Standard (supino)",
         "Estensione collo → aumento tono muscolare gambe?"),
        ("rtl_piedi",     "RTL / TLR — Test in piedi",
         "Testa su/giù → cambiamento tono muscolare gambe? Con occhi chiusi?"),
        ("moro_supino",   "Moro — Test Standard (supino, testa cade indietro)",
         "Abduzione arti superiori quando la testa cade indietro inaspettatamente?"),
        ("moro_piedi",    "Moro — Test in piedi (Bennett-Clarke-Rowston)",
         "Movimento braccia come risposta a caduta inattesa della testa?"),
        ("galant",        "Riflesso Spinal Galant",
         "Stimolazione paravertebrale → spostamento laterale bacino ipsilaterale?"),
        ("babinski",      "Riflesso di Babinski",
         "Stimolazione pianta piede → estensione alluce + apertura dita?"),
        ("rooting",       "Riflesso di Ricerca (Rooting / Punti Cardinali)",
         "Stimolazione angoli bocca → movimento labbra verso stimolo?"),
        ("suzione",       "Riflesso di Suzione",
         "Stimolazione piega naso-labiale → labbra in avanti?"),
        ("prensile_mano", "Riflesso Prensile Palmare",
         "Stimolazione palmo → flessione pollice/dita verso palmo?"),
        ("prensile_piede","Riflesso Prensile Plantare (Book test)",
         "Peso sulle punte dei piedi → flessione dita dei piedi?"),
    ]

    for key, label, help_txt in riflessi:
        with st.expander(f"**{label}**", expanded=False):
            st.caption(help_txt)
            c = st.columns([1, 1, 2])
            with c[0]:
                sc = _score("Score", _g(d, key, "score"), f"{px}_{key}_sc")
            with c[1]:
                lato = _lato("Lato prevalente", _g(d, key, "lato", default="—"), f"{px}_{key}_lato")
            with c[2]:
                nota = st.text_input("Osservazioni", _g(d, key, "nota", default=""),
                                     key=f"{px}_{key}_nota", label_visibility="collapsed",
                                     placeholder="Descrivi la risposta osservata...")
            res[key] = {"score": sc, "lato": lato, "nota": nota}
            scores.append(sc)

    return res, scores


# ─────────────────────────────────────────────────────────────────────────────
# E. RIFLESSI POSTURALI
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_riflessi_posturali(d: dict, px: str) -> tuple[dict, list]:
    st.markdown("#### 🏗️ E — Riflessi Posturali")
    st.caption("⚠️ Per i riflessi posturali il punteggio si **inverte**: 4=assente (peggio), 0=completamente presente (norma per età)")
    scores = []
    res = {}

    posturali = [
        ("landau",         "Riflesso di Landau",
         "Posizione prona: solleva tronco → si sollevano i piedi?"),
        ("anfibio_supino", "Riflesso Anfibio — Supino",
         "Lento sollevamento bacino → flessione omolaterale arto?"),
        ("anfibio_prono",  "Riflesso Anfibio — Prono",
         "Come sopra ma in posizione prona."),
        ("rot_bacino",     "Rotazione Segmentaria dal Bacino",
         "Flessione gamba attraverso il corpo → rotazione sequenziale tronco superiore?"),
        ("rot_spalle",     "Rotazione Segmentaria dalle Spalle",
         "Rotazione spalle → rotazione sequenziale tronco inferiore?"),
        ("sost_cef_oculare","Sostegno Cefalico Oculare (Raddrizzamento cervicale)",
         "Inclinazione corpo → testa si raddrizza in direzione opposta? (occhi aperti)"),
        ("sost_cef_labirintico","Sostegno Cefalico Labirintico",
         "Come sopra ma ad occhi chiusi (sistema vestibolare)."),
    ]

    for key, label, help_txt in posturali:
        with st.expander(f"**{label}**", expanded=False):
            st.caption(help_txt)
            sc, nota = _score_row(f"Score (0=normale, 4=assente)", _g(d, key, "score"),
                                   f"{px}_{key}_sc", _g(d, key, "nota", default=""))
            res[key] = {"score": sc, "nota": nota}
            scores.append(sc)

    return res, scores


# ─────────────────────────────────────────────────────────────────────────────
# F. LATERALITÀ
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_lateralita(d: dict, px: str) -> dict:
    st.markdown("#### 👁️ F — Lateralità")
    res = {}

    st.markdown("**Dominanza Oculare**")
    c = st.columns(3)
    with c[0]: dom_oc_lon = _lato("Lontano (cannocchiale/anello)", _g(d,"dom_occhio","lontano","—"), f"{px}_doc_lon")
    with c[1]: dom_oc_vic = _lato("Vicino (cartoncino/foro)", _g(d,"dom_occhio","vicino","—"), f"{px}_doc_vic")
    with c[2]: dom_oc_nota = st.text_input("Note", _g(d,"dom_occhio","nota",""), key=f"{px}_doc_nota",
                                            label_visibility="collapsed", placeholder="Note...")
    res["dom_occhio"] = {"lontano": dom_oc_lon, "vicino": dom_oc_vic, "nota": dom_oc_nota}

    st.markdown("**Dominanza Manuale**")
    c2 = st.columns(3)
    with c2[0]: dom_mano_scr = _lato("Scrittura", _g(d,"dom_mano","scrittura","—"), f"{px}_dm_scr")
    with c2[1]: dom_mano_pall = _lato("Prendere una palla", _g(d,"dom_mano","palla","—"), f"{px}_dm_pall")
    with c2[2]: dom_mano_app = _lato("Applauso (mano attiva)", _g(d,"dom_mano","applauso","—"), f"{px}_dm_app")
    res["dom_mano"] = {"scrittura": dom_mano_scr, "palla": dom_mano_pall, "applauso": dom_mano_app}

    st.markdown("**Dominanza Pedale**")
    c3 = st.columns(3)
    with c3[0]: dom_pi_calc = _lato("Calciare una palla", _g(d,"dom_piede","calcio","—"), f"{px}_dp_calc")
    with c3[1]: dom_pi_salt = _lato("Saltellare", _g(d,"dom_piede","saltello","—"), f"{px}_dp_salt")
    with c3[2]: dom_pi_sca = _lato("Salire su sedia", _g(d,"dom_piede","sedia","—"), f"{px}_dp_sca")
    res["dom_piede"] = {"calcio": dom_pi_calc, "saltello": dom_pi_salt, "sedia": dom_pi_sca}

    # Lateralità incrociata
    def _lat_consistente(occhio, mano, piede):
        vals = [v for v in [occhio, mano, piede] if v in ("DX","SX")]
        if len(vals) < 2: return "—"
        return "✅ Omolaterale" if len(set(vals)) == 1 else "⚠️ Incrociata"

    lat_stato = _lat_consistente(dom_oc_lon, dom_mano_scr, dom_pi_calc)
    if lat_stato != "—":
        if "✅" in lat_stato: st.success(f"Lateralità: {lat_stato}")
        else: st.warning(f"Lateralità: {lat_stato} — associata a RTAC residuo se > 8 anni")

    res["lateralita_consistente"] = lat_stato
    return res


# ─────────────────────────────────────────────────────────────────────────────
# G. VALUTAZIONE OCULO-MOTORIA
# ─────────────────────────────────────────────────────────────────────────────

def _sezione_oculomotoria(d: dict, px: str) -> tuple[dict, list]:
    st.markdown("#### 👁️ G — Valutazione Oculo-Motoria")
    scores = []
    res = {}

    oculo_tests = [
        ("fissazione",    "Fissazione",
         "Occhi allineati? Movimenti di aggiustamento? Convergenza/divergenza? Chiusura palpebre?"),
        ("tracking",      "Tracking / Inseguimento",
         "Movimenti di rifissazione (saccadi)? Perdita del target? Movimenti della testa?"),
        ("saccadi",       "Saccadi",
         "Precisione? Ipometria/ipermetria? Movimenti della testa compensatori?"),
        ("convergenza",   "Convergenza",
         "PPC cm: rot./rec. Sintomi durante la convergenza? (RTSC)"),
        ("divergenza",    "Divergenza",
         "Foria associata? Diplopia?"),
    ]

    for key, label, help_txt in oculo_tests:
        with st.expander(f"**{label}**", expanded=False):
            st.caption(help_txt)
            sc, nota = _score_row("Score", _g(d, key, "score"), f"{px}_{key}_sc",
                                   _g(d, key, "nota", default=""))
            res[key] = {"score": sc, "nota": nota}
            scores.append(sc)

    # PPC specifico
    st.markdown("**PPC — Punto Prossimo di Convergenza**")
    c = st.columns(3)
    with c[0]: ppc_rot = st.number_input("Rottura (cm)", 0.0, 50.0,
                                          float(_g(d,"ppc","rottura",default=0)), 0.5, "%.1f",
                                          key=f"{px}_ppc_rot")
    with c[1]: ppc_rec = st.number_input("Recupero (cm)", 0.0, 50.0,
                                          float(_g(d,"ppc","recupero",default=0)), 0.5, "%.1f",
                                          key=f"{px}_ppc_rec")
    with c[2]: ppc_occhio = st.selectbox("Occhio che devia", ["—","OD","OS","Alt"],
                                          key=f"{px}_ppc_occhio")
    res["ppc"] = {"rottura": ppc_rot, "recupero": ppc_rec, "occhio": ppc_occhio}

    return res, scores


# ─────────────────────────────────────────────────────────────────────────────
# CALCOLO INDICE DI DISFUNZIONE
# ─────────────────────────────────────────────────────────────────────────────

def _calcola_indice(scores_primitivi: list, scores_posturali: list,
                    scores_coord: list, scores_cerebellare: list,
                    scores_oculomotori: list) -> dict:
    """
    Calcola l'Indice di Disfunzione INPP.
    Punteggio massimo teorico = n_test × 4
    Indice = (somma punteggi / max teorico) × 100
    """
    tutti = scores_coord + scores_cerebellare + scores_primitivi + scores_posturali + scores_oculomotori

    n = len(tutti)
    if n == 0:
        return {"indice": 0, "somma": 0, "max": 0, "n_test": 0}

    somma = sum(tutti)
    max_score = n * 4
    indice = round(somma / max_score * 100, 1)

    # Breakdown per categoria
    def _cat_indice(scores):
        if not scores: return 0
        return round(sum(scores) / (len(scores)*4) * 100, 1)

    return {
        "indice": indice,
        "somma": somma,
        "max": max_score,
        "n_test": n,
        "breakdown": {
            "coordinazione": _cat_indice(scores_coord),
            "cerebellare": _cat_indice(scores_cerebellare),
            "primitivi": _cat_indice(scores_primitivi),
            "posturali": _cat_indice(scores_posturali),
            "oculomotori": _cat_indice(scores_oculomotori),
        }
    }


def _render_indice(calc: dict):
    st.markdown("#### 📊 Indice di Disfunzione INPP")

    indice = calc.get("indice", 0)
    txt, tipo = _interpreta_indice(indice)
    getattr(st, tipo)(f"**Indice di Disfunzione: {indice}%** — {txt}")

    c = st.columns(5)
    bd = calc.get("breakdown", {})
    labels = [("Coord.", "coordinazione"), ("Cerebellare", "cerebellare"),
              ("R. Primitivi", "primitivi"), ("R. Posturali", "posturali"),
              ("Oculomotori", "oculomotori")]
    for i, (label, key) in enumerate(labels):
        c[i].metric(label, f"{bd.get(key, 0):.0f}%")

    st.caption(f"Somma punteggi: {calc.get('somma',0)} / {calc.get('max',0)} "
               f"({calc.get('n_test',0)} test valutati)")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_inpp_neuromotorio(
    data_json: dict | None,
    prefix: str,
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Entry point — Valutazione Neurologica INPP completa.
    data_json: dict salvato in pnev_json["inpp_neuromotorio"] o {}
    """
    if data_json is None:
        data_json = {}

    st.markdown("## 🧠 Valutazione Neurologica INPP (Goddard Blythe)")
    st.caption(
        "Scheda diagnostica INPP (ISND 2009-2022). Punteggio 0-4: "
        "0=N.A. · 1=25% · 2=50% · 3=75% · 4=100%. "
        "Tutti i test scalzi con vestiti comodi. Genitore presente."
    )

    tabs = st.tabs([
        "🏃 A — Coordinazione",
        "🐛 B — Sviluppo Motorio",
        "🧠 C — Cerebellare",
        "🔄 D — Riflessi Primitivi",
        "🏗️ E — Riflessi Posturali",
        "👁️ F — Lateralità",
        "👁️ G — Oculomotoria",
        "📊 Indice Disfunzione",
    ])

    nuovi = dict(data_json)

    with tabs[0]:
        res_a, sc_coord = _sezione_coordinazione(data_json.get("coordinazione", {}), f"{prefix}_a")
        nuovi["coordinazione"] = res_a

    with tabs[1]:
        res_b = _sezione_schemi_motori(data_json.get("schemi_motori", {}), f"{prefix}_b")
        nuovi["schemi_motori"] = res_b

    with tabs[2]:
        res_c, sc_cereb = _sezione_cerebellare(data_json.get("cerebellare", {}), f"{prefix}_c")
        nuovi["cerebellare"] = res_c

    with tabs[3]:
        res_d, sc_prim = _sezione_riflessi_primitivi(data_json.get("primitivi", {}), f"{prefix}_d")
        nuovi["primitivi"] = res_d

    with tabs[4]:
        res_e, sc_post = _sezione_riflessi_posturali(data_json.get("posturali", {}), f"{prefix}_e")
        nuovi["posturali"] = res_e

    with tabs[5]:
        res_f = _sezione_lateralita(data_json.get("lateralita", {}), f"{prefix}_f")
        nuovi["lateralita"] = res_f

    with tabs[6]:
        res_g, sc_ocul = _sezione_oculomotoria(data_json.get("oculomotoria", {}), f"{prefix}_g")
        nuovi["oculomotoria"] = res_g

    with tabs[7]:
        calc = _calcola_indice(sc_prim, sc_post, sc_coord, sc_cereb, sc_ocul)
        _render_indice(calc)
        nuovi["indice_disfunzione"] = calc

    nuovi["_meta"] = {"data": date.today().isoformat(), "versione": "inpp_v1"}

    # Summary
    indice = nuovi.get("indice_disfunzione", {}).get("indice", 0)
    txt_ris, _ = _interpreta_indice(indice)
    
    # Riflessi più significativi
    rf_sig = []
    for key in ["rtac_supino","rtsc","rtl_supino","moro_supino","galant"]:
        sc = nuovi.get("primitivi",{}).get(key,{}).get("score",0)
        if sc >= 2:
            rf_sig.append(f"{key.replace('_',' ')} ({sc})")

    summary = f"INPP: Indice {indice}% — {txt_ris}"
    if rf_sig:
        summary += f" | RF attivi: {', '.join(rf_sig[:3])}"

    return nuovi, summary
