# -*- coding: utf-8 -*-
"""
Valutazione Visuo-Percettiva - The Organism
Notazione Skeffington/OEP
Sezioni: A Stato refrattivo, B Equilibrio binoculare,
C Accomodazione, D Oculomotricita, E Esame obiettivo,
F Profilo funzionale, G Prescrizione, H Sports Vision
"""
from __future__ import annotations
import json, datetime
import streamlit as st


# ══════════════════════════════════════════════════════════════════════
#  UTILITY
# ══════════════════════════════════════════════════════════════════════

def _get_user():
    return st.session_state.get("user") or {}

def _prof():
    return _get_user().get("username", "The Organism")

def _sk(sez, campo, pid):
    return f"vvp_{pid}_{sez}_{campo}"

def _carica(conn, pid):
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT visita_json FROM valutazioni_visive "
            "WHERE paziente_id=%s ORDER BY id DESC LIMIT 1", (pid,))
        row = cur.fetchone()
        if not row: return {}
        raw = row["visita_json"] if isinstance(row, dict) else row[0]
        if not raw: return {}
        return raw if isinstance(raw, dict) else json.loads(raw)
    except Exception:
        return {}

def _salva(conn, pid, dati):
    try:
        cur = conn.cursor()
        dump = json.dumps(dati, ensure_ascii=False, default=str)
        cur.execute(
            "SELECT id FROM valutazioni_visive WHERE paziente_id=%s ORDER BY id DESC LIMIT 1",
            (pid,))
        row = cur.fetchone()
        if row:
            vid = int(row["id"] if isinstance(row, dict) else row[0])
            cur.execute("UPDATE valutazioni_visive SET visita_json=%s::jsonb WHERE id=%s",
                        (dump, vid))
        else:
            cur.execute(
                "INSERT INTO valutazioni_visive "
                "(paziente_id, data_valutazione, professionista, visita_json) "
                "VALUES (%s,%s,%s,%s::jsonb)",
                (pid, datetime.date.today().isoformat(), _prof(), dump))
        conn.commit()
        st.success("Salvato.")
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore: {e}")

def _num(label, key, val=0.0, step=0.25, fmt="%.2f", mn=None, mx=None):
    kw = {"value": float(val or 0), "step": step, "format": fmt, "key": key}
    if mn is not None: kw["min_value"] = mn
    if mx is not None: kw["max_value"] = mx
    return st.number_input(label, **kw)

def _txt(label, key, val="", h=None):
    if h: return st.text_area(label, value=val or "", key=key, height=h)
    return st.text_input(label, value=val or "", key=key)

def _radio(label, opts, key, val=None):
    idx = opts.index(val) if val in opts else 0
    return st.radio(label, opts, index=idx, horizontal=True, key=key)

def _eta(dn_str):
    try:
        dn = datetime.date.fromisoformat(str(dn_str)[:10])
        anni = (datetime.date.today() - dn).days // 365
        return anni
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
#  INTESTAZIONE VISITA
# ══════════════════════════════════════════════════════════════════════

