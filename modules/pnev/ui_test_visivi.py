# -*- coding: utf-8 -*-
"""
ui_test_visivi.py — Test Visivi con Scoring Automatico
Test implementati con norme e calcolo risultato automatico:
  1. DEM  — Developmental Eye Movement Test
  2. K-D  — King-Devick Saccade Test
  3. NSUCO — Oculomotor Test (saccadi + pursuit, scala 1-5)
  4. GROFFMAN — Visual Tracing Test
  5. PPA  — Punto Prossimo di Accomodazione
  6. Focus Flexibility (flessibilità accomodativa)
  7. Fusion Flexibility
  8. TVPS-3 — Test of Visual Perceptual Skills (7 subtest)
  9. AVIT  — Integrazione Visuo-Uditiva (Birch & Belmont)
  10. VADS — Visuo-Auditory Digit Span
  11. VMI  — Visual Motor Integration (punteggio grezzo → standard)
  12. Gardner Reversal Frequency Test
  13. WACHS — Visual Analysis Skills

Ogni test: insert(pnev_json, prefix, existing) → (dict, summary)
Entry point: render_test_visivi(pnev_json, prefix) → (dict, summary)
"""

from __future__ import annotations
from datetime import date
from typing import Any
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _g(d, *keys, default=""):
    for k in keys:
        if not isinstance(d, dict): return default
        d = d.get(k, default)
    return d if d != {} else default

def _n(label, val, key, min_v=0.0, max_v=999.0, step=1.0, fmt="%.0f"):
    v = float(val or 0)
    v = max(float(min_v), min(float(max_v), v))
    return st.number_input(label, min_value=float(min_v), max_value=float(max_v),
                           value=v, step=float(step), format=fmt, key=key)

def _s(label, opts, val, key):
    idx = opts.index(val) if val in opts else 0
    return st.selectbox(label, opts, index=idx, key=key)

def _t(label, val, key, height=68):
    return st.text_area(label, value=str(val or ""), height=height, key=key)

def _ds(val, media, ds):
    """Calcola quante DS dal valore atteso."""
    try:
        return (float(val) - float(media)) / float(ds)
    except Exception:
        return None

def _interpreta_ds(ds_val, inverso=False):
    """
    Interpreta il numero di DS.
    inverso=True: tempi più alti = peggio (DEM, KD)
    inverso=False: punteggi più alti = meglio (NSUCO, TVPS)
    """
    if ds_val is None:
        return "—"
    if inverso:
        ds_val = -ds_val  # giriamo: tempi elevati = DS negativi
    if ds_val >= 1.5:   return "✅ Ottimale (>1 DS sopra norma)"
    if ds_val >= 0.5:   return "✅ Nella norma"
    if ds_val >= -0.5:  return "🟡 Limite inferiore"
    if ds_val >= -1.0:  return "🟠 1 DS sotto norma"
    if ds_val >= -2.0:  return "🔴 2 DS sotto norma"
    return "🔴🔴 3+ DS sotto norma"

def _badge(testo):
    if "✅" in testo: return "success"
    if "🟡" in testo: return "warning"
    return "error"


# ─────────────────────────────────────────────────────────────────────────────
# 1. DEM — Developmental Eye Movement Test
# Norme da Scheda Analisi xlsx: media e DS per età (anni)
# ─────────────────────────────────────────────────────────────────────────────

# (età, media_V, ds_V, media_H, ds_H, media_ratio, ds_ratio, media_err, ds_err)
DEM_NORME = {
    6:  (49.1, 8.4,  66.7, 11.0, 1.35, 0.14, 2.21, 1.60),
    7:  (41.8, 7.3,  53.7,  9.2, 1.28, 0.12, 1.78, 1.40),
    8:  (35.1, 5.9,  43.9,  8.1, 1.24, 0.11, 1.44, 1.30),
    9:  (30.4, 5.2,  38.3,  7.4, 1.20, 0.10, 1.24, 1.18),
    10: (28.3, 4.9,  35.5,  6.8, 1.17, 0.10, 1.11, 1.17),
    11: (26.1, 4.5,  32.3,  6.3, 1.14, 0.09, 1.01, 1.10),
    12: (24.0, 4.2,  29.8,  5.9, 1.12, 0.09, 0.95, 1.05),
    13: (22.5, 4.0,  27.5,  5.5, 1.11, 0.09, 0.88, 1.00),
    14: (21.0, 3.8,  25.6,  5.2, 1.10, 0.08, 0.83, 0.95),
    15: (20.0, 3.6,  24.0,  5.0, 1.09, 0.08, 0.80, 0.90),
}

def _dem_norme_for_age(eta):
    """Ritorna le norme per età (usa la più vicina disponibile)."""
    eta = max(6, min(15, int(round(float(eta)))))
    return DEM_NORME.get(eta, DEM_NORME[10])

def _dem_tipologia(tv_ds, th_ds, ratio_ds):
    """Determina la tipologia DEM (I-IV)."""
    v_ok = tv_ds >= -1.0
    h_ok = th_ds >= -1.0
    r_ok = ratio_ds >= -1.0
    if v_ok and h_ok: return "I — Normale"
    if v_ok and not h_ok: return "II — Disfunzione oculomotoria"
    if not v_ok and not h_ok and r_ok: return "III — Disfunzione verbale"
    return "IV — Disfunzione oculomotoria e verbale"

