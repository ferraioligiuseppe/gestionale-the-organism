# -*- coding: utf-8 -*-
"""
ui_valutazione_visiva_funzionale.py
Batteria completa secondo struttura OEP / The Organism

STRUTTURA (10 sezioni):
  S1 — Test Preliminari
  S2 — Test Spaziali OEP
  S3 — Test Oculomotori (DEM, K-D, NSUCO, Groffman, Visual Tracking)
  S4 — Test Accomodativi (PPA, Focus Flex, Fusion Flex, Acc-Verg Flex)
  S5 — Test Visuo-Percettivi (TVPS-3)
  S6 — Relazioni Visuo-Spaziali (Piaget, Gardner)
  S7 — Screening Grosso Motorio (SUNY, WACHS)
  S8 — Integrazione Visuo-Motoria (VMI, WOLD)
  S9 — Integrazione Visuo-Uditiva e Memoria (AVIT, VADS, Monroe, Getman)
  S10 — Sindrome Vertiginosa Visiva (SVV)
  DIAGNOSI — Report automatico con pattern diagnostici

NOTA: i test oculomotori interattivi (DEM con click, K-D con timer, Visual
Tracking, Piaget) sono disponibili come widget React in widget_test_interattivi.jsx.
Questa versione usa form Streamlit con inserimento manuale dei risultati.
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
    v = max(float(min_v), min(float(max_v), float(val or 0)))
    return st.number_input(label, min_value=float(min_v), max_value=float(max_v),
                           value=v, step=float(step), format=fmt, key=key)

def _s(label, opts, val, key):
    idx = opts.index(val) if val in opts else 0
    return st.selectbox(label, opts, index=idx, key=key)

def _t(label, val, key, height=68):
    return st.text_area(label, value=str(val or ""), height=height, key=key)

def _cb(label, val, key):
    return st.checkbox(label, value=bool(val), key=key)

def _ds(val, media, ds):
    try: return (float(val) - float(media)) / float(ds)
    except: return None

def _ris(ds_val, inverso=False):
    if ds_val is None: return ("—", "")
    d = -ds_val if inverso else ds_val
    if d >= 1.0:   return ("✅ Ottimale", "success")
    if d >= 0.0:   return ("✅ Nella norma", "success")
    if d >= -1.0:  return ("🟡 1 DS sotto norma", "warning")
    if d >= -2.0:  return ("🔴 2 DS sotto norma", "error")
    return ("🔴 3+ DS sotto norma", "error")

def _show_ris(label, val, media, ds, inverso=False, unit=""):
    ds_val = _ds(val, media, ds)
    txt, tipo = _ris(ds_val, inverso)
    getattr(st, tipo)(f"**{label}:** {val}{unit} (norma: {media}±{ds}{unit}) → {txt}")
    return ds_val

# ─────────────────────────────────────────────────────────────────────────────
# S1 — TEST PRELIMINARI
# ─────────────────────────────────────────────────────────────────────────────

def s1_preliminari(d: dict, px: str) -> dict:
    st.markdown("### 🔍 S1 — Test Preliminari")

    c = st.columns(3)
    with c[0]: dom_occhio = _s("Dominanza occhio", ["—","OD","OS"], _g(d,"dom_occhio"), f"{px}_dom_o")
    with c[1]: dom_mano = _s("Dominanza mano", ["—","DX","SX"], _g(d,"dom_mano"), f"{px}_dom_m")
    with c[2]: dom_piede = _s("Dominanza piede", ["—","DX","SX"], _g(d,"dom_piede"), f"{px}_dom_p")

    st.markdown("**Movimenti oculari (osservazione clinica)**")
    c2 = st.columns(2)
    with c2[0]:
        pursuit_orizz = _s("Pursuit orizzontali", ["—","Fluidi","Lievi saccadi","Moderate saccadi","Saccadici"], _g(d,"pursuit_orizz"), f"{px}_pur_o")
        pursuit_vert  = _s("Pursuit verticali", ["—","Fluidi","Lievi saccadi","Moderate saccadi","Saccadici"], _g(d,"pursuit_vert"), f"{px}_pur_v")
        pursuit_diag  = _s("Pursuit diagonali", ["—","Fluidi","Lievi saccadi","Moderate saccadi","Saccadici"], _g(d,"pursuit_diag"), f"{px}_pur_d")
        pursuit_cerchi = _s("Pursuit cerchi", ["—","Fluidi","Lievi saccadi","Moderate saccadi","Saccadici"], _g(d,"pursuit_cerchi"), f"{px}_pur_c")
    with c2[1]:
        pursuit_testa = _cb("Compensazione con la testa", _g(d,"pursuit_testa"), f"{px}_pur_t")
        sintomi_pursuit = _t("Sintomi durante pursuit", _g(d,"sintomi_pursuit"), f"{px}_sint_pur")

    st.markdown("**PPC — Punto Prossimo di Convergenza**")
    c3 = st.columns(3)
    with c3[0]: ppc_rot = _n("Rottura (cm)", _g(d,"ppc_rot"), f"{px}_ppc_r", 0, 50, 0.5, "%.1f")
    with c3[1]: ppc_rec = _n("Recupero (cm)", _g(d,"ppc_rec"), f"{px}_ppc_rec", 0, 50, 0.5, "%.1f")
    with c3[2]: ppc_occhio = _s("Occhio che devia", ["—","OD","OS","Alt"], _g(d,"ppc_occhio"), f"{px}_ppc_o")
    ppc_note = _t("Note PPC", _g(d,"ppc_note"), f"{px}_ppc_note")

    # Norma PPC: rottura 5±2.5, recupero 7±3
    if ppc_rot > 0:
        ds_r = _ds(ppc_rot, 5.0, 2.5)
        txt, tipo = _ris(ds_r, inverso=True)
        getattr(st, tipo)(f"PPC rottura: {ppc_rot}cm (norma 5±2.5cm) → {txt}")

    st.markdown("**Acuità Visiva**")
    c4 = st.columns(4)
    with c4[0]: av_lon_od = st.text_input("AV lontano OD", _g(d,"av_lon_od"), key=f"{px}_av_lon_od")
    with c4[1]: av_lon_os = st.text_input("AV lontano OS", _g(d,"av_lon_os"), key=f"{px}_av_lon_os")
    with c4[2]: av_lon_oo = st.text_input("AV lontano OO", _g(d,"av_lon_oo"), key=f"{px}_av_lon_oo")
    with c4[3]: av_cc_oo  = st.text_input("AV c.c. OO", _g(d,"av_cc_oo"), key=f"{px}_av_cc_oo")

    st.markdown("**Stereopsi (Randot)**")
    c5 = st.columns(3)
    with c5[0]: stereo_simb = st.text_input("Simboli (250-500\")", _g(d,"stereo_simb"), key=f"{px}_ster_s")
    with c5[1]: stereo_anim = st.text_input("Animali (100-400\")", _g(d,"stereo_anim"), key=f"{px}_ster_a")
    with c5[2]: stereo_anel = st.text_input("Anelli (20-400\")", _g(d,"stereo_anel"), key=f"{px}_ster_r")

    st.markdown("**Cover Test**")
    c6 = st.columns(2)
    with c6[0]:
        ct_lon = _s("Cover test lontano", ["—","Ortoforia","Esoforia lieve","Esoforia mod","Esoforia grave",
                    "Exoforia lieve","Exoforia mod","Esotropia","Exotropia","Iperforia OD","Iperforia OS"],
                    _g(d,"ct_lon"), f"{px}_ct_l")
    with c6[1]:
        ct_vic = _s("Cover test vicino", ["—","Ortoforia","Esoforia lieve","Esoforia mod","Esoforia grave",
                    "Exoforia lieve","Exoforia mod","Esotropia","Exotropia","Iperforia OD","Iperforia OS"],
                    _g(d,"ct_vic"), f"{px}_ct_v")

    return {
        "dom_occhio":dom_occhio,"dom_mano":dom_mano,"dom_piede":dom_piede,
        "pursuit_orizz":pursuit_orizz,"pursuit_vert":pursuit_vert,
        "pursuit_diag":pursuit_diag,"pursuit_cerchi":pursuit_cerchi,
        "pursuit_testa":pursuit_testa,"sintomi_pursuit":sintomi_pursuit,
        "ppc_rot":ppc_rot,"ppc_rec":ppc_rec,"ppc_occhio":ppc_occhio,"ppc_note":ppc_note,
        "av_lon_od":av_lon_od,"av_lon_os":av_lon_os,"av_lon_oo":av_lon_oo,"av_cc_oo":av_cc_oo,
        "stereo_simb":stereo_simb,"stereo_anim":stereo_anim,"stereo_anel":stereo_anel,
        "ct_lon":ct_lon,"ct_vic":ct_vic,
    }


# ─────────────────────────────────────────────────────────────────────────────
# S2 — TEST SPAZIALI OEP
# ─────────────────────────────────────────────────────────────────────────────

OEP_NORME = {
    "#3":  ("Foria abituale lontano", "1X eso", 1.0, 2.0),
    "#13A":("Foria abituale vicino", "3X eso", 3.0, 3.0),
    "#8":  ("Foria indotta lontano", "1X eso", 1.0, 2.0),
    "#13B":("Foria indotta vicino", "3X eso", 3.0, 3.0),
    "#9":  ("Sfocatura BE lontano", "9 DP", 9.0, 4.0),
    "#10": ("Rottura BE lontano", "19 DP", 19.0, 8.0),
    "#10r":("Recupero BE lontano", "10 DP", 10.0, 4.0),
    "#11": ("Rottura BI lontano", "7 DP", 7.0, 3.0),
    "#11r":("Recupero BI lontano", "4 DP", 4.0, 2.0),
    "#16A":("Sfocatura BE vicino", "17 DP", 17.0, 5.0),
    "#16B":("Rottura BE vicino", "21 DP", 21.0, 6.0),
    "#16r":("Recupero BE vicino", "11 DP", 11.0, 7.0),
    "#17A":("Sfocatura BI vicino", "13 DP", 13.0, 4.0),
    "#17B":("Rottura BI vicino", "21 DP", 21.0, 4.0),
    "#17r":("Recupero BI vicino", "13 DP", 13.0, 5.0),
    "#20": ("ARP", "2.00 D", 2.00, 0.50),
    "#21": ("ARN", "-1.00 D", -1.00, 0.50),
    "MEM": ("Retinoscopia MEM", "+0.50 D", 0.50, 0.25),
    "#7A": ("Soggettivo #7A (lag acc.)", "-0.50 D", -0.50, 0.25),
}

def s2_spaziali(d: dict, px: str) -> dict:
    st.markdown("### 📐 S2 — Test Spaziali OEP")
    st.caption("Valori normativi Morgan. H=High, L=Low rispetto alla norma.")

    risultati = {}

    # Forie e retinoscopia
    with st.expander("**Forie e Retinoscopia**", expanded=True):
        c = st.columns(4)
        for i, (code, label) in enumerate([
            ("#3","Foria abit. lon."),("#13A","Foria abit. vic."),
            ("#8","Foria ind. lon."),("#13B","Foria ind. vic."),
        ]):
            with c[i]:
                val = _n(label, _g(d,code), f"{px}_oep_{code.replace('#','')}", -20, 20, 0.5, "%.1f")
                risultati[code] = val
                n = OEP_NORME.get(code)
                if n and val != 0:
                    ds = _ds(val, n[2], n[3])
                    txt, tipo = _ris(ds, inverso=False)
                    st.caption(f"norma: {n[1]} → {txt}")

        c2 = st.columns(3)
        with c2[0]:
            rx_l_od = st.text_input("Ret. L OD (sf/cil/ax)", _g(d,"rx_l_od"), key=f"{px}_rxlod")
            rx_l_os = st.text_input("Ret. L OS", _g(d,"rx_l_os"), key=f"{px}_rxlos")
        with c2[1]:
            rx_v_od = st.text_input("Ret. V OD (MEM)", _g(d,"rx_v_od"), key=f"{px}_rxvod")
            rx_v_os = st.text_input("Ret. V OS (MEM)", _g(d,"rx_v_os"), key=f"{px}_rxvos")
        with c2[2]:
            mem_val = _n("MEM OD (D)", _g(d,"MEM"), f"{px}_mem", -2, 3, 0.25, "%.2f")
            risultati["MEM"] = mem_val
            n = OEP_NORME["MEM"]
            if mem_val != 0:
                ds = _ds(mem_val, n[2], n[3])
                txt, tipo = _ris(ds, inverso=False)
                st.caption(f"norma {n[1]} → {txt}")

    # Soggettivo
    with st.expander("**Soggettivo #7 e #7A**", expanded=False):
        c = st.columns(4)
        with c[0]: s7_od = st.text_input("#7 OD (sf/cil/ax)", _g(d,"s7_od"), key=f"{px}_s7od")
        with c[1]: s7_os = st.text_input("#7 OS", _g(d,"s7_os"), key=f"{px}_s7os")
        with c[2]: s7a_od = _n("#7A OD (lag acc.)", _g(d,"#7A"), f"{px}_s7a", -2, 2, 0.25, "%.2f")
        with c[3]: s7a_os = _n("#7A OS", _g(d,"s7a_os"), f"{px}_s7aos", -2, 2, 0.25, "%.2f")
        risultati["#7A"] = s7a_od

    # Vergenze
    with st.expander("**Vergenze BI/BE lontano e vicino**", expanded=False):
        st.markdown("*Lontano*")
        c = st.columns(4)
        for i, (code, label) in enumerate([
            ("#9","Sf BE lon."),("#10","Rot. BE lon."),("#10r","Rec. BE lon."),
        ]):
            with c[i]:
                val = _n(label, _g(d,code), f"{px}_{code.replace('#','').replace(' ','')}", 0, 60, 1, "%.0f")
                risultati[code] = val
                n = OEP_NORME.get(code)
                if n:
                    ds = _ds(val, n[2], n[3])
                    txt, tipo = _ris(ds)
                    st.caption(f"norma {n[1]} → {txt}")
        with c[3]:
            val11 = _n("#11 Rot. BI lon.", _g(d,"#11"), f"{px}_11", 0, 30, 1, "%.0f")
            risultati["#11"] = val11
            n = OEP_NORME["#11"]
            ds = _ds(val11, n[2], n[3])
            txt, tipo = _ris(ds)
            st.caption(f"norma {n[1]} → {txt}")

        st.markdown("*Vicino*")
        c2 = st.columns(4)
        for i, (code, label) in enumerate([
            ("#16A","Sf BE vic."),("#16B","Rot. BE vic."),("#16r","Rec. BE vic."),("#17A","Sf BI vic."),
        ]):
            with c2[i]:
                val = _n(label, _g(d,code), f"{px}_{code.replace('#','').replace(' ','')}_v", 0, 60, 1, "%.0f")
                risultati[code] = val

    # ARP/ARN
    with st.expander("**ARP / ARN (#20 / #21)**", expanded=False):
        c = st.columns(2)
        with c[0]:
            arp = _n("ARP #20 (D)", _g(d,"#20"), f"{px}_arp", 0, 5, 0.25, "%.2f")
            risultati["#20"] = arp
            if arp > 0: _show_ris("ARP", arp, 2.0, 0.5, unit="D")
        with c[1]:
            arn = _n("ARN #21 (D)", _g(d,"#21"), f"{px}_arn", -3, 0, 0.25, "%.2f")
            risultati["#21"] = arn
            if arn != 0: _show_ris("ARN", arn, -1.0, 0.5, unit="D")

    risultati.update({
        "rx_l_od":rx_l_od,"rx_l_os":rx_l_os,
        "rx_v_od":rx_v_od,"rx_v_os":rx_v_os,
        "s7_od":s7_od,"s7_os":s7_os,"s7a_os":s7a_os,
    })
    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S3 — TEST OCULOMOTORI
# ─────────────────────────────────────────────────────────────────────────────

DEM_NORME = {
    6:(49.1,8.4,66.7,11.0,1.35,0.14,2.21,1.60),
    7:(41.8,7.3,53.7,9.2,1.28,0.12,1.78,1.40),
    8:(35.1,5.9,43.9,8.1,1.24,0.11,1.44,1.30),
    9:(30.4,5.2,38.3,7.4,1.20,0.10,1.24,1.18),
    10:(28.3,4.9,35.5,6.8,1.17,0.10,1.11,1.17),
    11:(26.1,4.5,32.3,6.3,1.14,0.09,1.01,1.10),
    12:(24.0,4.2,29.8,5.9,1.12,0.09,0.95,1.05),
    13:(22.5,4.0,27.5,5.5,1.11,0.09,0.88,1.00),
}
KD_NORME = {
    6:[(23.5,4.5,0.30,0.40),(25.0,5.0,0.40,0.50),(28.0,5.5,0.55,0.65),(76.5,15.0)],
    7:[(20.0,3.8,0.22,0.35),(21.5,4.2,0.30,0.40),(24.0,4.8,0.40,0.55),(65.5,12.8)],
    8:[(17.5,3.2,0.18,0.30),(18.5,3.6,0.22,0.35),(21.0,4.2,0.32,0.48),(57.0,11.0)],
    9:[(15.5,2.8,0.15,0.25),(16.5,3.2,0.18,0.30),(18.5,3.8,0.28,0.42),(50.5,9.8)],
    10:[(14.0,2.5,0.12,0.22),(15.0,2.9,0.15,0.26),(17.0,3.5,0.24,0.38),(46.0,8.9)],
    11:[(13.0,2.3,0.10,0.19),(13.8,2.6,0.13,0.23),(15.5,3.2,0.21,0.35),(42.3,8.1)],
    12:[(12.0,2.2,0.09,0.17),(12.8,2.4,0.11,0.20),(14.5,3.0,0.18,0.32),(39.3,7.6)],
}
GROFFMAN_NORME = {6:(18,4),7:(20,4),8:(23,4),9:(26,4),10:(28,3),11:(28,3),12:(29,3),13:(30,3)}
NSUCO_NORME = {
    (5,6):{"sacc":(3.0,3.5,3.5,4.0),"purs":(3.0,3.0,3.5,4.0)},
    (7,8):{"sacc":(4.0,4.0,4.0,4.5),"purs":(4.0,3.5,4.0,4.5)},
    (9,10):{"sacc":(4.5,4.5,4.5,5.0),"purs":(4.5,4.0,4.5,5.0)},
    (11,99):{"sacc":(5.0,5.0,5.0,5.0),"purs":(5.0,5.0,5.0,5.0)},
}

def _nsuco_norma(eta):
    for (emin,emax),v in NSUCO_NORME.items():
        if emin <= eta <= emax: return v
    return NSUCO_NORME[(11,99)]

def s3_oculomotori(d: dict, px: str) -> dict:
    st.markdown("### 👁️ S3 — Test Oculomotori")
    st.info("💡 Per DEM, K-D e Visual Tracking interattivi usa il **widget React** (`widget_test_interattivi.jsx`) "
            "oppure inserisci i risultati manualmente qui sotto.")

    eta = int(_n("Età paziente (anni)", _g(d,"eta",10), f"{px}_eta_ocm", 5, 18, 1))
    risultati = {"eta": eta}

    # DEM
    with st.expander("🔢 **DEM — Developmental Eye Movement Test**", expanded=True):
        c = st.columns(3)
        with c[0]:
            tv = _n("TV adj (sec)", _g(d,"dem","tv_adj"), f"{px}_dem_tv", 0, 200, 0.1, "%.1f")
            te = int(_n("Errori totali", _g(d,"dem","tot_err"), f"{px}_dem_err", 0, 50, 1))
        with c[1]:
            th = _n("TH adj (sec)", _g(d,"dem","th_adj"), f"{px}_dem_th", 0, 300, 0.1, "%.1f")
        with c[2]:
            ratio = _n("Ratio H/V", _g(d,"dem","ratio"), f"{px}_dem_ratio", 0, 5, 0.01, "%.2f")

        n = DEM_NORME.get(max(6,min(13,eta)), DEM_NORME[8])
        if tv > 0 or th > 0:
            ds_v = _ds(tv, n[0], n[1]); ds_h = _ds(th, n[2], n[3]); ds_r = _ds(ratio, n[4], n[5])
            v_ok = (-(ds_v or 0)) >= -1; h_ok = (-(ds_h or 0)) >= -1; r_ok = (-(ds_r or 0)) >= -1
            if v_ok and h_ok: tip = "I — Normale"
            elif v_ok and not h_ok: tip = "II — Disfunzione oculomotoria"
            elif not v_ok and not h_ok and r_ok: tip = "III — Disfunzione verbale"
            else: tip = "IV — Disfunzione oculomotoria e verbale"

            col1,col2,col3 = st.columns(3)
            col1.metric("TV adj", f"{tv:.1f}s", f"norma {n[0]:.0f}±{n[1]:.0f}")
            col2.metric("TH adj", f"{th:.1f}s", f"norma {n[2]:.0f}±{n[2]:.0f}")
            col3.metric("Ratio", f"{ratio:.2f}", f"norma {n[4]:.2f}±{n[5]:.2f}")
            st.markdown(f"**Tipologia DEM: `{tip}`**")
            risultati["dem"] = {"tv_adj":tv,"th_adj":th,"ratio":ratio,"tot_err":te,"tipologia":tip}
        note_dem = _t("Note DEM", _g(d,"dem","note"), f"{px}_dem_note")

    # K-D
    with st.expander("⚡ **K-D Test — King-Devick**", expanded=False):
        kd_norme = KD_NORME.get(max(6,min(12,eta)), KD_NORME[8])
        kd_res = {}
        cols = st.columns(4)
        for i, label in enumerate(["Demo","Card 1","Card 2","Card 3"]):
            with cols[i]:
                st.markdown(f"**{label}**")
                t = _n("Tempo (s)", _g(d,"kd",f"t{i}"), f"{px}_kdt{i}", 0, 200, 0.1, "%.1f")
                e = int(_n("Errori", _g(d,"kd",f"e{i}"), f"{px}_kde{i}", 0, 20, 1))
                kd_res[f"t{i}"] = t; kd_res[f"e{i}"] = e
                if i >= 1 and t > 0:
                    n = kd_norme[i-1]
                    ds = _ds(t, n[0], n[1])
                    txt, tipo = _ris(ds, inverso=True)
                    st.caption(f"norma {n[0]:.1f}±{n[1]:.1f}s → {txt}")

        tot_t = kd_res.get("t1",0)+kd_res.get("t2",0)+kd_res.get("t3",0)
        tot_e = int(kd_res.get("e1",0)+kd_res.get("e2",0)+kd_res.get("e3",0))
        st.metric("Totale", f"{tot_t:.1f}s / {tot_e} err", f"norma {kd_norme[3][0]:.0f}±{kd_norme[3][1]:.0f}s")
        kd_res["tot_tempo"] = tot_t; kd_res["tot_errori"] = tot_e
        risultati["kd"] = kd_res

    # NSUCO
    with st.expander("👁️ **NSUCO Oculomotor Test**", expanded=False):
        n_norma = _nsuco_norma(eta)
        nsuco_res = {}
        for tipo_moto, label in [("saccadi","Saccadi"),("pursuit","Pursuit")]:
            st.markdown(f"**{label}**")
            c = st.columns(4)
            for i, (param, pmax) in enumerate([("abilita",5),("accuratezza",5),("testa",5),("corpo",5)]):
                with c[i]:
                    val = int(_n(param.capitalize(), _g(d,"nsuco",tipo_moto,param,3),
                                 f"{px}_nsuco_{tipo_moto}_{param}", 1, 5, 1))
                    nsuco_res[f"{tipo_moto}_{param}"] = val
                    n_atteso = n_norma[tipo_moto][i] if tipo_moto in n_norma else 4
                    if val < n_atteso - 1:
                        st.caption(f"⚠️ sotto norma (≥{n_atteso:.0f})")
                    else:
                        st.caption(f"✅ norma ≥{n_atteso:.0f}")
        risultati["nsuco"] = nsuco_res

    # Groffman
    with st.expander("🔗 **Groffman Visual Tracing**", expanded=False):
        g_tot = 0
        g_res = {}
        cols = st.columns(5)
        for i, perc in enumerate(["A","B","C","D","E"]):
            with cols[i]:
                st.markdown(f"**{perc}**")
                punti = int(_n(f"Punti {perc}", _g(d,"groffman",f"punti_{perc}"), f"{px}_gr_{perc}", 0, 10, 1))
                g_res[f"punti_{perc}"] = punti; g_tot += punti
        n_g = GROFFMAN_NORME.get(max(6,min(13,eta)),(28,3))
        ds_g = _ds(g_tot, n_g[0], n_g[1])
        txt, tipo = _ris(ds_g)
        getattr(st, tipo)(f"Totale Groffman: {g_tot}/50 (norma {n_g[0]}±{n_g[1]}) → {txt}")
        g_res["totale"] = g_tot
        risultati["groffman"] = g_res

    # Visual Tracking
    with st.expander("🎯 **Visual Tracking**", expanded=False):
        c = st.columns(3)
        with c[0]: vt_tempo = _n("Tempo (s)", _g(d,"visual_tracking","tempo"), f"{px}_vt_t", 0, 300, 1)
        with c[1]: vt_pct = _n("% correttezza", _g(d,"visual_tracking","pct_corr"), f"{px}_vt_pct", 0, 100, 1)
        with c[2]: vt_persi = int(_n("Segno perso (n°)", _g(d,"visual_tracking","perso"), f"{px}_vt_persi", 0, 20, 1))
        vt_note = _t("Note Visual Tracking", _g(d,"visual_tracking","note"), f"{px}_vt_note")
        if vt_pct > 0:
            if vt_pct >= 90: st.success(f"Visual Tracking {vt_pct:.0f}% → ✅ Nella norma")
            elif vt_pct >= 70: st.warning(f"Visual Tracking {vt_pct:.0f}% → 🟡 Limite")
            else: st.error(f"Visual Tracking {vt_pct:.0f}% → 🔴 Sotto norma")
        risultati["visual_tracking"] = {"tempo":vt_tempo,"pct_corr":vt_pct,"perso":vt_persi,"note":vt_note}

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S4 — TEST ACCOMODATIVI
# ─────────────────────────────────────────────────────────────────────────────

FOCUS_MONO = {6:(5.5,2.5),7:(6.5,2.0),8:(7.0,2.5),9:(7.0,2.5),10:(7.0,2.5),
              11:(7.0,2.5),12:(7.0,2.5),13:(11.0,5.0)}
FOCUS_BINO = {6:(3.0,2.5),7:(3.5,2.5),8:(5.0,2.5),9:(5.0,2.5),10:(5.0,2.5),
              11:(5.0,2.5),12:(5.0,2.5),13:(8.0,5.0)}

def s4_accomodativi(d: dict, px: str) -> dict:
    st.markdown("### 🔭 S4 — Test Accomodativi")
    eta = int(_n("Età (anni)", _g(d,"eta",10), f"{px}_eta_acc4", 5, 50, 1))
    risultati = {"eta": eta}

    asp_ppa_od = 15 - eta/4
    asp_ppa_bino = 18 - eta/3

    with st.expander("**PPA — Punto Prossimo di Accomodazione**", expanded=True):
        c = st.columns(3)
        with c[0]: ppa_od = _n("OD (cm)", _g(d,"ppa","od_cm"), f"{px}_ppa_od4", 0, 50, 0.5, "%.1f")
        with c[1]: ppa_os = _n("OS (cm)", _g(d,"ppa","os_cm"), f"{px}_ppa_os4", 0, 50, 0.5, "%.1f")
        with c[2]: ppa_b  = _n("Bino (cm)", _g(d,"ppa","bino_cm"), f"{px}_ppa_b4", 0, 50, 0.5, "%.1f")
        def cm2dt(cm): return round(100/cm, 2) if cm > 0 else 0
        od_dt = cm2dt(ppa_od); os_dt = cm2dt(ppa_os); b_dt = cm2dt(ppa_b)
        st.caption(f"OD: {od_dt:.2f}dt (asp≥{asp_ppa_od:.1f}) | OS: {os_dt:.2f}dt | Bino: {b_dt:.2f}dt (asp≥{asp_ppa_bino:.1f})")
        if ppa_od > 0: _show_ris("PPA OD", od_dt, asp_ppa_od, 2.0, unit="dt")
        risultati["ppa"] = {"od_cm":ppa_od,"os_cm":ppa_os,"bino_cm":ppa_b,
                            "od_dt":od_dt,"os_dt":os_dt,"bino_dt":b_dt}

    with st.expander("**Focus Flexibility (flessibilità accomodativa)**", expanded=False):
        c = st.columns(3)
        with c[0]: ff_od = _n("OD (cpm)", _g(d,"focus_flex","od"), f"{px}_ff_od4", 0, 30, 0.5, "%.1f")
        with c[1]: ff_os = _n("OS (cpm)", _g(d,"focus_flex","os"), f"{px}_ff_os4", 0, 30, 0.5, "%.1f")
        with c[2]: ff_b  = _n("Bino (cpm)", _g(d,"focus_flex","bino"), f"{px}_ff_b4", 0, 30, 0.5, "%.1f")
        ek = max(6,min(13,eta))
        nm = FOCUS_MONO.get(ek,(7,2.5)); nb = FOCUS_BINO.get(ek,(5,2.5))
        _show_ris("Focus Flex OD", ff_od, nm[0], nm[1], unit=" cpm")
        _show_ris("Focus Flex Bino", ff_b, nb[0], nb[1], unit=" cpm")
        risultati["focus_flex"] = {"od":ff_od,"os":ff_os,"bino":ff_b}

    with st.expander("**Fusion Flexibility + Acc-Verg Flexibility**", expanded=False):
        fus_b = _n("Fusion Flex Bino (cpm)", _g(d,"fusion_flex","bino"), f"{px}_fus_b4", 0, 30, 0.5, "%.1f")
        _show_ris("Fusion Flex", fus_b, 8.1, 4.3, unit=" cpm")
        c = st.columns(2)
        with c[0]: av80 = _n("Acc-Verg Flex 20/80 (cicli/30s)", _g(d,"acc_verg","v80"), f"{px}_av80_4", 0, 40, 1)
        with c[1]: av25 = _n("Acc-Verg Flex 20/25 (cicli/30s)", _g(d,"acc_verg","v25"), f"{px}_av25_4", 0, 40, 1)
        asp_av = 16 if eta >= 13 else 12
        if av80 > 0: _show_ris("Acc-Verg 20/80", av80, asp_av, 4.0)
        risultati["fusion_flex"] = {"bino":fus_b}
        risultati["acc_verg"] = {"v80":av80,"v25":av25}

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S5 — TEST VISUO-PERCETTIVI (TVPS-3)
# ─────────────────────────────────────────────────────────────────────────────

TVPS_MEDIA_RAW = {
    5:{"disc":7,"mem":5,"spaz":5,"cost":7,"seq":4,"fig":5,"chius":5},
    6:{"disc":9,"mem":7,"spaz":7,"cost":9,"seq":6,"fig":7,"chius":7},
    7:{"disc":11,"mem":9,"spaz":9,"cost":10,"seq":8,"fig":9,"chius":9},
    8:{"disc":12,"mem":10,"spaz":10,"cost":11,"seq":9,"fig":10,"chius":10},
    9:{"disc":13,"mem":11,"spaz":11,"cost":12,"seq":10,"fig":11,"chius":11},
    10:{"disc":13,"mem":12,"spaz":12,"cost":12,"seq":11,"fig":12,"chius":12},
    11:{"disc":14,"mem":12,"spaz":13,"cost":13,"seq":12,"fig":13,"chius":13},
    12:{"disc":14,"mem":13,"spaz":13,"cost":13,"seq":12,"fig":13,"chius":13},
    13:{"disc":15,"mem":13,"spaz":14,"cost":14,"seq":13,"fig":14,"chius":14},
}
TVPS_SUBS = [("disc","Discriminazione"),("mem","Memoria"),("spaz","Rel. Spaziali"),
             ("cost","Costanza forma"),("seq","Mem. Sequenziale"),("fig","Figura-sfondo"),("chius","Chiusura")]

def s5_visuo_percettivi(d: dict, px: str) -> dict:
    st.markdown("### 🎨 S5 — Test Visuo-Percettivi (TVPS-3)")
    eta = int(_n("Età (anni)", _g(d,"eta",8), f"{px}_eta_tvps5", 4, 18, 1))
    raw = {}; scaled = {}

    cols = st.columns(4)
    for i, (code, nome) in enumerate(TVPS_SUBS):
        with cols[i%4]:
            r = int(_n(nome[:18], _g(d,"raw",code), f"{px}_tvps5_{code}", 0, 16, 1))
            raw[code] = r
            ek = max(5,min(13,eta)); media = TVPS_MEDIA_RAW.get(ek,TVPS_MEDIA_RAW[8]).get(code,8)
            sc = max(1, min(19, 10 + round((r - media) * 3/3)))
            scaled[code] = sc
            pct_map = {1:1,2:1,3:1,4:2,5:5,6:9,7:16,8:25,9:37,10:50,
                       11:63,12:75,13:84,14:91,15:95,16:98,17:99,18:99,19:99}
            pct = pct_map.get(sc, 50)
            st.caption(f"Scaled: **{sc}** | {pct}° %ile")

    sc_sum = sum(scaled.values())
    std = max(40, min(160, round(100 + (sc_sum - 70) * 15/21)))
    pct_g = {1:1,2:1,3:1,4:2,5:5,6:9,7:16,8:25,9:37,10:50,11:63,12:75,
             13:84,14:91,15:95,16:98,17:99,18:99,19:99}.get(max(1,min(19,round(sc_sum/7))),50)
    classifica = ("Molto superiore" if std>=130 else "Superiore" if std>=120 else
                  "Sopra la media" if std>=110 else "Nella media" if std>=90 else
                  "Sotto la media" if std>=80 else "Limite" if std>=70 else "Molto sotto la media")

    st.metric("Standard Score TVPS-3", std, f"Percentile ~{pct_g}° — {classifica}")
    if std >= 85: st.success(f"✅ {classifica}")
    elif std >= 70: st.warning(f"🟡 {classifica}")
    else: st.error(f"🔴 {classifica} (std={std})")

    return {"eta":eta,"raw":raw,"scaled":scaled,
            "calcoli":{"std":std,"percentile":pct_g,"classifica":classifica}}


# ─────────────────────────────────────────────────────────────────────────────
# S6 — RELAZIONI VISUO-SPAZIALI (Piaget + Gardner)
# ─────────────────────────────────────────────────────────────────────────────

PIAGET_ETA = {5:["A"],6:["A"],7:["A","C"],8:["A","B","C","D"],
              9:["A","B","C","D"],10:["A","B","C","D"],11:["A","B","C","D","E"]}
PIAGET_TESTS_N = {"A":6,"B":6,"C":4,"D":2,"E":6}

GARDNER_NORME_E = {5:(3.5,2.0),6:(2.5,1.8),7:(1.8,1.5),8:(1.2,1.2),9:(0.8,1.0),10:(0.5,0.8)}

def s6_visuo_spaziali(d: dict, px: str) -> dict:
    st.markdown("### ↔️ S6 — Relazioni Visuo-Spaziali")
    risultati = {}

    # Piaget
    with st.expander("**Test di Piaget (Consapevolezza Destra/Sinistra)**", expanded=True):
        st.info("💡 Per somministrazione interattiva usa il **widget React**")
        eta_p = int(_n("Età (anni)", _g(d,"piaget","eta",7), f"{px}_eta_piag", 5, 11, 1))
        attesi = PIAGET_ETA.get(max(5,min(11,eta_p)),["A"])
        st.caption(f"Livelli attesi al 75% per età {eta_p}: **{', '.join(attesi)}**")

        piaget_res = {"eta": eta_p}
        for t, n_items in PIAGET_TESTS_N.items():
            c = st.columns([3,1,1])
            with c[0]: st.markdown(f"**Test {t}** ({n_items} item)")
            with c[1]: corr = int(_n(f"Corr.", _g(d,"piaget",f"{t}_corr",0), f"{px}_piag_{t}", 0, n_items, 1))
            with c[2]:
                pct = round(corr/n_items*100)
                is_atteso = t in attesi
                if pct >= 75: st.success(f"{pct}% ✓")
                elif is_atteso: st.error(f"{pct}% ✗")
                else: st.warning(f"{pct}%")
            piaget_res[f"{t}_corr"] = corr; piaget_res[f"{t}_pct"] = pct
        risultati["piaget"] = piaget_res

    # Gardner
    with st.expander("**Gardner Reversal Frequency Test**", expanded=False):
        eta_g = int(_n("Età (anni)", _g(d,"gardner","eta",6), f"{px}_eta_gard6", 5, 10, 1))
        sesso_g = _s("Sesso", ["M","F","—"], _g(d,"gardner","sesso","—"), f"{px}_sesso_gard6")
        c = st.columns(3)
        with c[0]: es_inv = int(_n("Esec. inversioni", _g(d,"gardner","es_inv"), f"{px}_gard_esi", 0, 25, 1))
        with c[1]: es_ign = int(_n("Esec. non conoscenza", _g(d,"gardner","es_ign"), f"{px}_gard_esign", 0, 25, 1))
        with c[2]: ric_err = int(_n("Riconosc. errori (0-42)", _g(d,"gardner","ric_err"), f"{px}_gard_ric", 0, 42, 1))
        es_tot = es_inv + es_ign
        n_g = GARDNER_NORME_E.get(max(5,min(10,eta_g)),(1.5,1.2))
        _show_ris("Esecuzione", es_tot, n_g[0], n_g[1], inverso=True, unit=" err")
        risultati["gardner"] = {"eta":eta_g,"sesso":sesso_g,"es_inv":es_inv,
                                "es_ign":es_ign,"es_tot":es_tot,"ric_err":ric_err}

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S7 — SCREENING GROSSO MOTORIO (SUNY + WACHS)
# ─────────────────────────────────────────────────────────────────────────────

SUNY_ITEMS = [
    "Entrambe le braccia (omologo)",
    "Braccio destro (monolaterale)",
    "Braccio sinistro (monolaterale)",
    "Gamba destra (monolaterale)",
    "Gamba sinistra (monolaterale)",
    "Braccio dx e gamba dx (omolaterale)",
    "Braccio sx e gamba sx (omolaterale)",
    "Braccio dx e gamba sx (controlaterale)",
    "Braccio sx e gamba dx (controlaterale)",
]
SUNY_ETA_NORME = {
    3:"Omologo con disponesi",
    4:"Omologo e monolaterale",
    5:"Omologo, mono e omo con disponesi",
    6:"Come sopra, disponesi poco evidente",
    7:"Tutti i pattern, disponesi minima nel controlaterale",
    8:"Tutti i pattern al massimo livello",
}

def s7_grosso_motorio(d: dict, px: str) -> dict:
    st.markdown("### 🏃 S7 — Screening Grosso Motorio")
    risultati = {}

    with st.expander("**SUNY — Batteria Grosso-Motoria (Angeli nella neve)**", expanded=True):
        eta_s = int(_n("Età (anni)", _g(d,"suny","eta",6), f"{px}_eta_suny", 3, 10, 1))
        st.caption(f"Livello atteso età {eta_s}: **{SUNY_ETA_NORME.get(max(3,min(8,eta_s)),'—')}**")

        suny_res = {"eta": eta_s}
        st.markdown("**Risultato per ogni movimento:**")
        for i, item in enumerate(SUNY_ITEMS):
            ris = _s(item, ["—","✅ Corretto","⚠️ Con disponesi","❌ Non eseguito/segmentato"],
                     _g(d,"suny",f"item_{i}","—"), f"{px}_suny_{i}")
            suny_res[f"item_{i}"] = ris

        livello_suny = _s("Livello d'età raggiunto",
                          ["—","3 anni","4 anni","5 anni","6 anni","7 anni","8 anni"],
                          _g(d,"suny","livello","—"), f"{px}_suny_livello")
        suny_res["livello"] = livello_suny

        # Prove aggiuntive SUNY
        st.markdown("**Prove aggiuntive:**")
        c = st.columns(2)
        with c[0]:
            saltelli = _s("Tre saltelli alternati", ["—","3 anni (non riesce)","4 anni (su un piede)",
                "5 anni (entrambi, non alternati)","6 anni (alternati, non fluidi)",
                "7 anni (leggera pausa)","8 anni (fluido)"],
                _g(d,"suny","saltelli","—"), f"{px}_suny_salt")
        with c[1]:
            cerchi = _s("Cerchi bimanuali lavagna", ["—","3 anni (un braccio)","4 anni (simmetrici breve)",
                "5 anni (simmetrici ok)","6 anni (1-2 reciproci)","7 anni (reciproci con calo)",
                "8 anni (tutti ok)"],
                _g(d,"suny","cerchi","—"), f"{px}_suny_cerc")
        suny_res["saltelli"] = saltelli; suny_res["cerchi"] = cerchi
        risultati["suny"] = suny_res

    with st.expander("**WACHS — Analisi Strutture Cognitive (Sub-test IV Movimento)**", expanded=False):
        wachs_items = [
            "Solleva parti singole (su comando tattile)",
            "Movimenti bilaterali simmetrici",
            "Movimenti bilaterali asimmetrici",
            "Movimenti controlaterali",
            "Rotazione del corpo",
            "Salto su un piede",
        ]
        wachs_res = {}
        for i, item in enumerate(wachs_items):
            ris = _s(item, ["—","✅ Sì","❌ No"], _g(d,"wachs",f"item_{i}","—"), f"{px}_wachs_{i}")
            wachs_res[f"item_{i}"] = ris
        livello_wachs = _s("Livello d'età WACHS",
                           ["—","3-4 anni","5-6 anni","7-8 anni","8+ anni"],
                           _g(d,"wachs","livello","—"), f"{px}_wachs_liv")
        wachs_res["livello"] = livello_wachs
        note_wachs = _t("Note WACHS", _g(d,"wachs","note"), f"{px}_note_wachs")
        wachs_res["note"] = note_wachs
        risultati["wachs"] = wachs_res

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S8 — INTEGRAZIONE VISUO-MOTORIA (VMI + WOLD)
# ─────────────────────────────────────────────────────────────────────────────

VMI_RAW_STD = {
    (3,3):[(0,55),(3,70),(6,85),(9,100),(12,115),(15,130)],
    (4,4):[(2,55),(5,70),(8,85),(11,100),(14,115),(17,130)],
    (5,5):[(4,55),(7,70),(10,85),(13,100),(16,115),(19,130)],
    (6,6):[(6,55),(9,70),(12,85),(15,100),(18,115),(21,130)],
    (7,7):[(8,55),(11,70),(14,85),(17,100),(20,115),(23,130)],
    (8,8):[(10,55),(13,70),(16,85),(19,100),(22,115),(25,130)],
    (9,9):[(12,55),(15,70),(17,85),(20,100),(23,115),(26,130)],
    (10,12):[(13,55),(16,70),(18,85),(21,100),(24,115),(27,130)],
    (13,15):[(15,55),(18,70),(20,85),(23,100),(25,115),(27,130)],
}

def _vmi_std(raw, eta):
    for (emin,emax), tbl in VMI_RAW_STD.items():
        if emin <= int(eta) <= emax:
            for j in range(len(tbl)-1):
                r0,s0=tbl[j]; r1,s1=tbl[j+1]
                if r0<=raw<=r1: return round(s0+(raw-r0)/(max(r1-r0,1))*(s1-s0))
            return tbl[0][1] if raw<=tbl[0][0] else tbl[-1][1]
    return 100

def _std_pct(std):
    if std>=130:return 98
    if std>=120:return 91
    if std>=110:return 75
    if std>=100:return 50
    if std>=90:return 25
    if std>=80:return 9
    if std>=70:return 2
    return 1

def s8_visuo_motoria(d: dict, px: str) -> dict:
    st.markdown("### ✏️ S8 — Integrazione Visuo-Motoria")
    risultati = {}

    with st.expander("**VMI — Beery Visual Motor Integration**", expanded=True):
        c = st.columns(2)
        with c[0]: eta_v = _n("Età (anni)", _g(d,"vmi","eta",8), f"{px}_eta_vmi8", 3, 18, 1)
        with c[1]: raw_v = int(_n("Punteggio grezzo (figure corrette)", _g(d,"vmi","raw"), f"{px}_vmi_raw8", 0, 27, 1))
        std_v = _vmi_std(raw_v, eta_v)
        pct_v = _std_pct(std_v)
        cl_v = ("Molto superiore" if std_v>=130 else "Superiore" if std_v>=120 else
                "Sopra la media" if std_v>=110 else "Nella media" if std_v>=90 else
                "Sotto la media" if std_v>=80 else "Limite" if std_v>=70 else "Molto sotto la media")
        st.metric("Standard score VMI", std_v, f"~{pct_v}° percentile")
        if std_v>=85: st.success(f"✅ {cl_v}")
        elif std_v>=70: st.warning(f"🟡 {cl_v}")
        else: st.error(f"🔴 {cl_v}")
        risultati["vmi"] = {"eta":eta_v,"raw":raw_v,"std":std_v,"percentile":pct_v,"classifica":cl_v}

    with st.expander("**WOLD — Test Visuo-Motorio**", expanded=False):
        st.caption("3 sezioni. Punteggio: errori = stacchi della matita dai puntini.")
        c = st.columns(3)
        with c[0]: wold_t1 = _n("Sez. 1 — Tempo (s)", _g(d,"wold","t1"), f"{px}_wold_t1", 0, 300, 1)
        with c[1]: wold_t2 = _n("Sez. 2 — Tempo (s)", _g(d,"wold","t2"), f"{px}_wold_t2", 0, 300, 1)
        with c[2]: wold_t3 = _n("Sez. 3 — Tempo (s)", _g(d,"wold","t3"), f"{px}_wold_t3", 0, 300, 1)
        c2 = st.columns(3)
        with c2[0]: wold_e1 = int(_n("Sez. 1 — Errori", _g(d,"wold","e1"), f"{px}_wold_e1", 0, 50, 1))
        with c2[1]: wold_e2 = int(_n("Sez. 2 — Errori", _g(d,"wold","e2"), f"{px}_wold_e2", 0, 50, 1))
        with c2[2]: wold_e3 = int(_n("Sez. 3 — Errori", _g(d,"wold","e3"), f"{px}_wold_e3", 0, 50, 1))
        risultati["wold"] = {"t1":wold_t1,"t2":wold_t2,"t3":wold_t3,
                             "e1":wold_e1,"e2":wold_e2,"e3":wold_e3}

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S9 — INTEGRAZIONE VISUO-UDITIVA E MEMORIA
# ─────────────────────────────────────────────────────────────────────────────

AVIT_NORME = {6:(6.5,None),7:(7.0,None),8:(7.5,None),9:(8.0,14.0),
              10:(None,15.0),11:(None,16.5),12:(None,17.5)}
VADS_NORME = {6:(3.0,2.5,2.5,2.0,10.0),7:(3.5,3.0,3.0,2.5,12.0),8:(4.0,3.5,3.5,3.0,14.0),
              9:(4.5,4.0,4.0,3.5,16.0),10:(5.0,4.5,4.5,4.0,18.0),11:(5.5,5.0,5.0,4.5,20.0)}
MONROE_NORME = {5:(3.5,1.5),6:(5.7,2.0),7:(7.6,2.0),8:(8.8,2.0),9:(10.4,2.0),10:(11.2,2.0)}
GETMAN_NORME_CL = {"K":4,"1":5,"2":6,"3":7,"4":8,"5":9,"6":10,"7":11,"8":12}

def s9_visuo_uditiva(d: dict, px: str) -> dict:
    st.markdown("### 🔊 S9 — Integrazione Visuo-Uditiva e Memoria")
    risultati = {}

    with st.expander("**AVIT — Test Integrazione Visuo-Uditiva (Birch & Belmont)**", expanded=True):
        eta_a = int(_n("Età (anni)", _g(d,"avit","eta",8), f"{px}_eta_avit9", 5, 14, 1))
        ver = _s("Versione", ["10 item (5.8-9 anni)","20 item (9+ anni)"],
                 _g(d,"avit","versione","10 item (5.8-9 anni)"), f"{px}_avit_ver9")
        max_it = 10 if "10" in ver else 20
        corr = int(_n(f"Corretti (/{max_it})", _g(d,"avit","corretti"), f"{px}_avit_corr9", 0, max_it, 1))
        n_avit = AVIT_NORME.get(max(6,min(12,eta_a)),(None,None))
        n_val = n_avit[0] if max_it==10 else n_avit[1]
        if n_val:
            _show_ris("AVIT", corr, n_val, 1.5)
        risultati["avit"] = {"eta":eta_a,"versione":ver,"corretti":corr}

    with st.expander("**VADS — Visuo-Auditory Digit Span (Koppitz)**", expanded=False):
        eta_v = int(_n("Età (anni)", _g(d,"vads","eta",8), f"{px}_eta_vads9", 5, 13, 1))
        c = st.columns(4)
        uo = int(_n("Uditivo-Orale", _g(d,"vads","uo"), f"{px}_vads_uo9", 0, 9, 1))
        with c[0]: st.metric("UO", uo)
        vo = int(_n("Visivo-Orale", _g(d,"vads","vo"), f"{px}_vads_vo9", 0, 9, 1))
        with c[1]: st.metric("VO", vo)
        us = int(_n("Uditivo-Scritto", _g(d,"vads","us"), f"{px}_vads_us9", 0, 9, 1))
        with c[2]: st.metric("US", us)
        vs = int(_n("Visivo-Scritto", _g(d,"vads","vs"), f"{px}_vads_vs9", 0, 9, 1))
        with c[3]: st.metric("VS", vs)
        tot = uo+vo+us+vs
        n_vads = VADS_NORME.get(max(6,min(11,eta_v)),(4,3.5,3.5,3,14))
        st.metric("VADS Totale", tot, f"norma≥{n_vads[4]:.0f}")
        risultati["vads"] = {"eta":eta_v,"uo":uo,"vo":vo,"us":us,"vs":vs,"tot":tot}

    with st.expander("**Monroe Visual III**", expanded=False):
        eta_m = int(_n("Età (anni)", _g(d,"monroe","eta",7), f"{px}_eta_mon9", 5, 10, 1))
        punti_m = _n("Punteggio (anche 0.5)", _g(d,"monroe","punti"), f"{px}_mon_punti", 0, 20, 0.5, "%.1f")
        n_mon = MONROE_NORME.get(max(5,min(10,int(eta_m))),(7,2))
        _show_ris("Monroe Visual III", punti_m, n_mon[0], n_mon[1])
        risultati["monroe"] = {"eta":eta_m,"punti":punti_m}

    with st.expander("**Getman — Test Manipolazione Visiva**", expanded=False):
        classe = _s("Classe scolastica", ["K","1","2","3","4","5","6","7","8"],
                    _g(d,"getman","classe","3"), f"{px}_getman_cl9")
        punti_get = int(_n("Punti totali (max 12)", _g(d,"getman","punti"), f"{px}_get_punti9", 0, 12, 1))
        norma_get = GETMAN_NORME_CL.get(classe, 7)
        if punti_get >= norma_get: st.success(f"✅ Getman: {punti_get}/12 (norma ≥{norma_get} per classe {classe})")
        elif punti_get >= norma_get-2: st.warning(f"🟡 Getman: {punti_get}/12 (limite)")
        else: st.error(f"🔴 Getman: {punti_get}/12 (sotto norma ≥{norma_get})")
        risultati["getman"] = {"classe":classe,"punti":punti_get,"norma":norma_get}

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# S10 — SINDROME VERTIGINOSA VISIVA (SVV)
# ─────────────────────────────────────────────────────────────────────────────

SVV_SINTOMI = [
    ("auto","Nausea in auto (anche su strade rettilinee)"),
    ("barca","Nausea su imbarcazioni (anche con mare calmo)"),
    ("giostre","Fastidio guardando oggetti che ruotano/dondolano"),
    ("testa","Instabilità/nausea con rotazione rapida della testa"),
    ("altezza","Fastidio in luoghi elevati o scale trasparenti"),
    ("cinema","Nausea al cinema (specialmente scene dinamiche)"),
    ("folla","Disagio, ansia, nausea in luoghi affollati"),
    ("fotofobia","Fotofobia, fastidio luci artificiali/stroboscopiche"),
    ("cefalea","Frequenti cefalee"),
    ("palla","Difficoltà a colpire/afferrare una palla (tennis ecc.)"),
    ("goffaggine","Tendenza a sbattere/inciampare contro oggetti"),
    ("guida","Difficoltà nella guida notturna, abbagliamento fari"),
]

def s10_svv(d: dict, px: str) -> dict:
    st.markdown("### 🌀 S10 — Sindrome Vertiginosa Visiva (SVV)")
    st.caption("Dalla scheda clinica The Organism — SVV Anamnesi.")
    risultati = {}

    with st.expander("**Anamnesi SVV — Sintomi**", expanded=True):
        sintomi_pos = []
        c1, c2 = st.columns(2)
        for i, (code, label) in enumerate(SVV_SINTOMI):
            col = c1 if i%2==0 else c2
            with col:
                val = _cb(label, _g(d,"svv","sintomi",code), f"{px}_svv_{code}")
                if val: sintomi_pos.append(label)
                risultati.setdefault("svv",{}).setdefault("sintomi",{})[code] = val

        score_svv = len(sintomi_pos)
        if score_svv >= 6: st.error(f"🌀 SVV score: {score_svv}/12 → Alta probabilità SVV")
        elif score_svv >= 3: st.warning(f"🌀 SVV score: {score_svv}/12 → SVV possibile, approfondire")
        else: st.success(f"✅ SVV score: {score_svv}/12 → Basso rischio")

    with st.expander("**Test Clinici SVV**", expanded=False):
        st.markdown("**Pursuit Test** (30 sec con pallina oscillante)")
        pursuit_svv = _s("Insorgenza sintomi", ["—","Nessuno","Lieve","Moderato","Elevato"],
                         _g(d,"svv","pursuit","—"), f"{px}_svv_pursuit")

        st.markdown("**Turn in Place Test** (3 rotazioni)")
        c = st.columns(2)
        with c[0]:
            tip_base = _s("Senza target", ["—","Stabile","Lieve instabilità","Moderata","Grave"],
                          _g(d,"svv","tip_base","—"), f"{px}_svv_tip1")
        with c[1]:
            tip_dito = _s("Guardando dito", ["—","Migliora","Uguale","Peggiora"],
                          _g(d,"svv","tip_dito","—"), f"{px}_svv_tip2")
            tip_oc_chiuso = _s("Chiudendo un occhio", ["—","Migliora","Uguale","Peggiora"],
                              _g(d,"svv","tip_oc_chiuso","—"), f"{px}_svv_tip3")

        st.markdown("**Saccadic Test** (4 tabelle a 2.5m, 30 sec)")
        sacc_svv = _s("Risultato saccadico", ["—","Normale","Compensazione con testa","Instabilità",
                      "Saccadi molto imprecise","Sintomi vertiginosi"],
                      _g(d,"svv","sacc_svv","—"), f"{px}_svv_sacc")

        svv_note = _t("Note SVV", _g(d,"svv","note"), f"{px}_svv_note")
        risultati["svv"].update({
            "pursuit":pursuit_svv,"tip_base":tip_base,"tip_dito":tip_dito,
            "tip_oc_chiuso":tip_oc_chiuso,"sacc_svv":sacc_svv,
            "score":score_svv,"note":svv_note,
        })

    return risultati


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSI AUTOMATICA
# ─────────────────────────────────────────────────────────────────────────────

def _diagnosi(dati: dict) -> list[dict]:
    """
    Genera una lista di ipotesi diagnostiche basate sui pattern dei risultati.
    Ogni diagnosi: {titolo, criteri_soddisfatti, criteri_mancanti, livello (alta/media/bassa), note}
    """
    diagnosi = []
    s1 = dati.get("s1", {})
    s2 = dati.get("s2", {})
    s3 = dati.get("s3", {})
    s4 = dati.get("s4", {})

    # ── Insufficienza di Convergenza (IC)
    ppc_rot = float(s1.get("ppc_rot", 0) or 0)
    ct_vic = s1.get("ct_vic", "—")
    foria_vic = float(s2.get("#13A", 0) or 0)
    vergenza_be_vic = float(s2.get("#16B", 0) or 0)
    ic_criteri = []
    ic_mancanti = []
    if ppc_rot > 10: ic_criteri.append(f"PPC elevato ({ppc_rot}cm > 10cm")
    else: ic_mancanti.append("PPC nella norma")
    if foria_vic > 6: ic_criteri.append(f"Exoforia vicino elevata ({foria_vic}X)")
    if vergenza_be_vic < 15: ic_criteri.append(f"Vergenza BE vicino ridotta ({vergenza_be_vic}DP < 15)")
    if len(ic_criteri) >= 2:
        diagnosi.append({"titolo":"Insufficienza di Convergenza (IC)",
                         "criteri":ic_criteri,"mancanti":ic_mancanti,
                         "livello":"alta" if len(ic_criteri)>=3 else "media",
                         "note":"Approfondire con test di vergenza e foria associata"})

    # ── Disfunzione Oculomotoria (Saccadica)
    dem = dati.get("s3", {}).get("dem", {})
    tip_dem = dem.get("tipologia", "")
    kd = dati.get("s3", {}).get("kd", {})
    tot_kd = float(kd.get("tot_tempo", 0) or 0)
    err_kd = int(kd.get("tot_errori", 0) or 0)
    groffman = dati.get("s3", {}).get("groffman", {})
    tot_gr = float(groffman.get("totale", 0) or 0)

    dom_criteri = []
    if "II" in tip_dem or "IV" in tip_dem: dom_criteri.append(f"DEM Tipologia {tip_dem}")
    if tot_kd > 80: dom_criteri.append(f"K-D totale elevato ({tot_kd:.1f}s)")
    if err_kd > 5: dom_criteri.append(f"K-D errori elevati ({err_kd})")
    if tot_gr < 20: dom_criteri.append(f"Groffman sotto norma ({tot_gr:.0f}/50)")
    if len(dom_criteri) >= 2:
        diagnosi.append({"titolo":"Disfunzione dei Movimenti Oculomotori Saccadici",
                         "criteri":dom_criteri,"mancanti":[],
                         "livello":"alta" if len(dom_criteri)>=3 else "media",
                         "note":"Considerare Visual Training saccadico"})

    # ── Disfunzione Accomodativa
    acc = dati.get("s4", {})
    ppa_bino = float(acc.get("ppa", {}).get("bino_dt", 0) or 0)
    ff_bino = float(acc.get("focus_flex", {}).get("bino", 0) or 0)
    mem_val = float(s2.get("MEM", 0) or 0)
    acc_criteri = []
    eta_acc = int(acc.get("eta", 10) or 10)
    asp_acc = 18 - eta_acc/3
    if ppa_bino > 0 and ppa_bino < asp_acc - 2: acc_criteri.append(f"PPA ridotta ({ppa_bino:.2f}dt)")
    if ff_bino > 0 and ff_bino < 3: acc_criteri.append(f"Focus Flexibility bino ridotta ({ff_bino}cpm)")
    if mem_val > 1.0: acc_criteri.append(f"MEM elevato (+{mem_val:.2f}D — lag accomodativo)")
    if len(acc_criteri) >= 2:
        diagnosi.append({"titolo":"Disfunzione Accomodativa",
                         "criteri":acc_criteri,"mancanti":[],
                         "livello":"alta" if len(acc_criteri)>=3 else "media",
                         "note":"Valutare lenti positive per vicino e VT accomodativo"})

    # ── Disfunzione Visuo-Percettiva
    tvps = dati.get("s5", {}).get("calcoli", {})
    std_tvps = int(tvps.get("std", 100) or 100)
    vmi_std = int(dati.get("s8", {}).get("vmi", {}).get("std", 100) or 100)
    vp_criteri = []
    if std_tvps < 80: vp_criteri.append(f"TVPS-3 basso (std={std_tvps})")
    if vmi_std < 80: vp_criteri.append(f"VMI basso (std={vmi_std})")
    if len(vp_criteri) >= 1:
        diagnosi.append({"titolo":"Disfunzione Visuo-Percettiva e/o Visuo-Motoria",
                         "criteri":vp_criteri,"mancanti":[],
                         "livello":"alta" if len(vp_criteri)>=2 else "media",
                         "note":"Approfondire con TVPS subtest profilo e VMI"})

    # ── SVV
    svv = dati.get("s10", {}).get("svv", {})
    svv_score = int(svv.get("score", 0) or 0)
    if svv_score >= 3:
        diagnosi.append({"titolo":"Sindrome Vertiginosa Visiva (SVV)",
                         "criteri":[f"Score SVV: {svv_score}/12"],
                         "mancanti":[],
                         "livello":"alta" if svv_score>=6 else "media",
                         "note":"Escludere cause vestibolari periferiche. Valutare VT orientamento spaziale."})

    # ── Immaturità Oculomotoria Generale
    nsuco = dati.get("s3", {}).get("nsuco", {})
    sacc_ab = int(nsuco.get("saccadi_abilita", 5) or 5)
    purs_ab = int(nsuco.get("pursuit_abilita", 5) or 5)
    immat_criteri = []
    if sacc_ab <= 3: immat_criteri.append(f"NSUCO saccadi abilità bassa ({sacc_ab}/5)")
    if purs_ab <= 3: immat_criteri.append(f"NSUCO pursuit abilità bassa ({purs_ab}/5)")
    if len(immat_criteri) >= 2:
        diagnosi.append({"titolo":"Immaturità Oculomotoria Generale",
                         "criteri":immat_criteri,"mancanti":[],
                         "livello":"media",
                         "note":"Considerare VT oculomotorio base (pursuit e saccadi)"})

    return diagnosi


def render_diagnosi(dati: dict, px: str):
    st.markdown("### 🩺 Diagnosi Automatica")
    st.caption("Ipotesi diagnostiche basate sull'analisi automatica dei pattern. Richiedono conferma clinica.")

    diag_list = _diagnosi(dati)

    if not diag_list:
        st.success("✅ Nessun pattern disfunzionale rilevato dai dati inseriti.")
        return

    for d in diag_list:
        livello = d["livello"]
        colore = {"alta":"error","media":"warning","bassa":"info"}.get(livello,"info")
        icona = {"alta":"🔴","media":"🟡","bassa":"🟢"}.get(livello,"ℹ️")

        with st.container():
            getattr(st, colore)(f"{icona} **{d['titolo']}** — Probabilità: {livello.upper()}")
            if d["criteri"]:
                st.markdown("**Criteri soddisfatti:**")
                for c in d["criteri"]:
                    st.markdown(f"  ✓ {c}")
            if d["note"]:
                st.caption(f"💡 {d['note']}")
            st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def render_valutazione_visiva_funzionale(
    data_json: dict | None,
    prefix: str,
    readonly: bool = False,
) -> tuple[dict, str]:
    """
    Entry point. Batteria completa di valutazione visiva funzionale.
    data_json: dict salvato in visita_json["valutazione_visiva_funzionale"]
    """
    if data_json is None:
        data_json = {}

    st.markdown("## 👁️‍🗨️ Valutazione Visiva Funzionale — Batteria Completa")
    st.caption("Struttura OEP / The Organism · 10 sezioni · Diagnosi automatica")

    tabs = st.tabs([
        "🔍 S1 Preliminari",
        "📐 S2 Spaziali OEP",
        "👁️ S3 Oculomotori",
        "🔭 S4 Accomodazione",
        "🎨 S5 TVPS-3",
        "↔️ S6 Visuo-Spaziali",
        "🏃 S7 Grosso Motorio",
        "✏️ S8 Visuo-Motorio",
        "🔊 S9 Udito/Memoria",
        "🌀 S10 SVV",
        "🩺 Diagnosi",
    ])

    nuovi = dict(data_json)

    with tabs[0]:  nuovi["s1"] = s1_preliminari(data_json.get("s1",{}), f"{prefix}_s1")
    with tabs[1]:  nuovi["s2"] = s2_spaziali(data_json.get("s2",{}), f"{prefix}_s2")
    with tabs[2]:  nuovi["s3"] = s3_oculomotori(data_json.get("s3",{}), f"{prefix}_s3")
    with tabs[3]:  nuovi["s4"] = s4_accomodativi(data_json.get("s4",{}), f"{prefix}_s4")
    with tabs[4]:  nuovi["s5"] = s5_visuo_percettivi(data_json.get("s5",{}), f"{prefix}_s5")
    with tabs[5]:  nuovi["s6"] = s6_visuo_spaziali(data_json.get("s6",{}), f"{prefix}_s6")
    with tabs[6]:  nuovi["s7"] = s7_grosso_motorio(data_json.get("s7",{}), f"{prefix}_s7")
    with tabs[7]:  nuovi["s8"] = s8_visuo_motoria(data_json.get("s8",{}), f"{prefix}_s8")
    with tabs[8]:  nuovi["s9"] = s9_visuo_uditiva(data_json.get("s9",{}), f"{prefix}_s9")
    with tabs[9]:  nuovi["s10"] = s10_svv(data_json.get("s10",{}), f"{prefix}_s10")
    with tabs[10]: render_diagnosi(nuovi, prefix)

    nuovi["_meta"] = {"data": date.today().isoformat(), "versione": "vvf_v1"}

    # Summary compatto
    parts = []
    s3d = nuovi.get("s3",{})
    if s3d.get("dem",{}).get("tipologia"): parts.append(f"DEM {s3d['dem']['tipologia'][:2]}")
    if s3d.get("kd",{}).get("tot_tempo"): parts.append(f"KD {s3d['kd']['tot_tempo']:.0f}s")
    if nuovi.get("s5",{}).get("calcoli",{}).get("std"): parts.append(f"TVPS {nuovi['s5']['calcoli']['std']}")
    if nuovi.get("s8",{}).get("vmi",{}).get("std"): parts.append(f"VMI {nuovi['s8']['vmi']['std']}")
    diag = _diagnosi(nuovi)
    if diag: parts.append(f"Diag: {', '.join(d['titolo'][:20] for d in diag[:2])}")

    summary = " | ".join(parts) if parts else "VVF compilata"
    return nuovi, summary