def _intestazione(pid, paziente, stored):
    s = lambda c: _sk("int", c, pid)
    d = stored.get("intestazione", {})

    st.markdown("### Dati visita")
    c1, c2, c3, c4 = st.columns(4)

    cog = paziente.get("Cognome","") if isinstance(paziente, dict) else ""
    nom = paziente.get("Nome","")    if isinstance(paziente, dict) else ""
    dn  = paziente.get("Data_Nascita","") if isinstance(paziente, dict) else ""
    eta_calc = _eta(dn)

    with c1:
        st.markdown(f"**Paziente:** {cog} {nom}")
        st.caption(f"Nato/a: {dn}")
    with c2:
        eta_vis = st.number_input("Eta esame (anni)",
                                   value=int(d.get("eta_vis") or eta_calc or 0),
                                   min_value=0, max_value=120, step=1, key=s("eta"))
    with c3:
        data_vis = st.date_input("Data visita",
                                  value=datetime.date.today(), key=s("data"))
    with c4:
        professionista = st.text_input("Professionista",
                                        value=d.get("professionista") or _prof(),
                                        key=s("prof"))

    c5, c6, c7 = st.columns(3)
    with c5:
        referente = _txt("Referente / Chi invia", s("referente"),
                         d.get("referente",""))
    with c6:
        sesso = _radio("Sesso", ["M","F","Altro"], s("sesso"), d.get("sesso"))
    with c7:
        preferenza = st.columns(3)
        with preferenza[0]:
            occhio = _txt("Occhio pref.", s("occhio"), d.get("occhio",""))
        with preferenza[1]:
            mano = _txt("Mano pref.", s("mano"), d.get("mano",""))
        with preferenza[2]:
            piede = _txt("Piede pref.", s("piede"), d.get("piede",""))

    note_int = _txt("Note", s("note"), d.get("note",""))

    return {"intestazione": {
        "eta_vis": eta_vis, "data_vis": str(data_vis),
        "professionista": professionista, "referente": referente,
        "sesso": sesso, "occhio": occhio, "mano": mano, "piede": piede,
        "note": note_int,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE A — STATO REFRATTIVO
# ══════════════════════════════════════════════════════════════════════

def _sez_a(pid, stored):
    st.markdown("### A — Stato Refrattivo")
    s = lambda c: _sk("a", c, pid)
    d = stored.get("sez_a", {})

    # Oftalmometria
    st.markdown("#### Oftalmometria / Cheratometria")
    c1,c2,c3,c4 = st.columns(4)
    with c1: k1_od_mm = _num("K1 OD (mm)", s("k1_od_mm"), d.get("k1_od_mm",7.80))
    with c2: k1_od_D  = _num("K1 OD (D)",  s("k1_od_D"),  d.get("k1_od_D",43.25))
    with c3: k2_od_mm = _num("K2 OD (mm)", s("k2_od_mm"), d.get("k2_od_mm",7.80))
    with c4: k2_od_D  = _num("K2 OD (D)",  s("k2_od_D"),  d.get("k2_od_D",43.25))
    c5,c6,c7,c8 = st.columns(4)
    with c5: k1_os_mm = _num("K1 OS (mm)", s("k1_os_mm"), d.get("k1_os_mm",7.80))
    with c6: k1_os_D  = _num("K1 OS (D)",  s("k1_os_D"),  d.get("k1_os_D",43.25))
    with c7: k2_os_mm = _num("K2 OS (mm)", s("k2_os_mm"), d.get("k2_os_mm",7.80))
    with c8: k2_os_D  = _num("K2 OS (D)",  s("k2_os_D"),  d.get("k2_os_D",43.25))

    # Dark Focus
    st.markdown("#### Dark-Focus Retinoscopia")
    c9,c10 = st.columns(2)
    with c9:  df_od = _num("Dark Focus OD (D)", s("df_od"), d.get("df_od",0))
    with c10: df_os = _num("Dark Focus OS (D)", s("df_os"), d.get("df_os",0))

    # Retinoscopia cicloplegica
    st.markdown("#### Retinoscopia cicloplegica")
    farmaco = _txt("Farmaco utilizzato", s("farmaco"), d.get("farmaco",""))
    def _rx_row(occhio, prefix, stored_rx):
        st.markdown(f"**{occhio}**")
        cc = st.columns(4)
        with cc[0]: sf  = _num("SF",  s(f"rc_sf_{prefix}"),  stored_rx.get("sf",0))
        with cc[1]: cil = _num("CIL", s(f"rc_cil_{prefix}"), stored_rx.get("cil",0))
        with cc[2]: ax  = st.number_input("AX", value=int(stored_rx.get("ax",0)),
                                           min_value=0, max_value=180, step=1,
                                           key=s(f"rc_ax_{prefix}"))
        with cc[3]: ac  = st.text_input("Acuita", value=stored_rx.get("acuita",""),
                                         key=s(f"rc_ac_{prefix}"))
        return {"sf":sf,"cil":cil,"ax":ax,"acuita":ac}

    rc_od = _rx_row("OD", "od", d.get("rc_od",{}))
    rc_os = _rx_row("OS", "os", d.get("rc_os",{}))

    # Autorefrattometro
    st.markdown("#### Autorefrattometro")
    ar_od = _rx_row("OD", "ar_od", d.get("ar_od",{}))
    ar_os = _rx_row("OS", "ar_os", d.get("ar_os",{}))

    # Refrazione soggettiva
    st.markdown("#### Refrazione soggettiva")
    rs_od = _rx_row("OD", "rs_od", d.get("rs_od",{}))
    rs_os = _rx_row("OS", "rs_os", d.get("rs_os",{}))

    c11,c12,c13 = st.columns(3)
    with c11: add_v = _num("ADD vicino", s("add_v"), d.get("add_v",0))
    with c12: add_i = _num("ADD intermedia", s("add_i"), d.get("add_i",0))
    with c13: dp    = _num("DP (mm)", s("dp"), d.get("dp",63), step=0.5, fmt="%.1f")

    # Acuita visiva
    st.markdown("#### Acuita visiva")
    av_cols = ["Nat OD","Nat OS","Nat OO","Corr OD","Corr OS","Corr OO"]
    av_vals = {}
    cc = st.columns(6)
    for i,k in enumerate(av_cols):
        key_k = k.lower().replace(" ","_")
        with cc[i]:
            av_vals[key_k] = st.text_input(k, value=d.get("av",{}).get(key_k,""),
                                             key=s(f"av_{key_k}"))

    note = _txt("Note sezione A", s("note"), d.get("note",""), h=68)

    return {"sez_a": {
        "k1_od_mm":k1_od_mm,"k1_od_D":k1_od_D,"k2_od_mm":k2_od_mm,"k2_od_D":k2_od_D,
        "k1_os_mm":k1_os_mm,"k1_os_D":k1_os_D,"k2_os_mm":k2_os_mm,"k2_os_D":k2_os_D,
        "df_od":df_od,"df_os":df_os,"farmaco":farmaco,
        "rc_od":rc_od,"rc_os":rc_os,"ar_od":ar_od,"ar_os":ar_os,
        "rs_od":rs_od,"rs_os":rs_os,"add_v":add_v,"add_i":add_i,"dp":dp,
        "av":av_vals,"note":note,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE B — EQUILIBRIO BINOCULARE (Skeffington/OEP)
# ══════════════════════════════════════════════════════════════════════

def _sez_b(pid, stored):
    st.markdown("### B — Equilibrio Binoculare")
    st.caption("Notazione Skeffington / OEP")
    s = lambda c: _sk("b", c, pid)
    d = stored.get("sez_b", {})

    # Cover Test
    st.markdown("#### Cover Test")
    c1,c2 = st.columns(2)
    with c1:
        ct_l = _radio("Cover Test lontano",
            ["Ortoforia","Esoforia","Esotropia","Exoforia","Exotropia","Iperforia"],
            s("ct_l"), d.get("ct_l","Ortoforia"))
        ct_l_pr = _num("Prismi CT lontano (dp)", s("ct_l_pr"), d.get("ct_l_pr",0), step=0.5)
    with c2:
        ct_v = _radio("Cover Test vicino",
            ["Ortoforia","Esoforia","Esotropia","Exoforia","Exotropia","Iperforia"],
            s("ct_v"), d.get("ct_v","Ortoforia"))
        ct_v_pr = _num("Prismi CT vicino (dp)", s("ct_v_pr"), d.get("ct_v_pr",0), step=0.5)

    # Maddox
    st.markdown("#### Maddox — Foria")
    c3,c4 = st.columns(2)
    with c3:
        madd_or_l = _num("#3 Foria Orizzontale lontano (dp)",
                          s("madd_or_l"), d.get("madd_or_l",0), step=0.5)
        madd_or_v = _num("#13A Foria Orizzontale vicino (dp)",
                          s("madd_or_v"), d.get("madd_or_v",0), step=0.5)
    with c4:
        madd_ver_l = _num("Foria Verticale lontano (dp)",
                           s("madd_ver_l"), d.get("madd_ver_l",0), step=0.5)
        madd_ver_v = _num("Foria Verticale vicino (dp)",
                           s("madd_ver_v"), d.get("madd_ver_v",0), step=0.5)

    # Disparita di fissazione
    st.markdown("#### Disparita di Fissazione")
    c5,c6 = st.columns(2)
    with c5:
        disp_l = _num("Disparita lontano (dp)", s("disp_l"), d.get("disp_l",0), step=0.5)
    with c6:
        disp_v = _num("Disparita vicino (dp)", s("disp_v"), d.get("disp_v",0), step=0.5)

    testa_incl = st.checkbox("Testa inclinata/ruotata",
                              value=d.get("testa_incl",False), key=s("testa_incl"))

    # Vergenze (notazione OEP)
    st.markdown("#### Vergenze")
    st.caption("Valori: rottura / recupero (dp)")

    def _vergenza_row(label, key_base):
        cc = st.columns(4)
        with cc[0]: st.markdown(f"**{label}**")
        with cc[1]:
            rot = _num("Rottura", s(f"{key_base}_rot"),
                        d.get(key_base,{}).get("rot",0), step=0.5)
        with cc[2]:
            rec = _num("Recupero", s(f"{key_base}_rec"),
                        d.get(key_base,{}).get("rec",0), step=0.5)
        with cc[3]:
            ab = st.text_input("Abituale", value=d.get(key_base,{}).get("ab",""),
                                key=s(f"{key_base}_ab"))
        return {"rot":rot,"rec":rec,"ab":ab}

    st.markdown("**Smooth Vergenze lontano**")
    v8_bo  = _vergenza_row("#8 BO lontano",  "v8_bo")
    v8_bi  = _vergenza_row("BI lontano",     "v8_bi")
    st.markdown("**Smooth Vergenze vicino**")
    v11_bo = _vergenza_row("#11 BO vicino",  "v11_bo")
    v11_bi = _vergenza_row("#12 BI vicino",  "v11_bi")
    st.markdown("**Step Vergenze**")
    v_step_bo_l = _vergenza_row("Step BO lontano", "vstep_bo_l")
    v_step_bi_l = _vergenza_row("Step BI lontano", "vstep_bi_l")
    v_step_bo_v = _vergenza_row("Step BO vicino",  "vstep_bo_v")
    v_step_bi_v = _vergenza_row("Step BI vicino",  "vstep_bi_v")
    st.markdown("**Jump Vergenze**")
    c7,c8 = st.columns(2)
    with c7:
        jv_16 = _num("#16 Jump 16BO/4BI (c/min)", s("jv_16"),
                      d.get("jv_16",0), step=1, fmt="%.0f")
    with c8:
        jv_8  = _num("#17 Jump 8BO/8BI (c/min)",  s("jv_8"),
                      d.get("jv_8",0), step=1, fmt="%.0f")

    # PPC
    st.markdown("#### PPC — Punto Prossimo di Convergenza")
    c9,c10,c11,c12 = st.columns(4)
    with c9:  ppc_acc_rot = _num("Acc. Rottura (cm)", s("ppc_acc_rot"), d.get("ppc_acc_rot",0), step=0.5, fmt="%.1f")
    with c10: ppc_acc_rec = _num("Acc. Recupero (cm)",s("ppc_acc_rec"), d.get("ppc_acc_rec",0), step=0.5, fmt="%.1f")
    with c11: ppc_an_rot  = _num("Anagl. Rottura (cm)",s("ppc_an_rot"), d.get("ppc_an_rot",0), step=0.5, fmt="%.1f")
    with c12: ppc_an_rec  = _num("Anagl. Recupero (cm)",s("ppc_an_rec"),d.get("ppc_an_rec",0), step=0.5, fmt="%.1f")

    ppc_migliora = st.checkbox("Migliora con +?", value=d.get("ppc_migliora",False),
                                key=s("ppc_migliora"))

    # AC/A
    st.markdown("#### AC/A Ratio")
    c13,c14 = st.columns(2)
    with c13:
        aca = _num("AC/A (dp/D)", s("aca"), d.get("aca",4.0), step=0.5, fmt="%.1f")
    with c14:
        aca_tipo = _radio("Tipo", ["Calcolato","Gradiente","Fisso"],
                          s("aca_tipo"), d.get("aca_tipo","Calcolato"))
    dp_int = _num("Distanza interpupillare (mm)", s("dp_int"),
                   d.get("dp_int",63), step=0.5, fmt="%.1f")

    # Condizione sensoriale
    st.markdown("#### Condizione Sensoriale")
    c15,c16 = st.columns(2)
    with c15:
        worth_l = _radio("Worth lontano",
            ["Fusione","Soppressione OD","Soppressione OS","Diplopia","Scotopico"],
            s("worth_l"), d.get("worth_l","Fusione"))
        worth_v = _radio("Worth vicino",
            ["Fusione","Soppressione OD","Soppressione OS","Diplopia","Scotopico"],
            s("worth_v"), d.get("worth_v","Fusione"))
    with c16:
        randot = st.number_input("#7 Randot (sec d arco)",
                                  value=int(d.get("randot",0)),
                                  min_value=0, max_value=3000, step=10, key=s("randot"))
        titmus = st.number_input("Titmus Nat (sec d arco)",
                                  value=int(d.get("titmus",0)),
                                  min_value=0, max_value=3000, step=10, key=s("titmus"))
        randot_p = _num("Randot (P)", s("randot_p"), d.get("randot_p",0), step=10, fmt="%.0f")

    note = _txt("Note sezione B", s("note"), d.get("note",""), h=68)

    return {"sez_b": {
        "ct_l":ct_l,"ct_l_pr":ct_l_pr,"ct_v":ct_v,"ct_v_pr":ct_v_pr,
        "madd_or_l":madd_or_l,"madd_or_v":madd_or_v,
        "madd_ver_l":madd_ver_l,"madd_ver_v":madd_ver_v,
        "disp_l":disp_l,"disp_v":disp_v,"testa_incl":testa_incl,
        "v8_bo":v8_bo,"v8_bi":v8_bi,
        "v11_bo":v11_bo,"v11_bi":v11_bi,
        "vstep_bo_l":v_step_bo_l,"vstep_bi_l":v_step_bi_l,
        "vstep_bo_v":v_step_bo_v,"vstep_bi_v":v_step_bi_v,
        "jv_16":jv_16,"jv_8":jv_8,
        "ppc_acc_rot":ppc_acc_rot,"ppc_acc_rec":ppc_acc_rec,
        "ppc_an_rot":ppc_an_rot,"ppc_an_rec":ppc_an_rec,
        "ppc_migliora":ppc_migliora,"aca":aca,"aca_tipo":aca_tipo,
        "dp_int":dp_int,"worth_l":worth_l,"worth_v":worth_v,
        "randot":randot,"titmus":titmus,"randot_p":randot_p,"note":note,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE C — ACCOMODAZIONE
# ══════════════════════════════════════════════════════════════════════

def _sez_c(pid, stored):
    st.markdown("### C — Accomodazione")
    s = lambda c: _sk("c", c, pid)
    d = stored.get("sez_c", {})

    def _acc_row(label, key, unit="D"):
        cc = st.columns(3)
        with cc[0]: st.markdown(f"**{label}**")
        with cc[1]: od = _num(f"OD ({unit})", s(f"{key}_od"), d.get(f"{key}_od",0))
        with cc[2]: os = _num(f"OS ({unit})", s(f"{key}_os"), d.get(f"{key}_os",0))
        return od, os

    st.markdown("#### Ampiezza accomodativa")
    pu_od,pu_os   = _acc_row("#14 Push-Up", "pu")
    ml_od,ml_os   = _acc_row("Minus Lens", "ml")

    st.markdown("#### Facilita accomodativa")
    c1,c2 = st.columns(2)
    with c1:
        fl_od = _num("Flipper +/-2.00 OD (c/30sec)", s("fl_od"),
                      d.get("fl_od",0), step=1, fmt="%.0f")
        fl_os = _num("Flipper +/-2.00 OS (c/30sec)", s("fl_os"),
                      d.get("fl_os",0), step=1, fmt="%.0f")
    with c2:
        fl_diff_od = st.multiselect("Difficolta OD", ["Con +","Con -","Entrambi"],
                                     default=d.get("fl_diff_od",[]),
                                     key=s("fl_diff_od"))
        fl_diff_os = st.multiselect("Difficolta OS", ["Con +","Con -","Entrambi"],
                                     default=d.get("fl_diff_os",[]),
                                     key=s("fl_diff_os"))

    st.markdown("#### MEM Retinoscopia")
    c3,c4 = st.columns(2)
    with c3:
        mem_od = _num("#14B MEM OD (D)", s("mem_od"), d.get("mem_od",0))
        mem_os = _num("#14B MEM OS (D)", s("mem_os"), d.get("mem_os",0))
    with c4:
        lag_od = _num("Lag accomodativo OD (D)", s("lag_od"), d.get("lag_od",0))
        lag_os = _num("Lag accomodativo OS (D)", s("lag_os"), d.get("lag_os",0))

    st.markdown("#### Test aggiuntivi accomodazione")
    c5,c6 = st.columns(2)
    with c5:
        t20 = _num("#20 (D)", s("t20"), d.get("t20",0))
    with c6:
        t21 = _num("#21 (D)", s("t21"), d.get("t21",0))

    peggiora = st.checkbox("Peggiora ripetendo il test",
                            value=d.get("peggiora",False), key=s("peggiora"))
    note = _txt("Note sezione C", s("note"), d.get("note",""), h=68)

    return {"sez_c": {
        "pu_od":pu_od,"pu_os":pu_os,"ml_od":ml_od,"ml_os":ml_os,
        "fl_od":fl_od,"fl_os":fl_os,"fl_diff_od":fl_diff_od,"fl_diff_os":fl_diff_os,
        "mem_od":mem_od,"mem_os":mem_os,"lag_od":lag_od,"lag_os":lag_os,
        "t20":t20,"t21":t21,"peggiora":peggiora,"note":note,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE D — OCULOMOTRICITA
# ══════════════════════════════════════════════════════════════════════

def _sez_d(pid, stored):
    st.markdown("### D — Oculomotricita")
    s = lambda c: _sk("d", c, pid)
    d = stored.get("sez_d", {})

    st.markdown("#### Pursuits (DEM / NSUCO)")
    c1,c2,c3 = st.columns(3)
    with c1:
        pur_h  = _txt("Horizz.", s("pur_h"), d.get("pur_h",""))
        pur_v  = _txt("Vert.",   s("pur_v"), d.get("pur_v",""))
        pur_ob = _txt("Obliqui", s("pur_ob"),d.get("pur_ob",""))
        pur_ci = _txt("Circ.",   s("pur_ci"),d.get("pur_ci",""))
    with c2:
        rrd = _txt("RRD", s("rrd"), d.get("rrd",""))
        ird = _txt("IRD", s("ird"), d.get("ird",""))
        har = _txt("Harmon", s("har"), d.get("har",""))
    with c3:
        pur_comp = st.checkbox("Compensazione testa",
                                value=d.get("pur_comp",False), key=s("pur_comp"))
        pur_note = _txt("Note pursuits", s("pur_note"), d.get("pur_note",""))

    st.markdown("#### NSUCO Saccadi")
    st.caption("Punteggio NSUCO: 1 (gravemente deficitario) → 5 (eccellente)")
    nsuco_opts = [1,2,3,4,5]
    c4,c5 = st.columns(2)
    with c4:
        st.markdown("**Saccadi orizzontali**")
        ns_or_ab   = st.select_slider("Abilita H", nsuco_opts,
                                       value=int(d.get("ns_or_ab",3)),
                                       key=s("ns_or_ab"))
        ns_or_ac   = st.select_slider("Accuratezza H", nsuco_opts,
                                       value=int(d.get("ns_or_ac",3)),
                                       key=s("ns_or_ac"))
    with c5:
        st.markdown("**Saccadi verticali**")
        ns_ver_ab  = st.select_slider("Abilita V", nsuco_opts,
                                       value=int(d.get("ns_ver_ab",3)),
                                       key=s("ns_ver_ab"))
        ns_ver_ac  = st.select_slider("Accuratezza V", nsuco_opts,
                                       value=int(d.get("ns_ver_ac",3)),
                                       key=s("ns_ver_ac"))

    st.markdown("#### Visual Tracking Test")
    c6,c7,c8 = st.columns(3)
    with c6: vtt_tempo  = _num("Tempo (sec)", s("vtt_t"), d.get("vtt_t",0), step=1, fmt="%.0f")
    with c7: vtt_errori = st.number_input("Errori", value=int(d.get("vtt_e",0)),
                                           min_value=0, step=1, key=s("vtt_e"))
    with c8: vtt_score  = _txt("Score/Livello", s("vtt_s"), d.get("vtt_s",""))

    st.markdown("#### Test linee intrecciate (Tracking)")
    c9,c10 = st.columns(2)
    with c9:  lin_tempo  = _num("Tempo (sec)", s("lin_t"), d.get("lin_t",0), step=1, fmt="%.0f")
    with c10: lin_errori = st.number_input("Errori", value=int(d.get("lin_e",0)),
                                            min_value=0, step=1, key=s("lin_e"))

    st.markdown("#### Fissazione monoculare")
    c11,c12 = st.columns(2)
    with c11: fiss_od = _radio("Fissazione OD",
                                ["Centrale stabile","Centrale instabile","Eccentrica"],
                                s("fiss_od"), d.get("fiss_od","Centrale stabile"))
    with c12: fiss_os = _radio("Fissazione OS",
                                ["Centrale stabile","Centrale instabile","Eccentrica"],
                                s("fiss_os"), d.get("fiss_os","Centrale stabile"))

    note = _txt("Note sezione D", s("note"), d.get("note",""), h=68)

    return {"sez_d": {
        "pur_h":pur_h,"pur_v":pur_v,"pur_ob":pur_ob,"pur_ci":pur_ci,
        "rrd":rrd,"ird":ird,"har":har,"pur_comp":pur_comp,"pur_note":pur_note,
        "ns_or_ab":ns_or_ab,"ns_or_ac":ns_or_ac,
        "ns_ver_ab":ns_ver_ab,"ns_ver_ac":ns_ver_ac,
        "vtt_t":vtt_tempo,"vtt_e":vtt_errori,"vtt_s":vtt_score,
        "lin_t":lin_tempo,"lin_e":lin_errori,
        "fiss_od":fiss_od,"fiss_os":fiss_os,"note":note,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE E — ESAME OBIETTIVO
# ══════════════════════════════════════════════════════════════════════

def _sez_e(pid, stored):
    st.markdown("### E — Esame Obiettivo")
    s = lambda c: _sk("e", c, pid)
    d = stored.get("sez_e", {})

    st.markdown("#### Segmento anteriore")
    c1,c2 = st.columns(2)
    with c1:
        cor_od  = _radio("Cornea OD",  ["Nella norma","Anomalia"], s("cor_od"),  d.get("cor_od","Nella norma"))
        cam_od  = _radio("Camera ant. OD",["Nella norma","Anomalia"],s("cam_od"), d.get("cam_od","Nella norma"))
        cri_od  = _radio("Cristallino OD",["Nella norma","Anomalia"],s("cri_od"), d.get("cri_od","Nella norma"))
    with c2:
        cor_os  = _radio("Cornea OS",  ["Nella norma","Anomalia"], s("cor_os"),  d.get("cor_os","Nella norma"))
        cam_os  = _radio("Camera ant. OS",["Nella norma","Anomalia"],s("cam_os"), d.get("cam_os","Nella norma"))
        cri_os  = _radio("Cristallino OS",["Nella norma","Anomalia"],s("cri_os"), d.get("cri_os","Nella norma"))

    cong = _radio("Congiuntiva/Sclera",
                  ["Nella norma","Iperemia","Pterigio","Altro"],
                  s("cong"), d.get("cong","Nella norma"))

    st.markdown("#### IOP + Pachimetria")
    c3,c4,c5,c6 = st.columns(4)
    with c3: iop_od  = _num("IOP OD (mmHg)", s("iop_od"),  d.get("iop_od",0),  step=0.5, fmt="%.1f")
    with c4: iop_os  = _num("IOP OS (mmHg)", s("iop_os"),  d.get("iop_os",0),  step=0.5, fmt="%.1f")
    with c5: pach_od = _num("Pachy OD (um)", s("pach_od"), d.get("pach_od",0), step=1,   fmt="%.0f")
    with c6: pach_os = _num("Pachy OS (um)", s("pach_os"), d.get("pach_os",0), step=1,   fmt="%.0f")

    iop_alta = (iop_od>21) or (iop_os>21)
    pach_bassa = (0<pach_od<500) or (0<pach_os<500)
    if iop_alta or pach_bassa:
        st.error("ATTENZIONE: " +
                 ("IOP elevata. " if iop_alta else "") +
                 ("Pachimetria ridotta. " if pach_bassa else "") +
                 "Inviare a visita oculistica approfondita.")

    st.markdown("#### Segmento posteriore")
    c7,c8 = st.columns(2)
    with c7:
        fon_od = _radio("Fondo OD",  ["Nella norma","Anomalia","Non valutato"], s("fon_od"), d.get("fon_od","Nella norma"))
        vit_od = _radio("Vitreo OD", ["Nella norma","Anomalia","Non valutato"], s("vit_od"), d.get("vit_od","Nella norma"))
    with c8:
        fon_os = _radio("Fondo OS",  ["Nella norma","Anomalia","Non valutato"], s("fon_os"), d.get("fon_os","Nella norma"))
        vit_os = _radio("Vitreo OS", ["Nella norma","Anomalia","Non valutato"], s("vit_os"), d.get("vit_os","Nella norma"))

    st.markdown("#### Topografia corneale")
    topo = _txt("Note topografia", s("topo"), d.get("topo",""))

    note = _txt("Note sezione E", s("note"), d.get("note",""), h=68)

    anomalie = sum(1 for x in [cor_od,cor_os,cam_od,cam_os,cri_od,cri_os,fon_od,fon_os]
                   if x=="Anomalia")

    return {"sez_e": {
        "cor_od":cor_od,"cor_os":cor_os,"cam_od":cam_od,"cam_os":cam_os,
        "cri_od":cri_od,"cri_os":cri_os,"cong":cong,
        "iop_od":iop_od,"iop_os":iop_os,"pach_od":pach_od,"pach_os":pach_os,
        "fon_od":fon_od,"fon_os":fon_os,"vit_od":vit_od,"vit_os":vit_os,
        "topo":topo,"note":note,"anomalie_n":anomalie,"iop_alta":iop_alta,
    }}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE F — PROFILO FUNZIONALE
# ══════════════════════════════════════════════════════════════════════

def _sez_f(pid, d):
    st.markdown("### F — Profilo Funzionale")
    st.caption("Valori derivati dalle sezioni A-E. Modificabili manualmente.")
    s = lambda c: _sk("f", c, pid)
    fd = d.get("sez_f", {})

    ITEMS = [
        ("Acuita visiva lontano",    "av_l"),
        ("Acuita visiva vicino",     "av_v"),
        ("Convergenza / PPC",        "conv"),
        ("Vergenze BO",              "vg_bo"),
        ("Vergenze BI",              "vg_bi"),
        ("Accomodazione",            "acc"),
        ("Facilita accomodativa",    "fac_acc"),
        ("Saccadi",                  "sacc"),
        ("Pursuits",                 "purs"),
        ("Stereopsi",                "stereo"),
        ("Fissazione",               "fiss"),
        ("Percezione visiva",        "perc"),
    ]

    tutti = []
    for label, k in ITEMS:
        col1,col2,col3 = st.columns([3,5,1])
        val = st.session_state.get(s(k), int(fd.get(k,3)))
        with col1: st.caption(label)
        with col2:
            v = st.select_slider(label, [1,2,3,4,5],
                                  value=val, key=s(k),
                                  label_visibility="collapsed")
        with col3:
            c = "#22c55e" if v>=4 else ("#f59e0b" if v>=2 else "#ef4444")
            bc = "#dcfce7" if v>=4 else ("#fef3c7" if v>=2 else "#fee2e2")
            tc = "#166534" if v>=4 else ("#92400e" if v>=2 else "#991b1b")
            st.markdown(
                f'<span style="background:{bc};color:{tc};padding:2px 6px;'
                f'border-radius:8px;font-size:11px;font-weight:500">{v}/5</span>',
                unsafe_allow_html=True)
        tutti.append((v, c))

    # Grafico barre
    st.markdown("---")
    for (v,c),(label,_) in zip(tutti, ITEMS):
        pct = int(v/5*100)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">' +
            f'<span style="width:180px;font-size:12px;text-align:right;color:var(--color-text-secondary)">{label}</span>' +
            f'<div style="flex:1;background:var(--color-background-secondary);border-radius:6px;height:12px">' +
            f'<div style="width:{pct}%;height:100%;background:{c};border-radius:6px"></div></div>' +
            f'<span style="width:28px;font-size:11px;font-weight:500;color:{c}">{v}/5</span></div>',
            unsafe_allow_html=True)

    media = sum(v for v,_ in tutti) / len(tutti)
    cg = "#22c55e" if media>=4 else ("#f59e0b" if media>=2 else "#ef4444")
    bt = "Nella norma" if media>=4 else ("Borderline" if media>=2 else "Deficitario")
    st.markdown("---")
    st.markdown(
        f'**Indice funzionale globale:** ' +
        f'<span style="font-size:1.2rem;font-weight:600;color:{cg}">{media:.1f}/5</span> ' +
        f'<span style="background:{cg}22;color:{cg};padding:3px 10px;border-radius:10px;font-size:13px">{bt}</span>',
        unsafe_allow_html=True)

    vals = {k: st.session_state.get(s(k),3) for _,k in ITEMS}
    return {"sez_f": vals}


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE G — PRESCRIZIONE E RELAZIONE
# ══════════════════════════════════════════════════════════════════════

def _sez_g(conn, pid, d, paziente):
    st.markdown("### G — Prescrizione e Relazione")
    s = lambda c: _sk("g", c, pid)
    gd = d.get("sez_g", {})

    cog = paziente.get("Cognome","") if isinstance(paziente,dict) else ""
    nom = paziente.get("Nome","")    if isinstance(paziente,dict) else ""
    dn  = paziente.get("Data_Nascita","") if isinstance(paziente,dict) else ""
    prof = d.get("intestazione",{}).get("professionista") or _prof()

    diagnosi = _txt("Diagnosi visiva e optometrica", s("diag"),
                    gd.get("diag",""), h=100)
    piano    = _txt("Piano terapeutico / raccomandazioni", s("piano"),
                    gd.get("piano",""), h=100)

    st.markdown("---")
    rx = d.get("sez_a",{})
    ob = d.get("sez_e",{})

    c1,c2,c3 = st.columns(3)
    with c1:
        if st.button("Genera Ricetta PDF", key=s("btn_rx"), type="primary"):
            _pdf_ricetta(pid, cog, nom, dn, rx, prof)
    with c2:
        if ob.get("anomalie_n",0)>0 or ob.get("iop_alta"):
            if st.button("Lettera invio oculista", key=s("btn_inv")):
                _pdf_lettera(pid, cog, nom, dn, ob, prof)
    with c3:
        if st.button("Relazione clinica PDF", key=s("btn_rel")):
            _pdf_relazione(pid, cog, nom, dn, d, prof, diagnosi, piano)

    return {"sez_g": {"diag": diagnosi, "piano": piano}}


def _pdf_ricetta(pid, cog, nom, dn, rx, prof):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=56,leftMargin=56,topMargin=56,bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t",fontSize=18,fontName="Helvetica-Bold",
                             textColor=VERDE,alignment=TA_CENTER,spaceAfter=4)
        sS = ParagraphStyle("s",fontSize=9,fontName="Helvetica",
                             textColor=colors.gray,alignment=TA_CENTER,spaceAfter=2)
        sH = ParagraphStyle("h",fontSize=12,fontName="Helvetica-Bold",
                             textColor=VERDE,spaceAfter=4,spaceBefore=10)
        sB = ParagraphStyle("b",fontSize=10,fontName="Helvetica",spaceAfter=4,leading=14)

        def _f(v): return f"+{v:.2f}" if float(v or 0)>=0 else f"{float(v or 0):.2f}"
        sod = rx.get("rs_od",{}); sos = rx.get("rs_os",{})

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Paragraph(f"Professionista: {prof}", sS),
            Spacer(1,15),
            HRFlowable(width="100%",thickness=1.5,color=VERDE),
            Spacer(1,10),
            Paragraph("PRESCRIZIONE OTTICA", sH),
            Paragraph(
                f"Paziente: <b>{cog} {nom}</b> | Nato/a: {dn} | "
                f"Data: {datetime.date.today().strftime('%d/%m/%Y')}", sB),
            Spacer(1,12),
        ]
        tbl = Table([
            ["","SF","CIL","AX","Acuita"],
            ["OD",_f(sod.get("sf")),_f(sod.get("cil")),
             str(sod.get("ax",0))+"g",sod.get("acuita","—")],
            ["OS",_f(sos.get("sf")),_f(sos.get("cil")),
             str(sos.get("ax",0))+"g",sos.get("acuita","—")],
        ], colWidths=[50,70,70,60,80])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),VERDE),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("FONTSIZE",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#D3D1C7")),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F1EFE8")]),
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ]))
        story.append(tbl)
        if rx.get("add_v"):
            story.append(Spacer(1,6))
            story.append(Paragraph(f"ADD vicino: +{float(rx['add_v']):.2f} D", sB))
        if rx.get("add_i"):
            story.append(Paragraph(f"ADD intermedia: +{float(rx['add_i']):.2f} D", sB))
        if rx.get("dp"):
            story.append(Paragraph(f"Distanza pupillare: {float(rx['dp']):.1f} mm", sB))
        story.append(Spacer(1,30))
        story.append(HRFlowable(width="100%",thickness=0.5,color=colors.gray))
        story.append(Spacer(1,8))
        story.append(Paragraph(f"Firma: _______________________  {prof}", sB))
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Ricetta PDF", data=buf,
            file_name=f"ricetta_{cog}_{nom}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_rx_{pid}")
    except Exception as e:
        st.error(f"Errore ricetta: {e}")


def _pdf_lettera(pid, cog, nom, dn, ob, prof):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=56,leftMargin=56,topMargin=56,bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t",fontSize=18,fontName="Helvetica-Bold",textColor=VERDE,alignment=TA_CENTER)
        sS = ParagraphStyle("s",fontSize=9,fontName="Helvetica",textColor=colors.gray,alignment=TA_CENTER)
        sB = ParagraphStyle("b",fontSize=10,fontName="Helvetica",spaceAfter=6,leading=16)

        anom = []
        for campo, lbl in [("cor_od","Cornea OD"),("cor_os","Cornea OS"),
                             ("fon_od","Fondo OD"),("fon_os","Fondo OS"),
                             ("cri_od","Cristallino OD"),("cri_os","Cristallino OS")]:
            if ob.get(campo)=="Anomalia": anom.append(lbl)
        if ob.get("iop_alta"): anom.append(f"IOP elevata (OD:{ob.get('iop_od')} / OS:{ob.get('iop_os')} mmHg)")
        pach_od = float(ob.get("pach_od") or 0)
        pach_os = float(ob.get("pach_os") or 0)
        if 0 < pach_od < 500 or 0 < pach_os < 500:
            anom.append(f"Pachimetria ridotta (OD:{pach_od:.0f} / OS:{pach_os:.0f} um)")

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Spacer(1,15),
            HRFlowable(width="100%",thickness=1,color=VERDE),Spacer(1,12),
            Paragraph("LETTERA DI INVIO A VISITA OCULISTICA", sB),Spacer(1,8),
            Paragraph(
                f"Egregio Collega,<br/><br/>"
                f"Le invio in visita il/la paziente <b>{cog} {nom}</b> (nato/a il {dn}), "
                f"giunto/a presso il nostro studio per valutazione visuo-percettiva.<br/><br/>"
                f"Nel corso dell esame obiettivo abbiamo riscontrato:", sB),
        ]
        for a in anom:
            story.append(Paragraph(f"- {a}", sB))
        story += [
            Spacer(1,8),
            Paragraph(
                f"Si richiede visita oculistica approfondita.<br/><br/>"
                f"Cordiali saluti.<br/><br/>"
                f"{datetime.date.today().strftime('%d/%m/%Y')}<br/><br/>"
                f"<b>{prof}</b><br/>The Organism Studio", sB),
        ]
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Lettera PDF", data=buf,
            file_name=f"invio_oculista_{cog}_{nom}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_ltr_{pid}")
    except Exception as e:
        st.error(f"Errore lettera: {e}")