def dem_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔢 DEM — Developmental Eye Movement Test")
    st.caption("Richman & Garzia, 1987. Test A=verticale, Test B=orizzontale pretest, Test C=orizzontale")

    eta = _n("Età paziente (anni)", _g(d,"eta"), f"{px}_eta", 5, 18, 1)

    c = st.columns(5)
    with c[0]: ta_add = _n("Test A add.", _g(d,"ta_add"), f"{px}_ta_add", 0, 30, 1)
    with c[1]: ta_omm = _n("Test A omm.", _g(d,"ta_omm"), f"{px}_ta_omm", 0, 30, 1)
    with c[2]: ta_sost = _n("Test A sost.", _g(d,"ta_sost"), f"{px}_ta_sost", 0, 30, 1)
    with c[3]: ta_trasp = _n("Test A trasp.", _g(d,"ta_trasp"), f"{px}_ta_trasp", 0, 30, 1)
    with c[4]: ta_tempo = _n("Test A (sec)", _g(d,"ta_tempo"), f"{px}_ta_tempo", 0, 300, 0.1, "%.1f")

    c2 = st.columns(5)
    with c2[0]: tb_add = _n("Test B add.", _g(d,"tb_add"), f"{px}_tb_add", 0, 30, 1)
    with c2[1]: tb_omm = _n("Test B omm.", _g(d,"tb_omm"), f"{px}_tb_omm", 0, 30, 1)
    with c2[2]: tb_sost = _n("Test B sost.", _g(d,"tb_sost"), f"{px}_tb_sost", 0, 30, 1)
    with c2[3]: tb_trasp = _n("Test B trasp.", _g(d,"tb_trasp"), f"{px}_tb_trasp", 0, 30, 1)
    with c2[4]: tb_tempo = _n("Test B (sec)", _g(d,"tb_tempo"), f"{px}_tb_tempo", 0, 300, 0.1, "%.1f")

    c3 = st.columns(5)
    with c3[0]: tc_add = _n("Test C add.", _g(d,"tc_add"), f"{px}_tc_add", 0, 30, 1)
    with c3[1]: tc_omm = _n("Test C omm.", _g(d,"tc_omm"), f"{px}_tc_omm", 0, 30, 1)
    with c3[2]: tc_sost = _n("Test C sost.", _g(d,"tc_sost"), f"{px}_tc_sost", 0, 30, 1)
    with c3[3]: tc_trasp = _n("Test C trasp.", _g(d,"tc_trasp"), f"{px}_tc_trasp", 0, 30, 1)
    with c3[4]: tc_tempo = _n("Test C (sec)", _g(d,"tc_tempo"), f"{px}_tc_tempo", 0, 300, 0.1, "%.1f")

    # Calcoli
    tot_err = int(ta_add+ta_omm+ta_sost+ta_trasp+tb_add+tb_omm+tb_sost+tb_trasp+tc_add+tc_omm+tc_sost+tc_trasp)
    tot_err_corr = int(tb_omm+tb_add+tc_omm+tc_add)

    # Tempo orizzontale aggiustato per errori
    try:
        th_adj = tc_tempo * 80 / (80 - tot_err_corr) if (80 - tot_err_corr) > 0 else tc_tempo
        tv_adj = ta_tempo
        ratio = th_adj / tv_adj if tv_adj > 0 else 0
    except Exception:
        th_adj = tv_adj = ratio = 0

    st.markdown("---")
    st.markdown("**📊 Scoring automatico DEM**")
    norme = _dem_norme_for_age(eta)
    mv, dsv, mh, dsh, mr, dsr, me, dse = norme

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("TV adj (sec)", f"{tv_adj:.1f}", f"norma: {mv:.0f}±{dsv:.1f}")
    col2.metric("TH adj (sec)", f"{th_adj:.1f}", f"norma: {mh:.0f}±{dsh:.1f}")
    col3.metric("Ratio H/V", f"{ratio:.2f}", f"norma: {mr:.2f}±{dsr:.2f}")
    col4.metric("Errori tot.", f"{tot_err}", f"norma: {me:.1f}±{dse:.1f}")

    ds_v = _ds(tv_adj, mv, dsv)
    ds_h = _ds(th_adj, mh, dsh)
    ds_r = _ds(ratio, mr, dsr)
    ds_e = _ds(tot_err, me, dse)

    tipologia = _dem_tipologia(-(ds_v or 0), -(ds_h or 0), -(ds_r or 0))

    r_v = _interpreta_ds(ds_v, inverso=True)
    r_h = _interpreta_ds(ds_h, inverso=True)
    r_r = _interpreta_ds(ds_r, inverso=True)

    st.markdown(f"**Tipologia: `{tipologia}`**")
    st.markdown(f"- Verticale: {r_v}  \n- Orizzontale: {r_h}  \n- Ratio: {r_r}")

    note = _t("Note DEM", _g(d,"note"), f"{px}_note")

    result = {
        "eta": eta,
        "ta": {"add":ta_add,"omm":ta_omm,"sost":ta_sost,"trasp":ta_trasp,"tempo":ta_tempo},
        "tb": {"add":tb_add,"omm":tb_omm,"sost":tb_sost,"trasp":tb_trasp,"tempo":tb_tempo},
        "tc": {"add":tc_add,"omm":tc_omm,"sost":tc_sost,"trasp":tc_trasp,"tempo":tc_tempo},
        "calcoli": {"tv_adj":round(tv_adj,1),"th_adj":round(th_adj,1),
                    "ratio":round(ratio,3),"tot_err":tot_err,
                    "ds_v":round(ds_v,2) if ds_v else None,
                    "ds_h":round(ds_h,2) if ds_h else None,
                    "tipologia":tipologia},
        "note": note,
    }
    summary = f"DEM: TV={tv_adj:.1f}s TH={th_adj:.1f}s Ratio={ratio:.2f} → {tipologia}"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 2. K-D TEST — King-Devick Saccade Test
# Norme per età (anni): media_tempo, ds_tempo, media_err, ds_err per ciascuna card
# ─────────────────────────────────────────────────────────────────────────────

KD_NORME = {
    # (età): [(media_t1, ds_t1, media_e1, ds_e1), (t2...), (t3...), (tot_t, ds_tot)]
    6:  [(23.5,4.5,0.30,0.40),(25.0,5.0,0.40,0.50),(28.0,5.5,0.55,0.65),(76.5,15.0)],
    7:  [(20.0,3.8,0.22,0.35),(21.5,4.2,0.30,0.40),(24.0,4.8,0.40,0.55),(65.5,12.8)],
    8:  [(17.5,3.2,0.18,0.30),(18.5,3.6,0.22,0.35),(21.0,4.2,0.32,0.48),(57.0,11.0)],
    9:  [(15.5,2.8,0.15,0.25),(16.5,3.2,0.18,0.30),(18.5,3.8,0.28,0.42),(50.5, 9.8)],
    10: [(14.0,2.5,0.12,0.22),(15.0,2.9,0.15,0.26),(17.0,3.5,0.24,0.38),(46.0, 8.9)],
    11: [(13.0,2.3,0.10,0.19),(13.8,2.6,0.13,0.23),(15.5,3.2,0.21,0.35),(42.3, 8.1)],
    12: [(12.0,2.2,0.09,0.17),(12.8,2.4,0.11,0.20),(14.5,3.0,0.18,0.32),(39.3, 7.6)],
    13: [(11.5,2.1,0.08,0.16),(12.2,2.3,0.10,0.18),(13.5,2.8,0.15,0.29),(37.2, 7.2)],
    14: [(11.0,2.0,0.07,0.15),(11.5,2.2,0.09,0.17),(13.0,2.7,0.13,0.27),(35.5, 6.9)],
    15: [(10.5,1.9,0.06,0.14),(11.0,2.1,0.08,0.16),(12.5,2.6,0.12,0.26),(34.0, 6.6)],
}

