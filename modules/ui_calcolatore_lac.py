# -*- coding: utf-8 -*-
"""
Modulo: Calcolatore LAC Inversa
Gestionale The Organism – PNEV

Implementa l'algoritmo del software "Inversa 6" di G. Toffoli:
- Calcolo Rb da r0, eccentricità e miopia da ridurre
- Calcolo flange con clearance progressiva
- Profilo sagittale cornea vs lente (grafico)
- Import topografo CSV/TXT
- Salvataggio parametri calcolati in scheda paziente
"""

import math
import json
try:
    from modules.ui_raggio_potere import r_to_d, d_to_r
except ImportError:
    def r_to_d(r): return round(337.5/r, 2) if r and r>0 else 0.0
    def d_to_r(d): return round(337.5/d, 3) if d and d>0 else 0.0
import io
import streamlit as st
import pandas as pd
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Helpers DB (stesso pattern degli altri moduli)
# ---------------------------------------------------------------------------

def _is_postgres(conn) -> bool:
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception:
        pass
    return False

def _ph(n, conn):
    mark = "%s" if _is_postgres(conn) else "?"
    return ", ".join([mark] * n)

def _get_conn():
    try:
        from modules.app_core import get_connection
        return get_connection()
    except Exception:
        pass
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import get_connection
        return get_connection()
    except Exception:
        pass
    import sqlite3
    conn = sqlite3.connect("organism.db")
    conn.row_factory = sqlite3.Row
    return conn

def _row_get(row, key, default=None):
    try:
        v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except Exception: return default

def _today_str():
    return date.today().strftime("%d/%m/%Y")