def _pdf_relazione(pid, cog, nom, dn, d, prof, diagnosi, piano):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=56,leftMargin=56,topMargin=56,bottomMargin=56)
        VERDE = colors.HexColor("#1D6B44")
        sT = ParagraphStyle("t",fontSize=18,fontName="Helvetica-Bold",textColor=VERDE,alignment=TA_CENTER)
        sS = ParagraphStyle("s",fontSize=9,fontName="Helvetica",textColor=colors.gray,alignment=TA_CENTER)
        sH = ParagraphStyle("h",fontSize=12,fontName="Helvetica-Bold",textColor=VERDE,spaceAfter=4,spaceBefore=10)
        sB = ParagraphStyle("b",fontSize=10,fontName="Helvetica",spaceAfter=4,leading=15)

        rx = d.get("sez_a",{}); b = d.get("sez_b",{})
        ob = d.get("sez_e",{}); c = d.get("sez_c",{})

        def _f(v): return f"+{float(v or 0):.2f}" if float(v or 0)>=0 else f"{float(v or 0):.2f}"
        sod = rx.get("rs_od",{}); sos = rx.get("rs_os",{})

        story = [
            Paragraph("The Organism", sT),
            Paragraph("Studio di Optometria Comportamentale e Neuropsicologia", sS),
            Paragraph(f"Professionista: {prof}", sS),
            Spacer(1,15),
            HRFlowable(width="100%",thickness=1.5,color=VERDE),Spacer(1,8),
            Paragraph("RELAZIONE CLINICA VISUO-PERCETTIVA", sH),
            Paragraph(
                f"Paziente: <b>{cog} {nom}</b> | Nato/a: {dn} | "
                f"Data visita: {d.get('intestazione',{}).get('data_vis', datetime.date.today().strftime('%Y-%m-%d'))}", sB),
            Spacer(1,10),
            Paragraph("Refrazione soggettiva", sH),
            Paragraph(
                f"OD: {_f(sod.get('sf'))} / {_f(sod.get('cil'))} x {sod.get('ax',0)}g — Visus {sod.get('acuita','nd')}<br/>"
                f"OS: {_f(sos.get('sf'))} / {_f(sos.get('cil'))} x {sos.get('ax',0)}g — Visus {sos.get('acuita','nd')}", sB),
            Paragraph("Equilibrio binoculare", sH),
            Paragraph(
                f"Cover test lontano: {b.get('ct_l','nd')} | Cover test vicino: {b.get('ct_v','nd')}<br/>"
                f"PPC accomodativo: {b.get('ppc_acc_rot','nd')} / {b.get('ppc_acc_rec','nd')} cm | "
                f"AC/A: {b.get('aca','nd')}", sB),
            Paragraph("Accomodazione", sH),
            Paragraph(
                f"Push-Up OD: {c.get('pu_od','nd')} D | OS: {c.get('pu_os','nd')} D<br/>"
                f"MEM OD: {c.get('mem_od','nd')} D | OS: {c.get('mem_os','nd')} D", sB),
            Paragraph("Esame obiettivo", sH),
            Paragraph(
                f"IOP OD: {ob.get('iop_od','nd')} / OS: {ob.get('iop_os','nd')} mmHg | "
                f"Pachimetria OD: {ob.get('pach_od','nd')} / OS: {ob.get('pach_os','nd')} um", sB),
        ]
        if diagnosi:
            story += [Paragraph("Diagnosi", sH), Paragraph(diagnosi, sB)]
        if piano:
            story += [Paragraph("Piano terapeutico", sH), Paragraph(piano, sB)]
        story += [
            Spacer(1,30),
            HRFlowable(width="100%",thickness=0.5,color=colors.gray),Spacer(1,8),
            Paragraph(f"Firma: _______________________  {prof}<br/>The Organism Studio", sB),
        ]
        doc.build(story)
        buf.seek(0)
        st.download_button("Scarica Relazione PDF", data=buf,
            file_name=f"relazione_{cog}_{nom}_{datetime.date.today()}.pdf",
            mime="application/pdf", key=f"dl_rel_{pid}")
    except Exception as e:
        st.error(f"Errore relazione: {e}")