def kd_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### ⚡ K-D Test — King-Devick Saccade Test")
    st.caption("NYSOA. 3 card + demo. Scoring: tempo (sec) + errori per card.")

    eta = _n("Età paziente (anni)", _g(d,"eta"), f"{px}_eta", 5, 18, 1)

    c = st.columns(4)
    with c[0]:
        st.markdown("**Demo**")
        demo_t = _n("Tempo (s)", _g(d,"demo","tempo"), f"{px}_demo_t", 0, 120, 0.1, "%.1f")
        demo_e = _n("Errori", _g(d,"demo","errori"), f"{px}_demo_e", 0, 20, 1)
    with c[1]:
        st.markdown("**Card 1**")
        t1 = _n("Tempo (s)", _g(d,"card1","tempo"), f"{px}_t1", 0, 120, 0.1, "%.1f")
        e1 = _n("Errori", _g(d,"card1","errori"), f"{px}_e1", 0, 20, 1)
    with c[2]:
        st.markdown("**Card 2**")
        t2 = _n("Tempo (s)", _g(d,"card2","tempo"), f"{px}_t2", 0, 120, 0.1, "%.1f")
        e2 = _n("Errori", _g(d,"card2","errori"), f"{px}_e2", 0, 20, 1)
    with c[3]:
        st.markdown("**Card 3**")
        t3 = _n("Tempo (s)", _g(d,"card3","tempo"), f"{px}_t3", 0, 120, 0.1, "%.1f")
        e3 = _n("Errori", _g(d,"card3","errori"), f"{px}_e3", 0, 20, 1)

    tot_t = t1 + t2 + t3
    tot_e = int(e1 + e2 + e3)

    st.markdown("---")
    st.markdown("**📊 Scoring automatico K-D**")

    eta_key = max(6, min(15, int(round(float(eta)))))
    norme = KD_NORME.get(eta_key, KD_NORME[10])
    n1, n2, n3, n_tot = norme

    risultati = []
    for i, (t, e, n, label) in enumerate([(t1,e1,n1,"Card 1"),(t2,e2,n2,"Card 2"),(t3,e3,n3,"Card 3")], 1):
        ds_t = _ds(t, n[0], n[1])
        ds_e = _ds(e, n[2], n[3])
        r_t = _interpreta_ds(ds_t, inverso=True)
        r_e = _interpreta_ds(ds_e, inverso=True)
        risultati.append({"card": label, "tempo": t, "errori": int(e),
                          "norma_t": f"{n[0]:.1f}±{n[1]:.1f}", "norma_e": f"{n[2]:.2f}±{n[3]:.2f}",
                          "ris_t": r_t, "ris_e": r_e})

    col1, col2, col3 = st.columns(3)
    for i, r in enumerate(risultati):
        col = [col1, col2, col3][i]
        col.metric(r["card"], f"{r['tempo']:.1f}s / {r['errori']} err",
                   f"norma: {r['norma_t']}s")
        col.caption(f"Tempo: {r['ris_t']}")
        col.caption(f"Errori: {r['ris_e']}")

    ds_tot = _ds(tot_t, n_tot[0], n_tot[1])
    r_tot = _interpreta_ds(ds_tot, inverso=True)
    st.metric("**Totale (card 1+2+3)**", f"{tot_t:.1f}s / {tot_e} err",
              f"norma: {n_tot[0]:.0f}±{n_tot[1]:.0f}s")
    getattr(st, _badge(r_tot))(f"Risultato totale: {r_tot}")

    note = _t("Note K-D", _g(d,"note"), f"{px}_note")

    result = {
        "eta": eta,
        "demo": {"tempo": demo_t, "errori": int(demo_e)},
        "card1": {"tempo": t1, "errori": int(e1)},
        "card2": {"tempo": t2, "errori": int(e2)},
        "card3": {"tempo": t3, "errori": int(e3)},
        "calcoli": {"tot_tempo": round(tot_t,1), "tot_errori": tot_e,
                    "ds_tot": round(ds_tot,2) if ds_tot else None,
                    "risultato": r_tot},
        "note": note,
    }
    summary = f"K-D: tot {tot_t:.1f}s / {tot_e} err → {r_tot}"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 3. NSUCO Oculomotor Test
# Scala 1-5 per 4 parametri × 2 prove (saccadi + pursuit)
# Norme: età 6-14 anni, sesso M/F
# ─────────────────────────────────────────────────────────────────────────────

NSUCO_NORME = {
    # (età_min, età_max): {"sacc": (ab, acc, testa, corpo), "purs": (ab, acc, testa, corpo)}
    # Medie normative (tutti i valori sono "ottimale = 5 per abilità, 5 per acc, 4 per testa/corpo")
    (5,6):   {"sacc":(3.0,3.5,3.5,4.0),"purs":(3.0,3.0,3.5,4.0)},
    (7,8):   {"sacc":(4.0,4.0,4.0,4.5),"purs":(4.0,3.5,4.0,4.5)},
    (9,10):  {"sacc":(4.5,4.5,4.5,5.0),"purs":(4.5,4.0,4.5,5.0)},
    (11,12): {"sacc":(5.0,5.0,5.0,5.0),"purs":(5.0,4.5,5.0,5.0)},
    (13,99): {"sacc":(5.0,5.0,5.0,5.0),"purs":(5.0,5.0,5.0,5.0)},
}

NSUCO_SCALE = {
    "abilità_sacc": [
        "1 — Completa <2 escursioni",
        "2 — Completa 2 escursioni",
        "3 — Completa 3 escursioni",
        "4 — Completa 4 escursioni",
        "5 — Completa 5 escursioni",
    ],
    "accuratezza_sacc": [
        "1 — 4+ saccadi iper/ipometriche",
        "2 — 3 saccadi moderate",
        "3 — 1-2 saccadi moderate",
        "4 — Leggere saccadi",
        "5 — Nessuna saccade",
    ],
    "testa": [
        "1 — Ampi movimenti ogni volta",
        "2 — Moderati movimenti ogni volta",
        "3 — Lievi movimenti >50% volte",
        "4 — Lievi movimenti <50% volte",
        "5 — Nessun movimento",
    ],
    "corpo": [
        "1 — Ampi movimenti ogni volta",
        "2 — Moderati movimenti ogni volta",
        "3 — Lievi movimenti >50% volte",
        "4 — Lievi movimenti <50% volte",
        "5 — Nessun movimento",
    ],
    "abilità_purs": [
        "1 — <mezza rotazione",
        "2 — Mezza rotazione entrambi i sensi",
        "3 — Una rotazione entrambi i sensi",
        "4 — Due rotazioni in un senso, <2 nell'altro",
        "5 — Due rotazioni in ciascun senso",
    ],
    "accuratezza_purs": [
        "1 — >10 rifissazioni",
        "2 — 5-10 rifissazioni",
        "3 — 3-4 rifissazioni",
        "4 — 1-2 rifissazioni",
        "5 — Nessuna rifissazione",
    ],
}