def _parse_date(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try: return datetime.strptime((s or "").strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return ""


# ---------------------------------------------------------------------------
# MOTORE DI CALCOLO – Algoritmo Inversa 6
# ---------------------------------------------------------------------------

def calcola_lac_inversa(
    r0: float,          # raggio apicale cornea (mm)
    e: float,           # eccentricità cornea
    miopia_D: float,    # miopia da ridurre (D, valore negativo)
    zona_ottica: str,   # "Sferica" o "Asferica"
    fattore_appiatt: float = 0.5,
    clear_inv: float = 0.054,   # clearance punto inversione (mm)
    c0: float = 0.005,          # curva base
    ampiezze: tuple = (0.8, 0.5, 0.7, 0.2, 0.4),  # flange I-V
    diametro_tot: float = 10.8,
) -> dict:
    """
    Calcola tutti i parametri della LAC inversa.
    Implementa le formule di Inversa 6 v1.3 (G. Toffoli).
    """
    CK = 337.5  # costante cheratometrica

    # ── Fattore p (forma cornea) ────────────────────────────────────────
    p = 1 - e**2  # fattore forma dalla eccentricità

    # ── Equivalente sferico e K flat ────────────────────────────────────
    k_flat_D  = 1 / r0 * CK
    k_flat_mm = r0

    # ── Raggio base Rb ──────────────────────────────────────────────────
    # Rb = r0 / (1 - fattore_appiatt * e^2) — semplificazione Inversa 6
    # Dal foglio: Rb = 1 / (1/r0*CK - |clear0| - |clear1|) * CK
    # Utilizziamo la formula diretta: Rb porta la clearance al punto inv.
    # Formula da Inversa 6: Rb calcolato in modo che la sagitta a y=ZO/2
    # sia uguale alla sagitta corneale + clearance_inv
    y_zo = 2.8  # semizona ottica default (diam ZO = 5.6 mm)

    # Sagitta corneale alla semizona ottica
    if zona_ottica == "Sferica":
        sag_cornea_zo = r0 - math.sqrt(max(r0**2 - y_zo**2, 0))
    else:
        # cornea asferica: formula conica
        sag_cornea_zo = (r0/p) - math.sqrt(max((r0/p)**2 - y_zo**2/p, 0))

    # Sagitta lente inversa (zona ottica piatta) deve = sag_cornea + clearance
    sag_lente_zo = sag_cornea_zo + clear_inv

    # Rb dalla sagitta inversa: Rb - sqrt(Rb^2 - y^2) = sag_lente
    # → Rb = (y^2 + sag_lente^2) / (2 * sag_lente)
    Rb = (y_zo**2 + sag_lente_zo**2) / (2 * sag_lente_zo)

    # ── Zona ottica diametro ─────────────────────────────────────────────
    # Empiricamente la ZO dipende dalla miopia da correggere
    if abs(miopia_D) <= 1.0:
        zo_diam = 6.0
    elif abs(miopia_D) <= 2.0:
        zo_diam = 5.8
    elif abs(miopia_D) <= 3.0:
        zo_diam = 5.6
    elif abs(miopia_D) <= 5.0:
        zo_diam = 5.4
    else:
        zo_diam = 5.2
    y_zo = zo_diam / 2

    # Ricalcola Rb con la ZO corretta
    if zona_ottica == "Sferica":
        sag_cornea_zo = r0 - math.sqrt(max(r0**2 - y_zo**2, 0))
    else:
        sag_cornea_zo = (r0/p) - math.sqrt(max((r0/p)**2 - y_zo**2/p, 0))
    sag_lente_zo = sag_cornea_zo + clear_inv
    Rb = (y_zo**2 + sag_lente_zo**2) / (2 * sag_lente_zo)

    # ── Punto di inversione (c1) ─────────────────────────────────────────
    # c1 = clearance al punto di inversione (input, default 0.054 mm)
    c1 = clear_inv

    # ── Calcolo raggi flange r1…r5 ───────────────────────────────────────
    # Altezze (y) dei bordi delle flange
    y_vals = [y_zo]
    amp_list = list(ampiezze)
    for amp in amp_list:
        y_vals.append(y_vals[-1] + amp)

    # Sagitta lente per ogni flangia (clearance progressivamente ridotta)
    clearances = [c1, c1*0.185, 0.0, 0.0, 0.0, 0.0]  # da Inversa 6

    # Per ogni flangia: il raggio della flangia è la sfera tangente
    # che tocca il profilo corneale con la clearance richiesta
    raggi_flange = []
    for i in range(len(amp_list)):
        y_in  = y_vals[i]
        y_out = y_vals[i+1]
        cl_in = clearances[i] if i < len(clearances) else 0.0

        # Sagitta corneale ai due bordi
        if zona_ottica == "Sferica":
            sag_in  = r0 - math.sqrt(max(r0**2 - y_in**2,  0))
            sag_out = r0 - math.sqrt(max(r0**2 - y_out**2, 0))
        else:
            sag_in  = (r0/p) - math.sqrt(max((r0/p)**2 - y_in**2/p,  0))
            sag_out = (r0/p) - math.sqrt(max((r0/p)**2 - y_out**2/p, 0))

        # Centro della flangia (sfera tangente)
        # Dal foglio: r_fl = sqrt((F45-J45)^2 + (G45-K45)^2)
        # approssimazione: raggio tangente tra i due punti
        dy = y_out - y_in
        dz = sag_out - sag_in - cl_in
        if dy > 0:
            r_fl = (dy**2 + dz**2) / (2 * abs(dz)) if abs(dz) > 1e-6 else Rb * (1.05 + i * 0.12)
        else:
            r_fl = Rb * (1.05 + i * 0.12)

        # Limita a valori fisicamente ragionevoli
        r_fl = max(min(r_fl, 14.0), Rb * 0.75)
        raggi_flange.append(round(r_fl, 3))

    # ── Diottrie flange ──────────────────────────────────────────────────
    diottrie_flange = [round(1/r * CK, 3) if r > 0 else 0 for r in raggi_flange]

    # ── Diametri cumulativi ──────────────────────────────────────────────
    diametri = []
    d_cum = zo_diam
    for amp in amp_list:
        d_cum += amp * 2
        diametri.append(round(d_cum, 1))

    # ── Curva base c0 (diottrie) ─────────────────────────────────────────
    c0_D = 1 / r0 * CK  # uguale a K flat

    # ── Potere lente ─────────────────────────────────────────────────────
    potere = round(abs(miopia_D) * 0.1, 2)  # compensazione residua

    # ── Fattore P ZO asferica ────────────────────────────────────────────
    p_ZO = 1 / (1 - e**2) if e != 1 else 999

    # ── Eccentricità equivalente zona ottica ─────────────────────────────
    ecc_ZO = e

    return {
        "r0_mm": round(r0, 3),
        "e": round(e, 3),
        "p": round(p, 4),
        "p_ZO": round(p_ZO, 4),
        "ecc_ZO": round(ecc_ZO, 4),
        "k_flat_mm": round(k_flat_mm, 3),
        "k_flat_D": round(k_flat_D, 3),
        "Rb_mm": round(Rb, 3),
        "Rb_D": round(1/Rb * CK, 3),
        "zo_diam_mm": round(zo_diam, 1),
        "zo_raggio_mm": round(y_zo, 2),
        "clear_inv_mm": round(c1, 3),
        "c0": round(c0, 3),
        "c0_D": round(c0_D, 3),
        "c1": round(c1, 3),
        "potere_D": potere,
        "zona_ottica": zona_ottica,
        "miopia_D": miopia_D,
        "flange": [
            {
                "nome": f"{'I II III IV V'.split()[i]} Flangia",
                "raggio_mm": raggi_flange[i],
                "diottrie": diottrie_flange[i],
                "ampiezza_mm": amp_list[i],
                "diametro_mm": diametri[i],
            }
            for i in range(len(amp_list))
        ],
        "diametro_tot_mm": diametri[-1] if diametri else diametro_tot,
    }


def profilo_cornea(r0, e, y_max, n=80):
    """Profilo sagittale corneale (ellisse conica)."""
    p = 1 - e**2
    ys, zs = [], []
    for i in range(n+1):
        y = y_max * i / n
        try:
            z = (r0/p) - math.sqrt(max((r0/p)**2 - y**2/p, 0))
        except Exception:
            z = 0
        ys.append(y); zs.append(z)
    return ys, zs


def profilo_lente(Rb, zo_r, flange, y_max, n=80):
    """Profilo sagittale lente inversa."""
    # Costruisce tratti per zona: ZO (Rb) + flange
    sezioni = [(zo_r, Rb)]
    y_cum = zo_r
    for fl in flange:
        y_cum += fl["ampiezza_mm"]
        sezioni.append((y_cum, fl["raggio_mm"]))

    ys, zs = [], []
    sag_acc = 0.0
    prev_y = 0.0
    prev_z = 0.0

    for i in range(n+1):
        y = y_max * i / n
        # Trova la sezione corrente
        r_cur = Rb
        y_start = 0.0
        z_start = 0.0
        for k, (y_bord, r_sec) in enumerate(sezioni):
            if y <= y_bord:
                r_cur = r_sec
                if k > 0:
                    y_start = sezioni[k-1][0]
                    # z_start calcolato al bordo precedente
                break
        else:
            r_cur = sezioni[-1][1]
            y_start = sezioni[-2][0]

        dy = y - y_start
        try:
            z = z_start + (r_cur - math.sqrt(max(r_cur**2 - dy**2, 0)))
        except Exception:
            z = z_start

        ys.append(y); zs.append(z)

    return ys, zs


# ---------------------------------------------------------------------------
# Import topografo
# ---------------------------------------------------------------------------

def parse_topografo_csv(file_content: str) -> dict:
    """
    Tenta di estrarre r0, e, K flat, K steep da file topografo.
    Supporta formati comuni: Topcon, Zeiss, Medmont, Sirius, CSV generico.
    """
    result = {"r0": None, "e": None, "k_flat_mm": None, "k_flat_D": None,
              "k_steep_mm": None, "k_steep_D": None, "asse_steep": None,
              "raw_lines": []}

    lines = file_content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    result["raw_lines"] = lines[:50]  # prime 50 righe per debug

    import re

    for line in lines:
        line_l = line.lower().strip()

        # Raggio apicale / Flat K
        if any(k in line_l for k in ["k flat", "k1", "flat k", "r0", "raggio apicale", "apical radius"]):
            nums = re.findall(r"[-+]?\d+\.?\d*", line)
            floats = [float(x) for x in nums if 0.1 < float(x) < 100]
            for v in floats:
                if 6.0 <= v <= 9.5 and result["r0"] is None:
                    result["r0"] = v; result["k_flat_mm"] = v
                    result["k_flat_D"] = round(337.5 / v, 2)
                elif 30.0 <= v <= 55.0 and result["k_flat_D"] is None:
                    result["k_flat_D"] = v; result["k_flat_mm"] = round(337.5 / v, 3)
                    if result["r0"] is None: result["r0"] = result["k_flat_mm"]

        # K steep
        if any(k in line_l for k in ["k steep", "k2", "steep k", "k max"]):
            nums = re.findall(r"[-+]?\d+\.?\d*", line)
            floats = [float(x) for x in nums if 0.1 < float(x) < 100]
            for v in floats:
                if 6.0 <= v <= 9.5 and result["k_steep_mm"] is None:
                    result["k_steep_mm"] = v; result["k_steep_D"] = round(337.5 / v, 2)
                elif 30.0 <= v <= 55.0 and result["k_steep_D"] is None:
                    result["k_steep_D"] = v; result["k_steep_mm"] = round(337.5 / v, 3)

        # Eccentricità
        if any(k in line_l for k in ["eccentr", "ecc", "e ="]):
            nums = re.findall(r"[-+]?\d+\.?\d*", line)
            for v_str in nums:
                v = float(v_str)
                if 0.0 <= v <= 1.5 and result["e"] is None:
                    result["e"] = v; break

        # Asse steep
        if any(k in line_l for k in ["axis", "asse", "ax"]):
            nums = re.findall(r"\d+", line)
            for v_str in nums:
                v = int(v_str)
                if 0 <= v <= 180 and result["asse_steep"] is None:
                    result["asse_steep"] = v; break

    return result


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_calcolatore_lac():
    st.header("Calcolatore LAC Inversa")
    st.caption("Algoritmo basato su Inversa 6 v1.3 – G. Toffoli")

    conn = _get_conn()
    cur  = conn.cursor()

    # Seleziona paziente (opzionale – per salvataggio)
    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception:
            pazienti = []

    paz_options = ["— nessuno (calcolo standalone) —"] + [
        f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip()
        for p in pazienti]
    sel_paz = st.selectbox("Paziente (opzionale, per salvare)", paz_options, key="calc_paz")
    paz_id  = None if sel_paz.startswith("—") else int(sel_paz.split(" - ")[0])

    st.divider()

    tab_manuale, tab_import, tab_analisi = st.tabs([
        "Calcolo manuale", "Import topografo", "Analisi costruttiva"])

    with tab_manuale:
        _ui_calcolo_manuale(conn, cur, paz_id)
    with tab_import:
        _ui_import_topografo(conn, cur, paz_id)
    with tab_analisi:
        _ui_analisi_costruttiva(conn, cur, paz_id)


# ---------------------------------------------------------------------------
# Tab: Calcolo manuale
# ---------------------------------------------------------------------------

def _ui_calcolo_manuale(conn, cur, paz_id):
    CK = 337.5
    st.subheader("Parametri di ingresso")

    col_sx, col_dx = st.columns([1, 1])

    with col_sx:
        st.markdown("#### Dati corneali")
        occhio       = st.selectbox("Occhio", ["OD","OS"], key="calc_occhio")
        # Inizializza valori
        for _k,_v in [("calc_r0",7.60),("calc_r0_D",round(CK/7.60,2)),
                      ("calc_kfl",7.60),("calc_kfl_D",round(CK/7.60,2)),
                      ("calc_kst",7.50),("calc_kst_D",round(CK/7.50,2))]:
            if _k not in st.session_state: st.session_state[_k] = _v

        def _r0_mm(): v=st.session_state.get("calc_r0",0); st.session_state["calc_r0_D"]=round(CK/v,2) if v>0 else 0
        def _r0_D():  v=st.session_state.get("calc_r0_D",0); st.session_state["calc_r0"]=round(CK/v,3) if v>0 else 0
        def _kfl_mm(): v=st.session_state.get("calc_kfl",0); st.session_state["calc_kfl_D"]=round(CK/v,2) if v>0 else 0
        def _kfl_D2(): v=st.session_state.get("calc_kfl_D",0); st.session_state["calc_kfl"]=round(CK/v,3) if v>0 else 0
        def _kst_mm(): v=st.session_state.get("calc_kst",0); st.session_state["calc_kst_D"]=round(CK/v,2) if v>0 else 0
        def _kst_D2(): v=st.session_state.get("calc_kst_D",0); st.session_state["calc_kst"]=round(CK/v,3) if v>0 else 0

        _rc1,_rc2 = st.columns(2)
        with _rc1: r0 = st.number_input("Raggio apicale r₀ (mm)", 6.0, 9.5, step=0.01, format="%.3f", key="calc_r0", on_change=_r0_mm)
        with _rc2: st.number_input("r₀ (D)", 35.0, 56.0, step=0.25, format="%.2f", key="calc_r0_D", on_change=_r0_D)
        e = st.number_input("Eccentricità e", 0.0, 1.5, 0.50, 0.01, key="calc_e")
        _kc1,_kc2 = st.columns(2)
        with _kc1: k_flat_mm = st.number_input("K flat (mm)", 6.0, 9.5, step=0.01, format="%.2f", key="calc_kfl", on_change=_kfl_mm)
        with _kc2: k_flat_D  = st.number_input("K flat (D)",  35.0, 52.0, step=0.25, format="%.2f", key="calc_kfl_D", on_change=_kfl_D2)
        _ks1,_ks2 = st.columns(2)
        with _ks1: k_steep_mm = st.number_input("K steep (mm)", 6.0, 9.5, step=0.01, format="%.2f", key="calc_kst", on_change=_kst_mm)
        with _ks2: k_steep_D  = st.number_input("K steep (D)",  35.0, 52.0, step=0.25, format="%.2f", key="calc_kst_D", on_change=_kst_D2)
        if abs(k_flat_D - k_steep_D) > 0.1:
            st.caption(f"Astigmatismo: {abs(k_flat_D-k_steep_D):.2f} D")

        st.markdown("#### Dati refrattivi")
        miopia_D     = st.number_input("Miopia da ridurre (D)", -20.0, 0.0, -5.25, 0.25, key="calc_mio")

    with col_dx:
        st.markdown("#### Parametri costruttivi")
        zona_ottica  = st.selectbox("Tipo Zona Ottica", ["Sferica","Asferica"], key="calc_zo_tipo")
        fatt_appiatt = st.number_input("Fattore appiattimento", 0.0, 2.0, 0.50, 0.01, key="calc_fatt")
        clear_inv    = st.number_input("Clearance punto inversione (mm)", 0.01, 0.15, 0.054, 0.001, format="%.3f", key="calc_clear")
        c0_val       = st.number_input("Curva base c₀ (mm)", 0.001, 0.020, 0.005, 0.001, format="%.3f", key="calc_c0")

        st.markdown("#### Ampiezze flange (mm)")
        amp_cols = st.columns(5)
        amp_labels = ["I","II","III","IV","V"]
        amp_defaults = [0.8, 0.5, 0.7, 0.2, 0.4]
        ampiezze = []
        for i, (col, lab, dfl) in enumerate(zip(amp_cols, amp_labels, amp_defaults)):
            with col:
                v = st.number_input(f"{lab}", 0.1, 3.0, dfl, 0.1, key=f"calc_amp_{i}")
                ampiezze.append(v)

        diametro_tot = st.number_input("Diametro totale (mm)", 8.0, 14.0, 10.8, 0.1, key="calc_dtot")

    st.divider()
    calcola = st.button("Calcola parametri LAC", type="primary", key="btn_calcola")

    if calcola:
        with st.spinner("Calcolo in corso..."):
            res = calcola_lac_inversa(
                r0=r0, e=e, miopia_D=miopia_D,
                zona_ottica=zona_ottica,
                fattore_appiatt=fatt_appiatt,
                clear_inv=clear_inv,
                c0=c0_val,
                ampiezze=tuple(ampiezze),
                diametro_tot=diametro_tot,
            )
        st.session_state["_calc_data"] = {
            "res": res, "occhio": occhio,
            "r0": r0, "e": e,
            "kfl": k_flat_mm, "kfl_D": k_flat_D,
            "kst": k_steep_mm, "kst_D": k_steep_D,
        }

    if "_calc_data" in st.session_state:
        d = st.session_state["_calc_data"]
        _mostra_risultati(conn, cur, paz_id, d["res"])


def _mostra_risultati(conn, cur, paz_id, res):
    st.success("Calcolo completato")
    st.markdown("## Risultati")

    # ── Riepilogo parametri principali ──────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Raggio base Rb", f"{res['Rb_mm']:.3f} mm")
    c2.metric("Rb (D)",         f"{res['Rb_D']:.2f} D")
    c3.metric("Zona Ottica",    f"{res['zo_diam_mm']:.1f} mm")
    c4.metric("Clearance inv.", f"{res['clear_inv_mm']:.3f} mm")

    c5,c6,c7,c8 = st.columns(4)
    c5.metric("Fattore p",      f"{res['p']:.4f}")
    c6.metric("p ZO",           f"{res['p_ZO']:.4f}")
    c7.metric("Potere lente",   f"{res['potere_D']:+.2f} D")
    c8.metric("Diam. totale",   f"{res['diametro_tot_mm']:.1f} mm")

    # ── Tabella flange ───────────────────────────────────────────────────
    st.markdown("### Flange")
    fl_data = []
    for fl in res["flange"]:
        fl_data.append({
            "Flangia":      fl["nome"],
            "Raggio (mm)":  fl["raggio_mm"],
            "Diottrie":     fl["diottrie"],
            "Ampiezza (mm)":fl["ampiezza_mm"],
            "Ø (mm)":       fl["diametro_mm"],
        })
    st.dataframe(pd.DataFrame(fl_data), use_container_width=True, hide_index=True)

    # ── Grafico profilo sagittale ─────────────────────────────────────────
    st.markdown("### Profilo sagittale – Cornea vs Lente")
    _grafico_profilo(res)

    # ── Schema testuale parametri per laboratorio ─────────────────────────
    st.markdown("### Schema per il laboratorio")
    schema = _genera_schema(res)
    st.code(schema, language=None)

    # ── Salva in scheda paziente ─────────────────────────────────────────
    if paz_id:
        st.divider()
        st.markdown("#### Salva parametri calcolati nel gestionale")
        occhio_sal = st.session_state.get("_calc_data", {}).get("occhio", "OD")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            mat = st.text_input("Materiale lente", "Boston XO", key="calc_sal_mat")
            dk  = st.number_input("DK", 0.0, 200.0, 100.0, 1.0, key="calc_sal_dk")
        with col_s2:
            note_sal = st.text_area("Note", "", key="calc_sal_note")

        if st.button("Salva in scheda Lenti Inverse", key="btn_salva_calc"):
            _salva_in_lenti_inverse(conn, cur, paz_id, occhio_sal, res, mat, dk, note_sal,
                                    st.session_state.get("_calc_data", {}).get("kfl", res["r0_mm"]),
                                    st.session_state.get("_calc_data", {}).get("kfl_D", res["k_flat_D"]),
                                    st.session_state.get("_calc_data", {}).get("kst", res["r0_mm"]),
                                    st.session_state.get("_calc_data", {}).get("kst_D", res["k_flat_D"]))


def _grafico_profilo(res):
    """Grafico ASCII + metriche del profilo sagittale."""
    r0   = res["r0_mm"]
    e    = res["e"]
    Rb   = res["Rb_mm"]
    zo_r = res["zo_diam_mm"] / 2
    y_max = res["diametro_tot_mm"] / 2

    ys_c, zs_c = profilo_cornea(r0, e, y_max)
    ys_l, zs_l = profilo_lente(Rb, zo_r, res["flange"], y_max)

    # Clearance punto per punto
    clearances = []
    for y, zc, zl in zip(ys_c, zs_c, zs_l):
        clearances.append(round((zl - zc) * 1000, 1))  # in µm

    df_plot = pd.DataFrame({
        "y (mm)":       ys_c,
        "Cornea (mm)":  zs_c,
        "Lente (mm)":   zs_l,
        "Clearance µm": clearances,
    })

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**Profilo sagittale (mm)**")
        st.line_chart(df_plot.set_index("y (mm)")[["Cornea (mm)","Lente (mm)"]])
    with col_g2:
        st.markdown("**Clearance lente-cornea (µm)**")
        st.line_chart(df_plot.set_index("y (mm)")[["Clearance µm"]])

    # Valori chiave clearance
    idx_zo  = min(range(len(ys_c)), key=lambda i: abs(ys_c[i] - zo_r))
    idx_inv = min(range(len(clearances)), key=lambda i: clearances[i])
    idx_brd = -1

    cc1,cc2,cc3 = st.columns(3)
    cc1.metric("Clearance centrale (µm)", f"{clearances[0]:.0f}")
    cc2.metric(f"Clearance ZO bordo (y={zo_r:.1f}mm) µm", f"{clearances[idx_zo]:.0f}")
    cc3.metric("Clearance al bordo (µm)", f"{clearances[idx_brd]:.0f}")


def _genera_schema(res) -> str:
    lines = [
        "═══════════════════════════════════════════════",
        f"  LAC INVERSA – Parametri costruttivi",
        f"  Tipo ZO: {res['zona_ottica']}   Miopia: {res['miopia_D']:.2f} D",
        "═══════════════════════════════════════════════",
        f"  r₀ (raggio apicale cornea):  {res['r0_mm']:.3f} mm",
        f"  e  (eccentricità):           {res['e']:.3f}",
        f"  p  (fattore forma):          {res['p']:.4f}",
        "───────────────────────────────────────────────",
        f"  Rb (raggio base):            {res['Rb_mm']:.3f} mm  ({res['Rb_D']:.2f} D)",
        f"  Zona Ottica (Ø):             {res['zo_diam_mm']:.1f} mm",
        f"  Clearance inversione:        {res['clear_inv_mm']:.3f} mm",
        f"  Potere lente:                {res['potere_D']:+.2f} D",
        "───────────────────────────────────────────────",
        "  FLANGE:",
    ]
    for fl in res["flange"]:
        lines.append(
            f"  {fl['nome']:12s}  r={fl['raggio_mm']:.3f} mm "
            f"({fl['diottrie']:.2f} D)  amp={fl['ampiezza_mm']:.1f} mm  Ø={fl['diametro_mm']:.1f} mm"
        )
    lines += [
        "───────────────────────────────────────────────",
        f"  Diametro totale:             {res['diametro_tot_mm']:.1f} mm",
        "═══════════════════════════════════════════════",
    ]
    return "\n".join(lines)


def _salva_in_lenti_inverse(conn, cur, paz_id, occhio, res, materiale, dk, note,
                             k_flat_mm, k_flat_D, k_steep_mm, k_steep_D):
    """Salva i parametri calcolati nella tabella lenti_inverse."""
    try:
        from modules.ui_lenti_inverse import init_lenti_inverse_db
        init_lenti_inverse_db(conn)
    except Exception:
        pass

    now_iso = datetime.now().isoformat(timespec="seconds")
    flange_json = json.dumps(res["flange"], ensure_ascii=False)

    params = (
        paz_id, occhio, date.today().isoformat(),
        k_flat_mm, k_flat_D, k_steep_mm, k_steep_D,
        res["e"], res["r0_mm"], 0.0, 0.0,
        "", "", "[]",
        0.0, 0.0, 0, res["miopia_D"], res["miopia_D"], "", "",
        res["zona_ottica"], res["r0_mm"], res["Rb_mm"],
        res["ecc_ZO"], res["p"], 0.5,
        res["zo_diam_mm"], res["clear_inv_mm"],
        res["c0"], res["c1"],
        0.0, 0.0, 0.0, 0.0, 0.0,
        flange_json, res["diametro_tot_mm"], res["potere_D"],
        materiale, dk, 0, note,
        "", "", 0.0, 0.0, "", "", 0.0, "", "", "", "", "",
        now_iso, now_iso,
    )
    ph = _ph(len(params), conn)
    sql = (
        "INSERT INTO lenti_inverse ("
        "paziente_id,occhio,data_scheda,"
        "topo_k_flat_mm,topo_k_flat_d,topo_k_steep_mm,topo_k_steep_d,"
        "topo_ecc_media,topo_raggio_apicale_mm,topo_dev_std_raggio,topo_dev_std_ecc,"
        "topo_topografo,topo_data,topo_misurazioni_json,"
        "rx_sfera,rx_cilindro,rx_asse,rx_miopia_tot,rx_miopia_ridurre,rx_avsc,rx_avcc,"
        "lente_tipo_zo,lente_r0_mm,lente_rb_mm,lente_ecc_zo,lente_fattore_p,"
        "lente_fattore_appiatt,lente_zo_diam_mm,lente_clearance_mm,"
        "lente_c0,lente_c1,lente_c2,lente_c3,lente_c4,lente_c5,lente_c6,"
        "lente_flange_json,lente_diam_tot_mm,lente_potere_d,"
        "lente_materiale,lente_dk,lente_puntino,lente_note,"
        "app_data,app_tipo,app_clearance_centrale,app_clearance_periferica,"
        "app_pattern,app_centratura,app_movimento_mm,app_valutazione,"
        "app_modifiche,app_operatore,app_note_fluoresceina,app_note,"
        "created_at,updated_at"
        f") VALUES ({ph})"
    )
    try:
        cur.execute(sql, params)
        conn.commit()
        st.success("Parametri salvati nella sezione Lenti Inverse.")
    except Exception as ex:
        st.error(f"Errore salvataggio: {ex}")


# ---------------------------------------------------------------------------
# Tab: Import topografo
# ---------------------------------------------------------------------------

def _ui_import_topografo(conn, cur, paz_id):
    st.subheader("Import dati topografo")
    st.info("Carica un file CSV o TXT esportato dal tuo topografo. "
            "Formati supportati: Topcon, Zeiss, Medmont, Sirius, CSV generico.")

    uploaded = st.file_uploader(
        "File topografo (CSV/TXT)", type=["csv","txt","dat","asc"],
        key="topo_upload")

    if uploaded:
        content = uploaded.read().decode("utf-8", errors="replace")
        parsed  = parse_topografo_csv(content)

        st.markdown("#### Dati estratti automaticamente")
        col_a, col_b = st.columns(2)
        with col_a:
            r0_imp    = st.number_input("Raggio apicale r₀ (mm)", 6.0, 9.5,
                                         float(parsed["r0"] or 7.60), 0.01, format="%.3f", key="imp_r0")
            e_imp     = st.number_input("Eccentricità e", 0.0, 1.5,
                                         float(parsed["e"] or 0.50), 0.01, key="imp_e")
            kfl_imp   = st.number_input("K flat (mm)", 6.0, 9.5,
                                         float(parsed["k_flat_mm"] or 7.60), 0.01, key="imp_kfl")
            kfl_D_imp = st.number_input("K flat (D)", 35.0, 52.0,
                                         float(parsed["k_flat_D"] or 44.41), 0.25, key="imp_kfl_D")
        with col_b:
            kst_imp   = st.number_input("K steep (mm)", 6.0, 9.5,
                                         float(parsed["k_steep_mm"] or 7.50), 0.01, key="imp_kst")
            kst_D_imp = st.number_input("K steep (D)", 35.0, 52.0,
                                         float(parsed["k_steep_D"] or 45.00), 0.25, key="imp_kst_D")
            asse_imp  = st.number_input("Asse steep (gradi)", 0, 180,
                                         int(parsed["asse_steep"] or 90), 1, key="imp_asse")

        if not parsed["r0"]:
            st.warning("r₀ non rilevato automaticamente – inseriscilo manualmente sopra.")
        if not parsed["e"]:
            st.warning("Eccentricità non rilevata – inseriscila manualmente sopra.")

        with st.expander("Mostra prime righe file grezzo"):
            st.text("\n".join(parsed["raw_lines"][:30]))

        st.divider()
        st.markdown("#### Procedi al calcolo")
        mio_imp  = st.number_input("Miopia da ridurre (D)", -20.0, 0.0, -3.0, 0.25, key="imp_mio")
        zo_imp   = st.selectbox("Tipo ZO", ["Sferica","Asferica"], key="imp_zo")
        occhio_imp = st.selectbox("Occhio", ["OD","OS"], key="imp_occhio")

        if st.button("Calcola da dati importati", type="primary", key="btn_calc_imp"):
            res = calcola_lac_inversa(
                r0=r0_imp, e=e_imp, miopia_D=mio_imp, zona_ottica=zo_imp)
            st.session_state["_calc_data"] = {
                "res": res, "occhio": occhio_imp,
                "r0": r0_imp, "e": e_imp,
                "kfl": kfl_imp, "kfl_D": kfl_D_imp,
                "kst": kst_imp, "kst_D": kst_D_imp,
            }
            _mostra_risultati(conn, cur, paz_id, res)


# ---------------------------------------------------------------------------
# Tab: Analisi costruttiva
# ---------------------------------------------------------------------------

def _ui_analisi_costruttiva(conn, cur, paz_id):
    st.subheader("Analisi costruttiva multi-parametro")
    st.caption("Confronta più varianti di lente al variare di eccentricità e clearance.")

    c1,c2,c3 = st.columns(3)
    with c1:
        r0_an  = st.number_input("r₀ (mm)", 6.0, 9.5, 7.60, 0.01, format="%.3f", key="an_r0")
        mio_an = st.number_input("Miopia (D)", -20.0, 0.0, -5.0, 0.25, key="an_mio")
    with c2:
        e_min  = st.number_input("Ecc. min", 0.0, 1.0, 0.40, 0.05, key="an_emin")
        e_max  = st.number_input("Ecc. max", 0.0, 1.5, 0.70, 0.05, key="an_emax")
    with c3:
        cl_min = st.number_input("Clear. min (mm)", 0.01, 0.10, 0.04, 0.005, format="%.3f", key="an_clmin")
        cl_max = st.number_input("Clear. max (mm)", 0.01, 0.15, 0.08, 0.005, format="%.3f", key="an_clmax")

    zo_an  = st.selectbox("Tipo ZO", ["Sferica","Asferica"], key="an_zo")

    if st.button("Genera analisi", type="primary", key="btn_analisi"):
        rows = []
        e_vals  = [round(e_min + (e_max-e_min)*i/4, 3) for i in range(5)]
        cl_vals = [round(cl_min + (cl_max-cl_min)*i/3, 4) for i in range(4)]

        for e_v in e_vals:
            for cl_v in cl_vals:
                try:
                    r = calcola_lac_inversa(
                        r0=r0_an, e=e_v, miopia_D=mio_an,
                        zona_ottica=zo_an, clear_inv=cl_v)
                    rows.append({
                        "Ecc (e)":       e_v,
                        "Clear inv (mm)":cl_v,
                        "Rb (mm)":       r["Rb_mm"],
                        "Rb (D)":        r["Rb_D"],
                        "ZO (mm)":       r["zo_diam_mm"],
                        "Diam tot (mm)": r["diametro_tot_mm"],
                        "r1 I fl (mm)":  r["flange"][0]["raggio_mm"] if r["flange"] else "—",
                        "r2 II fl (mm)": r["flange"][1]["raggio_mm"] if len(r["flange"])>1 else "—",
                    })
                except Exception:
                    pass

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Grafico Rb vs eccentricità
            pivot = df.pivot_table(index="Ecc (e)", columns="Clear inv (mm)", values="Rb (mm)")
            st.markdown("**Rb (mm) al variare di eccentricità e clearance**")
            st.line_chart(pivot)

            # Esporta CSV
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(
                "Scarica analisi CSV",
                csv_buf.getvalue().encode("utf-8"),
                file_name="analisi_costruttiva_lac.csv",
                mime="text/csv",
                key="btn_dl_analisi"
            )