# ══════════════════════════════════════════════════════════════════════
#  SEZIONE H — SPORTS VISION (placeholder)
# ══════════════════════════════════════════════════════════════════════

def _sez_h(pid, stored):
    st.markdown("### H — Sports Vision")
    st.info(
        "Sezione in costruzione. I test per la visione sportiva "
        "verranno aggiunti nella prossima versione: "
        "tempo di reazione visiva, Dynamic Visual Acuity, "
        "Visual Tracking sportivo, Contrast Sensitivity."
    )
    s = lambda c: _sk("h", c, pid)
    note = _txt("Note anticipatorie", s("note"),
                stored.get("sez_h",{}).get("note",""), h=80)
    return {"sez_h": {"note": note}}


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def render_valutazione_visuo_percettiva(conn, paz_id, paziente=None):
    st.subheader("Valutazione Visuo-Percettiva")
    st.caption("Notazione Skeffington/OEP | The Organism")

    if paziente is None:
        paziente = {}

    stored = _carica(conn, paz_id)
    dati   = dict(stored)

    tabs = st.tabs([
        "Intestazione",
        "A. Stato refrattivo",
        "B. Equilibrio binoculare",
        "C. Accomodazione",
        "D. Oculomotricita",
        "E. Esame obiettivo",
        "F. Profilo funzionale",
        "G. Prescrizione",
        "H. Sports Vision",
    ])

    with tabs[0]:
        dati.update(_intestazione(paz_id, paziente, stored))
        if st.button("Salva intestazione", key=f"sv_int_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[1]:
        dati.update(_sez_a(paz_id, stored))
        if st.button("Salva sezione A", key=f"sv_a_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[2]:
        dati.update(_sez_b(paz_id, stored))
        if st.button("Salva sezione B", key=f"sv_b_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[3]:
        dati.update(_sez_c(paz_id, stored))
        if st.button("Salva sezione C", key=f"sv_c_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[4]:
        dati.update(_sez_d(paz_id, stored))
        if st.button("Salva sezione D", key=f"sv_d_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[5]:
        dati.update(_sez_e(paz_id, stored))
        if st.button("Salva sezione E", key=f"sv_e_{paz_id}"):
            _salva(conn, paz_id, dati)

    with tabs[6]:
        dati.update(_sez_f(paz_id, dati))

    with tabs[7]:
        extra = _sez_g(conn, paz_id, dati, paziente)
        dati.update(extra)
        if st.button("Salva diagnosi e piano", key=f"sv_g_{paz_id}", type="primary"):
            _salva(conn, paz_id, dati)

    with tabs[8]:
        dati.update(_sez_h(paz_id, stored))
        if st.button("Salva note Sports Vision", key=f"sv_h_{paz_id}"):
            _salva(conn, paz_id, dati)