def _nsuco_norma(eta):
    for (emin, emax), vals in NSUCO_NORME.items():
        if emin <= eta <= emax:
            return vals
    return NSUCO_NORME[(11,12)]

def nsuco_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 👁️ NSUCO Oculomotor Test")
    st.caption("Maples 1995. Saccadi e Pursuit — scala 1-5 per 4 parametri ciascuno.")

    c = st.columns(2)
    with c[0]: eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta", 4, 18, 1)
    with c[1]: sesso = _s("Sesso", ["M", "F", "—"], _g(d,"sesso","—"), f"{px}_sesso")

    def _score_row(label, opts, val, key):
        idx = int(val or 1) - 1
        idx = max(0, min(4, idx))
        scelta = st.selectbox(label, opts, index=idx, key=key)
        return opts.index(scelta) + 1

    tab_s, tab_p = st.tabs(["🔴 Saccadi", "🔵 Pursuit"])

    with tab_s:
        sacc_ab  = _score_row("Abilità", NSUCO_SCALE["abilità_sacc"], _g(d,"saccadi","abilita"), f"{px}_sacc_ab")
        sacc_acc = _score_row("Accuratezza", NSUCO_SCALE["accuratezza_sacc"], _g(d,"saccadi","accuratezza"), f"{px}_sacc_acc")
        sacc_t   = _score_row("Movimento testa", NSUCO_SCALE["testa"], _g(d,"saccadi","testa"), f"{px}_sacc_t")
        sacc_c   = _score_row("Movimento corpo", NSUCO_SCALE["corpo"], _g(d,"saccadi","corpo"), f"{px}_sacc_c")

    with tab_p:
        purs_ab  = _score_row("Abilità", NSUCO_SCALE["abilità_purs"], _g(d,"pursuit","abilita"), f"{px}_purs_ab")
        purs_acc = _score_row("Accuratezza", NSUCO_SCALE["accuratezza_purs"], _g(d,"pursuit","accuratezza"), f"{px}_purs_acc")
        purs_t   = _score_row("Movimento testa", NSUCO_SCALE["testa"], _g(d,"pursuit","testa"), f"{px}_purs_t")
        purs_c   = _score_row("Movimento corpo", NSUCO_SCALE["corpo"], _g(d,"pursuit","corpo"), f"{px}_purs_c")

    norma = _nsuco_norma(int(eta))
    n_s = norma["sacc"]
    n_p = norma["purs"]

    st.markdown("---")
    st.markdown("**📊 Confronto con norma età**")

    def _nsuco_ris(val, norma_val):
        diff = val - norma_val
        if diff >= 0: return "✅ Nella norma"
        if diff >= -1: return "🟡 Limite"
        if diff >= -2: return "🔴 Sotto norma"
        return "🔴🔴 Molto sotto norma"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Saccadi**")
        st.write(f"Abilità: {sacc_ab}/5 (norma≥{n_s[0]:.0f}) → {_nsuco_ris(sacc_ab,n_s[0])}")
        st.write(f"Accuratezza: {sacc_acc}/5 (norma≥{n_s[1]:.0f}) → {_nsuco_ris(sacc_acc,n_s[1])}")
        st.write(f"Testa: {sacc_t}/5 (norma≥{n_s[2]:.0f}) → {_nsuco_ris(sacc_t,n_s[2])}")
        st.write(f"Corpo: {sacc_c}/5 (norma≥{n_s[3]:.0f}) → {_nsuco_ris(sacc_c,n_s[3])}")
    with col2:
        st.markdown("**Pursuit**")
        st.write(f"Abilità: {purs_ab}/5 (norma≥{n_p[0]:.0f}) → {_nsuco_ris(purs_ab,n_p[0])}")
        st.write(f"Accuratezza: {purs_acc}/5 (norma≥{n_p[1]:.0f}) → {_nsuco_ris(purs_acc,n_p[1])}")
        st.write(f"Testa: {purs_t}/5 (norma≥{n_p[2]:.0f}) → {_nsuco_ris(purs_t,n_p[2])}")
        st.write(f"Corpo: {purs_c}/5 (norma≥{n_p[3]:.0f}) → {_nsuco_ris(purs_c,n_p[3])}")

    note = _t("Note NSUCO", _g(d,"note"), f"{px}_note")

    result = {
        "eta": eta, "sesso": sesso,
        "saccadi": {"abilita":sacc_ab,"accuratezza":sacc_acc,"testa":sacc_t,"corpo":sacc_c},
        "pursuit": {"abilita":purs_ab,"accuratezza":purs_acc,"testa":purs_t,"corpo":purs_c},
        "note": note,
    }
    s_ris = _nsuco_ris(min(sacc_ab,sacc_acc), min(n_s[0],n_s[1]))
    p_ris = _nsuco_ris(min(purs_ab,purs_acc), min(n_p[0],n_p[1]))
    summary = f"NSUCO: Sacc {sacc_ab}/{sacc_acc} {s_ris} | Purs {purs_ab}/{purs_acc} {p_ris}"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 4. GROFFMAN Visual Tracing Test
# 5 percorsi (A-E), punteggio max 10 per percorso, tot max 50
# Norma: 28±3 per età 9-14 anni
# ─────────────────────────────────────────────────────────────────────────────

GROFFMAN_NORME = {
    6: (18,4), 7: (20,4), 8: (23,4), 9: (26,4), 10: (28,3),
    11: (28,3), 12: (29,3), 13: (30,3), 14: (30,3), 15: (31,3),
}

def groffman_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔗 Groffman Visual Tracing Test")
    st.caption("5 percorsi (A-E). Punteggio: lettere/numeri corretti × tempo. Max 10 per percorso.")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta", 5, 18, 1)

    percorsi = {}
    tot = 0
    for perc in ["A","B","C","D","E"]:
        c = st.columns(4)
        with c[0]: st.markdown(f"**Percorso {perc}**")
        with c[1]: ln = _n("Lett/Num", _g(d,f"perc_{perc}","lett_num"), f"{px}_{perc}_ln", 0, 10, 1)
        with c[2]: tempo = _n("Tempo (s)", _g(d,f"perc_{perc}","tempo"), f"{px}_{perc}_t", 0, 120, 1)
        with c[3]: sol = _n("Soluzione", _g(d,f"perc_{perc}","soluzione"), f"{px}_{perc}_sol", 0, 10, 1)
        # punteggio = min(sol * ln, 10)  — semplificazione: usiamo il punteggio diretto
        punti = _n(f"Punti {perc}", _g(d,f"perc_{perc}","punti"), f"{px}_{perc}_punti", 0, 10, 1)
        percorsi[perc] = {"lett_num": int(ln), "tempo": int(tempo), "soluzione": int(sol), "punti": int(punti)}
        tot += int(punti)

    st.markdown("---")
    norma = GROFFMAN_NORME.get(max(6,min(15,int(eta))), (28,3))
    ds = _ds(tot, norma[0], norma[1])
    ris = _interpreta_ds(ds)

    c_res = st.columns(2)
    c_res[0].metric("Totale punti", f"{tot}/50", f"norma: {norma[0]}±{norma[1]}")
    c_res[1].markdown(f"**Risultato:** {ris}")

    note = _t("Note Groffman", _g(d,"note"), f"{px}_note")

    result = {"eta": eta, **{f"perc_{p}": v for p,v in percorsi.items()},
              "calcoli": {"totale": tot, "ds": round(ds,2) if ds else None, "risultato": ris},
              "note": note}
    summary = f"Groffman: {tot}/50 punti → {ris}"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 5. ACCOMODAZIONE — PPA, Focus Flexibility, Fusion Flexibility
# ─────────────────────────────────────────────────────────────────────────────

# Focus Flexibility norme (cpm) per età
FOCUS_FLEX_MONO = {
    6: (5.5,2.5), 7: (6.5,2.0), 8: (7.0,2.5), 9: (7.0,2.5), 10: (7.0,2.5),
    11: (7.0,2.5), 12: (7.0,2.5), 13: (11.0,5.0), 14: (11.0,5.0), 15: (11.0,5.0),
}
FOCUS_FLEX_BINO = {
    6: (3.0,2.5), 7: (3.5,2.5), 8: (5.0,2.5), 9: (5.0,2.5), 10: (5.0,2.5),
    11: (5.0,2.5), 12: (5.0,2.5), 13: (8.0,5.0), 14: (8.0,5.0), 15: (8.0,5.0),
}

def accomodazione_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔭 Accomodazione")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_acc", 5, 50, 1)

    # PPA
    st.markdown("**PPA — Punto Prossimo di Accomodazione**")
    try:
        asp_ppa_od = 15 - eta/4
        asp_ppa_bino = 18 - eta/3
    except Exception:
        asp_ppa_od = asp_ppa_bino = 0

    c = st.columns(3)
    with c[0]: ppa_od_cm = _n("OD (cm)", _g(d,"ppa","od_cm"), f"{px}_ppa_od", 0, 50, 0.5, "%.1f")
    with c[1]: ppa_os_cm = _n("OS (cm)", _g(d,"ppa","os_cm"), f"{px}_ppa_os", 0, 50, 0.5, "%.1f")
    with c[2]: ppa_bino_cm = _n("Bino (cm)", _g(d,"ppa","bino_cm"), f"{px}_ppa_bino", 0, 50, 0.5, "%.1f")

    def _cm_to_dt(cm): return round(100/cm, 2) if cm > 0 else 0
    ppa_od_dt = _cm_to_dt(ppa_od_cm)
    ppa_os_dt = _cm_to_dt(ppa_os_cm)
    ppa_bino_dt = _cm_to_dt(ppa_bino_cm)

    st.caption(f"OD: {ppa_od_dt:.2f}dt (asp ≥{asp_ppa_od:.1f}dt±2) | "
               f"OS: {ppa_os_dt:.2f}dt | Bino: {ppa_bino_dt:.2f}dt (asp ≥{asp_ppa_bino:.1f}dt±2)")

    # Focus Flexibility
    st.markdown("**Focus Flexibility (flessibilità accomodativa)**")
    c2 = st.columns(3)
    with c2[0]: ff_od = _n("OD (cpm)", _g(d,"focus_flex","od"), f"{px}_ff_od", 0, 30, 0.5, "%.1f")
    with c2[1]: ff_os = _n("OS (cpm)", _g(d,"focus_flex","os"), f"{px}_ff_os", 0, 30, 0.5, "%.1f")
    with c2[2]: ff_bino = _n("Bino (cpm)", _g(d,"focus_flex","bino"), f"{px}_ff_bino", 0, 30, 0.5, "%.1f")

    eta_key = max(6,min(15,int(eta)))
    nm = FOCUS_FLEX_MONO.get(eta_key,(7.0,2.5))
    nb = FOCUS_FLEX_BINO.get(eta_key,(5.0,2.5))

    def _ff_ris(val, norma):
        ds = _ds(val, norma[0], norma[1])
        return _interpreta_ds(ds)

    st.caption(f"OD: {_ff_ris(ff_od,nm)} | OS: {_ff_ris(ff_os,nm)} | Bino: {_ff_ris(ff_bino,nb)}")
    st.caption(f"Norma mono: {nm[0]}±{nm[1]} cpm | Norma bino: {nb[0]}±{nb[1]} cpm")

    # Fusion Flexibility
    st.markdown("**Fusion Flexibility (flessibilità fusionale)**")
    fus_bino = _n("Bino (cpm)", _g(d,"fusion_flex","bino"), f"{px}_fus_bino", 0, 30, 0.5, "%.1f")
    fus_ris = _interpreta_ds(_ds(fus_bino, 8.1, 4.3))
    st.caption(f"Norma: 8.1±4.3 cpm → {fus_ris}")

    # Acc-Vergence Flexibility
    st.markdown("**Acc-Vergence Flexibility**")
    c3 = st.columns(2)
    with c3[0]: av_80 = _n("20/80 (cicli/30s)", _g(d,"acc_verg_flex","v80"), f"{px}_av80", 0, 40, 1)
    with c3[1]: av_25 = _n("20/25 (cicli/30s)", _g(d,"acc_verg_flex","v25"), f"{px}_av25", 0, 40, 1)
    asp_av = 16 if eta >= 13 else 12
    st.caption(f"Norma: {asp_av} cicli/30s → "
               f"20/80: {'✅' if av_80>=asp_av else '🔴'} | 20/25: {'✅' if av_25>=asp_av else '🔴'}")

    note = _t("Note accomodazione", _g(d,"note"), f"{px}_note_acc")

    result = {
        "eta": eta,
        "ppa": {"od_cm":ppa_od_cm,"os_cm":ppa_os_cm,"bino_cm":ppa_bino_cm,
                "od_dt":ppa_od_dt,"os_dt":ppa_os_dt,"bino_dt":ppa_bino_dt},
        "focus_flex": {"od":ff_od,"os":ff_os,"bino":ff_bino,
                       "ris_od":_ff_ris(ff_od,nm),"ris_bino":_ff_ris(ff_bino,nb)},
        "fusion_flex": {"bino":fus_bino,"risultato":fus_ris},
        "acc_verg_flex": {"v80":av_80,"v25":av_25},
        "note": note,
    }
    summary = (f"Acc: PPA bino {ppa_bino_cm:.1f}cm | FF bino {ff_bino}cpm {_ff_ris(ff_bino,nb)} | "
               f"Fus {fus_bino}cpm {fus_ris}")
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 6. TVPS-3 — Test of Visual Perceptual Skills (3rd Edition)
# 7 subtest, punteggi grezzi → scaled (media 10, DS 3) → standard (media 100, DS 15)
# Tabelle semplificate per età 4-18
# ─────────────────────────────────────────────────────────────────────────────

TVPS_SUBTESTS = [
    ("disc",  "Discriminazione visiva",     16),
    ("mem",   "Memoria visiva",             16),
    ("spaz",  "Relazioni spaziali",         16),
    ("cost",  "Costanza della forma",       16),
    ("seq",   "Memoria sequenziale",        16),
    ("fig",   "Figura-sfondo",              16),
    ("chius", "Chiusura visiva",            16),
]

# Norme semplificate: raw_score → scaled score per età 5-15
# (media raw per età → scaled 10, ±1raw = ±1scaled approssimato)
# Fonte: TVPS-3 manual tables (Appendix B.1)
TVPS_RAW_TO_SCALED = {
    # età: {subtest: [(raw_min, raw_max, scaled)]}
    # Semplificato: per ogni età, raw score "medio" = scaled 10
    # Ogni punto grezzo ≈ 1 punto scaled (varia per subtest/età)
    5:  {"disc":7,"mem":5,"spaz":5,"cost":7,"seq":4,"fig":5,"chius":5},
    6:  {"disc":9,"mem":7,"spaz":7,"cost":9,"seq":6,"fig":7,"chius":7},
    7:  {"disc":11,"mem":9,"spaz":9,"cost":10,"seq":8,"fig":9,"chius":9},
    8:  {"disc":12,"mem":10,"spaz":10,"cost":11,"seq":9,"fig":10,"chius":10},
    9:  {"disc":13,"mem":11,"spaz":11,"cost":12,"seq":10,"fig":11,"chius":11},
    10: {"disc":13,"mem":12,"spaz":12,"cost":12,"seq":11,"fig":12,"chius":12},
    11: {"disc":14,"mem":12,"spaz":13,"cost":13,"seq":12,"fig":13,"chius":13},
    12: {"disc":14,"mem":13,"spaz":13,"cost":13,"seq":12,"fig":13,"chius":13},
    13: {"disc":15,"mem":13,"spaz":14,"cost":14,"seq":13,"fig":14,"chius":14},
    14: {"disc":15,"mem":14,"spaz":14,"cost":14,"seq":13,"fig":14,"chius":14},
    15: {"disc":15,"mem":14,"spaz":15,"cost":15,"seq":14,"fig":15,"chius":15},
}

def _raw_to_scaled_tvps(raw, subtest, eta):
    eta_key = max(5, min(15, int(eta)))
    medie = TVPS_RAW_TO_SCALED.get(eta_key, TVPS_RAW_TO_SCALED[10])
    media_raw = medie.get(subtest, 10)
    # Ogni punto grezzo ≈ 1 scaled (DS=3 per range di ~9 punti raw)
    diff = raw - media_raw
    scaled = 10 + round(diff * 3 / 3)  # approssimazione lineare
    return max(1, min(19, scaled))

def _scaled_to_standard(scaled_sum):
    """Somma scaled → standard score (media 100, DS 15)."""
    # Media attesa 70 (7 subtest × 10), DS ≈ 15
    return max(40, min(160, round(100 + (scaled_sum - 70) * 15 / 21)))

def _scaled_to_percentile(scaled):
    """Scaled score → percentile approssimato."""
    table = {1:1,2:1,3:1,4:2,5:5,6:9,7:16,8:25,9:37,10:50,
             11:63,12:75,13:84,14:91,15:95,16:98,17:99,18:99,19:99}
    return table.get(max(1,min(19,int(scaled))),50)

def _tvps_classifica(std):
    if std >= 130: return "Molto superiore"
    if std >= 120: return "Superiore"
    if std >= 110: return "Sopra la media"
    if std >= 90:  return "Nella media"
    if std >= 80:  return "Sotto la media"
    if std >= 70:  return "Limite"
    return "Molto sotto la media"

def tvps_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 👁️ TVPS-3 — Test of Visual Perceptual Skills")
    st.caption("Martin 2006. 7 subtest, 16 item ciascuno. Scaled score media=10, DS=3.")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_tvps", 4, 18, 1)

    raw = {}
    scaled = {}

    st.markdown("**Inserisci punteggi grezzi (0-16 per subtest):**")
    cols = st.columns(4)
    for i, (code, nome, max_raw) in enumerate(TVPS_SUBTESTS):
        with cols[i % 4]:
            r = int(_n(nome[:20], _g(d,"raw",code), f"{px}_tvps_{code}", 0, max_raw, 1))
            raw[code] = r
            sc = _raw_to_scaled_tvps(r, code, eta)
            scaled[code] = sc
            st.caption(f"Scaled: **{sc}** | %ile: **{_scaled_to_percentile(sc)}°**")

    scaled_sum = sum(scaled.values())
    std = _scaled_to_standard(scaled_sum)
    pct_glob = _scaled_to_percentile(round(scaled_sum/7))
    classifica = _tvps_classifica(std)

    st.markdown("---")
    st.markdown("**📊 Risultati TVPS-3**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Somma scaled", f"{scaled_sum}/133")
    col2.metric("Standard score", f"{std}", f"Percentile ~{pct_glob}°")
    col3.metric("Classificazione", classifica)

    # Profilo per subtest
    with st.expander("📋 Profilo dettagliato per subtest", expanded=False):
        for code, nome, _ in TVPS_SUBTESTS:
            sc = scaled.get(code,10)
            pct = _scaled_to_percentile(sc)
            bar = "█" * sc + "░" * (19-sc)
            st.markdown(f"`{nome[:22]:22s}` raw={raw.get(code,0):2d} scaled={sc:2d} "
                        f"({pct:3d}°%ile) {bar}")

    note = _t("Note TVPS", _g(d,"note"), f"{px}_note_tvps")

    result = {
        "eta": eta,
        "raw": raw,
        "scaled": scaled,
        "calcoli": {"scaled_sum": scaled_sum, "standard": std,
                    "percentile": pct_glob, "classificazione": classifica},
        "note": note,
    }
    summary = f"TVPS-3: SS={std} ({classifica}, {pct_glob}° %ile)"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 7. AVIT — Test Integrazione Visuo-Uditiva (Birch & Belmont)
# 20 item (o 10 per bambini 5.8-9.0 anni)
# ─────────────────────────────────────────────────────────────────────────────

AVIT_NORME = {
    # età: (media_su_10, media_su_20)
    6:  (6.5, None), 7: (7.0, None), 8: (7.5, None), 9: (8.0, 14.0),
    10: (None, 15.0), 11: (None, 16.5), 12: (None, 17.5), 13: (None, 18.0),
}

def avit_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔊 AVIT — Test Integrazione Visuo-Uditiva")
    st.caption("Birch & Belmont. Confronto pattern sonori con pattern visivi.")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_avit", 5, 14, 1)
    versione = _s("Versione somministrata", ["10 item (5.8-9.0 anni)", "20 item (9+ anni)"],
                  _g(d,"versione","10 item (5.8-9.0 anni)"), f"{px}_avit_ver")
    max_items = 10 if "10" in versione else 20
    corretti = int(_n(f"Risposte corrette (/{max_items})", _g(d,"corretti"), f"{px}_avit_corr",
                      0, max_items, 1))

    eta_key = max(6, min(13, int(eta)))
    norma = AVIT_NORME.get(eta_key, (None, None))
    n_val = norma[0] if max_items == 10 else norma[1]

    if n_val:
        ds = _ds(corretti, n_val, 1.5)
        ris = _interpreta_ds(ds)
        st.metric(f"Punteggio", f"{corretti}/{max_items}", f"norma: ≥{n_val:.0f}")
        getattr(st, _badge(ris))(ris)
    else:
        st.metric("Punteggio", f"{corretti}/{max_items}")

    note = _t("Note AVIT", _g(d,"note"), f"{px}_note_avit")
    result = {"eta": eta, "versione": versione, "corretti": corretti, "note": note}
    summary = f"AVIT: {corretti}/{max_items}"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 8. VADS — Visuo-Auditory Digit Span
# 4 subtest: UO, VO, US, VS (span di cifre)
# ─────────────────────────────────────────────────────────────────────────────

VADS_NORME = {
    # età: (media_UO, media_VO, media_US, media_VS, media_tot)
    6:  (3.0,2.5,2.5,2.0, 10.0),
    7:  (3.5,3.0,3.0,2.5, 12.0),
    8:  (4.0,3.5,3.5,3.0, 14.0),
    9:  (4.5,4.0,4.0,3.5, 16.0),
    10: (5.0,4.5,4.5,4.0, 18.0),
    11: (5.5,5.0,5.0,4.5, 20.0),
    12: (6.0,5.5,5.5,5.0, 22.0),
}

def vads_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔢 VADS — Visuo-Auditory Digit Span")
    st.caption("Koppitz. 4 subtest: Uditivo-Orale, Visivo-Orale, Uditivo-Scritto, Visivo-Scritto.")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_vads", 5, 13, 1)

    c = st.columns(4)
    with c[0]: uo = int(_n("Uditivo-Orale", _g(d,"uo"), f"{px}_vads_uo", 0, 9, 1))
    with c[1]: vo = int(_n("Visivo-Orale", _g(d,"vo"), f"{px}_vads_vo", 0, 9, 1))
    with c[2]: us = int(_n("Uditivo-Scritto", _g(d,"us"), f"{px}_vads_us", 0, 9, 1))
    with c[3]: vs = int(_n("Visivo-Scritto", _g(d,"vs"), f"{px}_vads_vs", 0, 9, 1))

    tot = uo + vo + us + vs
    eta_key = max(6, min(12, int(eta)))
    norme = VADS_NORME.get(eta_key, VADS_NORME[9])

    st.markdown("---")
    cols = st.columns(5)
    subtests = [("UO",uo,norme[0]),("VO",vo,norme[1]),("US",us,norme[2]),("VS",vs,norme[3]),("Tot",tot,norme[4])]
    for i, (label,val,nm) in enumerate(subtests):
        ds = _ds(val, nm, 1.0)
        ris = _interpreta_ds(ds)
        cols[i].metric(label, str(val), f"norma≥{nm:.0f}")
        cols[i].caption(ris[:15])

    note = _t("Note VADS", _g(d,"note"), f"{px}_note_vads")
    result = {"eta": eta, "uo":uo,"vo":vo,"us":us,"vs":vs,
              "calcoli":{"tot":tot}, "note": note}
    summary = f"VADS: Tot {tot} (UO={uo} VO={vo} US={us} VS={vs})"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 9. VMI — Beery Visual Motor Integration
# Punteggio grezzo → standard (media 100, DS 15) → percentile
# ─────────────────────────────────────────────────────────────────────────────

# Tabelle semplificate VMI: raw_grezzo → std per fascia d'età
# Fonte: Tabelle A del manuale VMI
VMI_RAW_TO_STD = {
    # (età_min, età_max): [(raw, std)]  — interpolazione lineare tra punti
    (3,3):   [(0,55),(3,70),(6,85),(9,100),(12,115),(15,130)],
    (4,4):   [(2,55),(5,70),(8,85),(11,100),(14,115),(17,130)],
    (5,5):   [(4,55),(7,70),(10,85),(13,100),(16,115),(19,130)],
    (6,6):   [(6,55),(9,70),(12,85),(15,100),(18,115),(21,130)],
    (7,7):   [(8,55),(11,70),(14,85),(17,100),(20,115),(23,130)],
    (8,8):   [(10,55),(13,70),(16,85),(19,100),(22,115),(25,130)],
    (9,9):   [(12,55),(15,70),(17,85),(20,100),(23,115),(26,130)],
    (10,10): [(13,55),(16,70),(18,85),(21,100),(24,115),(27,130)],
    (11,11): [(14,55),(17,70),(19,85),(22,100),(25,115),(27,130)],
    (12,12): [(15,55),(17,70),(20,85),(22,100),(25,115),(27,130)],
    (13,15): [(15,55),(18,70),(20,85),(23,100),(25,115),(27,130)],
}

def _vmi_raw_to_std(raw, eta):
    eta_int = int(eta)
    for (emin, emax), table in VMI_RAW_TO_STD.items():
        if emin <= eta_int <= emax:
            # Interpolazione lineare
            for j in range(len(table)-1):
                r0, s0 = table[j]
                r1, s1 = table[j+1]
                if r0 <= raw <= r1:
                    ratio = (raw - r0) / max(r1 - r0, 1)
                    return round(s0 + ratio * (s1 - s0))
            if raw <= table[0][0]: return table[0][1]
            if raw >= table[-1][0]: return table[-1][1]
    return 100

def _std_to_percentile(std):
    # Tabella standard → percentile
    if std >= 130: return 98
    if std >= 120: return 91
    if std >= 110: return 75
    if std >= 100: return 50
    if std >= 90:  return 25
    if std >= 80:  return 9
    if std >= 70:  return 2
    return 1

def vmi_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### ✏️ VMI — Beery Visual Motor Integration")
    st.caption("Beery & Buktenica. Copia figure geometriche. Punteggio grezzo → standard → percentile.")

    eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_vmi", 3, 18, 1)
    raw = int(_n("Punteggio grezzo (figure corrette)", _g(d,"raw"), f"{px}_vmi_raw", 0, 27, 1))

    std = _vmi_raw_to_std(raw, eta)
    pct = _std_to_percentile(std)
    classifica = _tvps_classifica(std)

    st.metric("Standard score VMI", std, f"Percentile ~{pct}°")
    if std >= 85:
        st.success(f"✅ {classifica}")
    elif std >= 70:
        st.warning(f"🟡 {classifica}")
    else:
        st.error(f"🔴 {classifica}")

    note = _t("Note VMI", _g(d,"note"), f"{px}_note_vmi")
    result = {"eta": eta, "raw": raw, "calcoli":{"std":std,"percentile":pct,"classifica":classifica}, "note":note}
    summary = f"VMI: raw={raw} → std={std} ({classifica}, {pct}° %ile)"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# 10. GARDNER Reversal Frequency Test
# 3 subtest: Esecuzione, Riconoscimento, Accoppiamento
# ─────────────────────────────────────────────────────────────────────────────

GARDNER_NORME_ESEC = {
    5:(3.5,2.0),6:(2.5,1.8),7:(1.8,1.5),8:(1.2,1.2),9:(0.8,1.0),10:(0.5,0.8),
}
GARDNER_NORME_RIC_M = {
    5:(8,4),6:(6,3),7:(4,3),8:(3,2),9:(2,2),10:(1,1),
}
GARDNER_NORME_RIC_F = {
    5:(7,4),6:(5,3),7:(3,3),8:(2,2),9:(1,2),10:(1,1),
}

def gardner_ui(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("#### 🔄 Gardner Reversal Frequency Test")
    st.caption("Gardner 1979. Inversioni di lettere/numeri. 3 subtest.")

    c = st.columns(2)
    with c[0]: eta = _n("Età (anni)", _g(d,"eta"), f"{px}_eta_gard", 5, 10, 1)
    with c[1]: sesso = _s("Sesso", ["M","F","—"], _g(d,"sesso","—"), f"{px}_gard_sesso")

    st.markdown("**Sub-test 1: Esecuzione (scrittura)**")
    c1 = st.columns(3)
    with c1[0]: es_inv = int(_n("Inversioni", _g(d,"esecuzione","inversioni"), f"{px}_es_inv", 0, 25, 1))
    with c1[1]: es_ign = int(_n("Non conoscenza", _g(d,"esecuzione","ignorati"), f"{px}_es_ign", 0, 25, 1))
    es_tot = es_inv + es_ign
    with c1[2]: st.metric("Totale errori esecuzione", es_tot)
    if es_tot > 16:
        st.warning("⚠️ Totale >16: non punteggiabile")

    st.markdown("**Sub-test 2: Riconoscimento**")
    ric_err = int(_n("Errori totali riconoscimento (0-42)", _g(d,"riconoscimento","errori"), f"{px}_ric_err", 0, 42, 1))

    st.markdown("**Sub-test 3: Accoppiamento** (solo 5-8 anni)")
    acc_err = int(_n("Errori accoppiamento", _g(d,"accoppiamento","errori"), f"{px}_acc_err", 0, 30, 1))

    # Scoring
    st.markdown("---")
    eta_key = max(5, min(10, int(eta)))
    n_es = GARDNER_NORME_ESEC.get(eta_key, (1.5, 1.2))
    n_ric = (GARDNER_NORME_RIC_M if sesso=="M" else GARDNER_NORME_RIC_F).get(eta_key, (3,2))

    ds_es = _ds(es_tot, n_es[0], n_es[1])
    ds_ric = _ds(ric_err, n_ric[0], n_ric[1])

    col1, col2 = st.columns(2)
    col1.metric("Esecuzione: errori", es_tot, f"norma: {n_es[0]:.1f}±{n_es[1]:.1f}")
    col1.caption(_interpreta_ds(ds_es, inverso=True))
    col2.metric("Riconoscimento: errori", ric_err, f"norma: {n_ric[0]:.0f}±{n_ric[1]:.0f}")
    col2.caption(_interpreta_ds(ds_ric, inverso=True))

    note = _t("Note Gardner", _g(d,"note"), f"{px}_note_gard")
    result = {
        "eta": eta, "sesso": sesso,
        "esecuzione": {"inversioni":es_inv,"ignorati":es_ign,"tot":es_tot},
        "riconoscimento": {"errori":ric_err},
        "accoppiamento": {"errori":acc_err},
        "note": note,
    }
    summary = f"Gardner: Esec {es_tot} err / Ric {ric_err} err"
    return result, summary


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def render_test_visivi(
    test_json: dict | None,
    prefix: str,
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Entry point. Mostra tutti i test in tabs.
    test_json: dict salvato in visita_json["test_visivi"] o {}
    """
    if test_json is None:
        test_json = {}

    if readonly:
        st.caption("Test visivi — modalità sola lettura")
        return test_json, "Test visivi (readonly)"

    st.markdown("## 🧪 Test Visivi Funzionali con Scoring")

    tabs = st.tabs([
        "🔢 DEM", "⚡ K-D", "👁️ NSUCO", "🔗 Groffman",
        "🔭 Accomodazione", "👁️ TVPS-3",
        "🔊 AVIT", "🔢 VADS", "✏️ VMI", "🔄 Gardner",
    ])

    nuovi = dict(test_json)
    summaries = []

    fn_map = [
        ("dem",          dem_ui),
        ("kd",           kd_ui),
        ("nsuco",        nsuco_ui),
        ("groffman",     groffman_ui),
        ("accomodazione", accomodazione_ui),
        ("tvps",         tvps_ui),
        ("avit",         avit_ui),
        ("vads",         vads_ui),
        ("vmi",          vmi_ui),
        ("gardner",      gardner_ui),
    ]

    for i, (key, fn) in enumerate(fn_map):
        with tabs[i]:
            data, s = fn(test_json.get(key, {}), f"{prefix}_{key}")
            nuovi[key] = data
            summaries.append(s)

    nuovi["_meta"] = {"data": date.today().isoformat(), "versione": "tv_v1"}
    summary_globale = " | ".join(summaries)
    return nuovi, summary_globale
