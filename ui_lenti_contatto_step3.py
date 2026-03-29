# -*- coding: utf-8 -*-
"""
Modulo self-contained Lenti a Contatto
- curve costruttive sempre visibili
- ordine produttore
- export TXT / PDF
- import topografo CSO/CSV assistito
- motore clearance-based
- simulazione fluoresceina
- ramo presbiopia inversa dedicato
"""

from __future__ import annotations

import io
import json
import tarfile
from datetime import date, datetime
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

# NEW LAC MODULES (STEP 3 SAFE FALLBACK)
try:
    from modules.lac.lac_engine import (
        esa_lookup,
        toffoli_calc,
        hyperopia_calc,
        astig_calc,
        presbyopia_calc,
        estimate_clearance,
    )
    from modules.lac.lac_decision import build_curves
    from modules.lac.lac_topography import parse_any_topo
    from modules.lac.lac_fluoro import plot_fluorescein_simulation
    from modules.lac.lac_storage import get_conn, init_db, build_payload
    LAC_BRIDGE_OK = True
except Exception:
    LAC_BRIDGE_OK = False


try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

ESA_DATA = {
  "0.50": [
    {"K": 7.27, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.59, "r1": 7.27, "r2": 7.86, "r3": 8.83, "r4": 10.26, "r5": 14.26, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.74, "r1": 7.45, "r2": 8.02, "r3": 8.97, "r4": 10.38, "r5": 14.38, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.89, "r1": 7.62, "r2": 8.17, "r3": 9.11, "r4": 10.5, "r5": 14.5, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.04, "r1": 7.8, "r2": 8.33, "r3": 9.26, "r4": 10.63, "r5": 14.63, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.19, "r1": 7.97, "r2": 8.48, "r3": 9.4, "r4": 10.75, "r5": 14.75, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.34, "r1": 8.14, "r2": 8.63, "r3": 9.54, "r4": 10.87, "r5": 14.87, "PWR": 0.75}
  ],
  "1.00": [
    {"K": 7.27, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.64, "r1": 7.27, "r2": 7.86, "r3": 8.83, "r4": 10.26, "r5": 14.26, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.79, "r1": 7.45, "r2": 8.02, "r3": 8.97, "r4": 10.38, "r5": 14.38, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.94, "r1": 7.62, "r2": 8.17, "r3": 9.11, "r4": 10.5, "r5": 14.5, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.09, "r1": 7.8, "r2": 8.33, "r3": 9.26, "r4": 10.63, "r5": 14.63, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.24, "r1": 7.97, "r2": 8.48, "r3": 9.4, "r4": 10.75, "r5": 14.75, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.39, "r1": 8.14, "r2": 8.63, "r3": 9.54, "r4": 10.87, "r5": 14.87, "PWR": 0.75}
  ],
  "2.00": [
    {"K": 7.27, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 7.74, "r1": 7.27, "r2": 7.92, "r3": 8.92, "r4": 10.34, "r5": 14.34, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 7.89, "r1": 7.45, "r2": 8.08, "r3": 9.06, "r4": 10.46, "r5": 14.46, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.04, "r1": 7.62, "r2": 8.23, "r3": 9.2, "r4": 10.58, "r5": 14.58, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.19, "r1": 7.8, "r2": 8.39, "r3": 9.35, "r4": 10.71, "r5": 14.71, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.34, "r1": 7.97, "r2": 8.54, "r3": 9.49, "r4": 10.83, "r5": 14.83, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.49, "r1": 8.14, "r2": 8.69, "r3": 9.63, "r4": 10.95, "r5": 14.95, "PWR": 0.75}
  ],
  "3.00": [
    {"K": 7.27, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 7.84, "r1": 7.27, "r2": 7.98, "r3": 9.0, "r4": 10.42, "r5": 14.42, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 7.99, "r1": 7.45, "r2": 8.14, "r3": 9.14, "r4": 10.54, "r5": 14.54, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.14, "r1": 7.62, "r2": 8.29, "r3": 9.28, "r4": 10.66, "r5": 14.66, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.29, "r1": 7.8, "r2": 8.45, "r3": 9.43, "r4": 10.79, "r5": 14.79, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.44, "r1": 7.97, "r2": 8.6, "r3": 9.57, "r4": 10.91, "r5": 14.91, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.59, "r1": 8.14, "r2": 8.75, "r3": 9.71, "r4": 11.03, "r5": 15.03, "PWR": 0.75}
  ]
}

# DB helpers
def _is_postgres(conn) -> bool:
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    try:
        mod = type(conn).__module__ or ""
        return "psycopg2" in mod or "psycopg" in mod
    except Exception:
        return False

def _ph(n: int, conn) -> str:
    mark = "%s" if _is_postgres(conn) else "?"
    return ", ".join([mark] * n)

def _get_conn():
    try:
        from modules.app_core import get_connection
        return get_connection()
    except Exception:
        import sqlite3
        conn = sqlite3.connect("organism.db")
        conn.row_factory = sqlite3.Row
        return conn

def _row_get(row, key, default=None):
    try:
        v = row[key]
        return default if v is None else v
    except Exception:
        try:
            return row.get(key, default)
        except Exception:
            return default

def _today_str() -> str:
    return date.today().strftime("%d/%m/%Y")

def _parse_date(s: str) -> str:
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return date.today().isoformat()

_SQL_PG = """
CREATE TABLE IF NOT EXISTS lenti_contatto (
    id BIGSERIAL PRIMARY KEY,
    paziente_id BIGINT NOT NULL,
    data_scheda TEXT, occhio TEXT, categoria TEXT, sottotipo TEXT, difetto TEXT, algoritmo TEXT,
    rx_sfera DOUBLE PRECISION, rx_cilindro DOUBLE PRECISION, rx_asse INTEGER, rx_add DOUBLE PRECISION,
    av_lontano TEXT, av_vicino TEXT,
    k1_mm DOUBLE PRECISION, k2_mm DOUBLE PRECISION, asse_k INTEGER, diametro_hvid DOUBLE PRECISION, pupilla_mm DOUBLE PRECISION,
    topografia_json TEXT,
    lente_rb_mm DOUBLE PRECISION, lente_diam_mm DOUBLE PRECISION, lente_bc_mm DOUBLE PRECISION,
    lente_potere_d DOUBLE PRECISION, lente_cilindro_d DOUBLE PRECISION, lente_asse_cil INTEGER, lente_add_d DOUBLE PRECISION,
    lente_materiale TEXT, lente_ricambio TEXT, lente_note TEXT,
    fitting_json TEXT, followup_json TEXT, stato TEXT, operatore TEXT, created_at TEXT, updated_at TEXT
)
"""
_SQL_SL = _SQL_PG.replace("BIGSERIAL PRIMARY KEY","INTEGER PRIMARY KEY AUTOINCREMENT").replace("BIGINT","INTEGER").replace("DOUBLE PRECISION","REAL")

def init_lenti_contatto_db(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(_SQL_PG if _is_postgres(conn) else _SQL_SL)
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass

def fetch_pazienti_for_select(conn, limit=5000):
    try:
        from modules.app_core import fetch_pazienti_for_select as fp
        return fp(conn, limit=limit)
    except Exception:
        return [], None, None

def _select_paziente(conn):
    rows, _, _ = fetch_pazienti_for_select(conn, limit=5000)
    if not rows:
        st.warning("Nessun paziente disponibile.")
        return None, ""
    options = []
    for r in rows:
        pid, cogn, nome, dn, scuola, eta = r
        options.append((int(pid), f"{cogn} {nome} • {dn or ''} • id {pid}"))
    sel = st.selectbox("Paziente", options=options, format_func=lambda x: x[1], key="lac_sc_paz")
    return sel[0], sel[1]

CATEGORIE = ["Morbida sferica","Torica","Multifocale / Presbiopia","RGP","Ortho-K / Inversa","Custom avanzata"]
DIFFETTI = ["Miopia","Ipermetropia","Astigmatismo","Presbiopia","Miopia + Astigmatismo","Ipermetropia + Astigmatismo","Presbiopia + Astigmatismo","Presbiopia + Miopia","Presbiopia + Ipermetropia"]
ALGORITMI = ["ESA 002","Toffoli","Clinico personalizzato"]
MODELLI = ["Automatico","C6 OBL","C6 TI","C6 AS TI","C6 OBL MF"]
STATI = ["Calcolata","Provata","Ordinata","Consegnata"]

# Topographer
def _infer_grid_side(n: int):
    for c in [101,102,111,121,122]:
        rem = n % c
        if rem <= 40 or (c-rem) <= 40:
            return c
    return None

def _parse_xyz_file(file_obj):
    raw = file_obj.getvalue()
    txt = raw.decode("utf-8", errors="ignore")
    vals = []
    for line in txt.replace(",", ".").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            vals.append(float(s))
        except Exception:
            pass
    arr = np.array(vals, dtype=float) if vals else np.array([], dtype=float)
    side = _infer_grid_side(len(arr))
    return {"kind":"xyz","summary":{"filename":getattr(file_obj,"name","topo.xyz"),"n_values":int(len(arr)),"grid_side_guess":side,"min":float(np.min(arr)) if len(arr) else None,"max":float(np.max(arr)) if len(arr) else None}}

def _parse_csv_topographer(file_obj):
    try:
        df = pd.read_csv(file_obj)
    except Exception:
        file_obj.seek(0)
        df = pd.read_csv(file_obj, sep=";")
    cmap = {str(c).strip().lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n in cmap: return cmap[n]
        return None
    k1_col = pick("k1","simk1","sim k1","flat k")
    k2_col = pick("k2","simk2","sim k2","steep k")
    axis_col = pick("asse","axis","steep axis","simk axis")
    hvid_col = pick("hvid","wtw","white to white")
    pup_col = pick("pupilla","pupil","pupil size")
    values={}
    if len(df)>0:
        row=df.iloc[0]
        values={
            "k1": float(row[k1_col]) if k1_col and pd.notna(row[k1_col]) else None,
            "k2": float(row[k2_col]) if k2_col and pd.notna(row[k2_col]) else None,
            "asse_k": int(float(row[axis_col])) if axis_col and pd.notna(row[axis_col]) else None,
            "hvid": float(row[hvid_col]) if hvid_col and pd.notna(row[hvid_col]) else None,
            "pupilla": float(row[pup_col]) if pup_col and pd.notna(row[pup_col]) else None,
        }
    return {"kind":"csv","summary":{"filename":getattr(file_obj,"name","topo.csv"),"rows":int(len(df))},"values":values,"preview":df.head(8)}

def _parse_zcs_file(file_obj):
    raw=file_obj.getvalue()
    names=[]; xyz_members=[]
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
        for m in tf.getmembers():
            names.append(m.name)
            if m.name.lower().endswith(".xyz"):
                xyz_members.append(m.name)
    return {"kind":"zcs","summary":{"filename":getattr(file_obj,"name","exam.zcs"),"members":len(names),"xyz_members":xyz_members[:10]},"members":names[:30]}

def _parse_any_topo(f):
    if not f: return None
    name=f.name.lower()
    try:
        if name.endswith(".csv"): return _parse_csv_topographer(f)
        if name.endswith(".xyz"): return _parse_xyz_file(f)
        if name.endswith(".zcs"): return _parse_zcs_file(f)
    except Exception as e:
        return {"kind":"error","summary":{"error":str(e)}}
    return None

def _import_topographer_section():
    st.markdown("### Import topografo CSO")
    c1,c2=st.columns(2)
    with c1:
        od_file=st.file_uploader("OD - CSV / XYZ / ZCS", type=["csv","xyz","zcs"], key="topo_od")
    with c2:
        os_file=st.file_uploader("OS - CSV / XYZ / ZCS", type=["csv","xyz","zcs"], key="topo_os")
    if od_file:
        st.session_state["topo_od_parsed"] = parse_any_topo(od_file) if LAC_BRIDGE_OK else _parse_any_topo(od_file)
    if os_file:
        st.session_state["topo_os_parsed"] = parse_any_topo(os_file) if LAC_BRIDGE_OK else _parse_any_topo(os_file)
    for side,key in [("OD","topo_od_parsed"),("OS","topo_os_parsed")]:
        parsed=st.session_state.get(key)
        if parsed:
            st.markdown(f"#### Preview {side}")
            st.json(parsed["summary"])
            if parsed.get("kind")=="csv" and "preview" in parsed:
                st.dataframe(parsed["preview"], use_container_width=True)
    with st.expander("Compilazione assistita da topografo", expanded=False):
        cols=st.columns(5)
        fields=[("k1","K1",7.80,0.01),("k2","K2",7.90,0.01),("ax","Asse",90,1),("hv","HVID",11.8,0.1),("pu","Pupilla",3.5,0.1)]
        for i,(suffix,label,default,step) in enumerate(fields):
            with cols[i]:
                if suffix=="ax":
                    st.number_input(f"OD {label} topografo", min_value=0, max_value=180, value=int(default), key=f"assist_od_{suffix}")
                    st.number_input(f"OS {label} topografo", min_value=0, max_value=180, value=int(default), key=f"assist_os_{suffix}")
                else:
                    st.number_input(f"OD {label} topografo", value=float(default), step=step, format="%.2f", key=f"assist_od_{suffix}")
                    st.number_input(f"OS {label} topografo", value=float(default), step=step, format="%.2f", key=f"assist_os_{suffix}")
        for side,key,prefix in [("OD","topo_od_parsed","assist_od"),("OS","topo_os_parsed","assist_os")]:
            parsed=st.session_state.get(key)
            if parsed and parsed.get("kind")=="csv":
                vals=parsed.get("values",{})
                if vals.get("k1") is not None: st.session_state[f"{prefix}_k1"]=vals["k1"]
                if vals.get("k2") is not None: st.session_state[f"{prefix}_k2"]=vals["k2"]
                if vals.get("asse_k") is not None: st.session_state[f"{prefix}_ax"]=vals["asse_k"]
                if vals.get("hvid") is not None: st.session_state[f"{prefix}_hv"]=vals["hvid"]
                if vals.get("pupilla") is not None: st.session_state[f"{prefix}_pu"]=vals["pupilla"]
        if st.button("Applica valori topografici ai campi clinici", use_container_width=True):
            mapping = {
                "lac_od_topo_k1":"assist_od_k1","lac_od_topo_k2":"assist_od_k2","lac_od_topo_assek":"assist_od_ax","lac_od_topo_hvid":"assist_od_hv","lac_od_topo_pup":"assist_od_pu",
                "lac_os_topo_k1":"assist_os_k1","lac_os_topo_k2":"assist_os_k2","lac_os_topo_assek":"assist_os_ax","lac_os_topo_hvid":"assist_os_hv","lac_os_topo_pup":"assist_os_pu",
            }
            for k,v in mapping.items():
                st.session_state[k]=st.session_state.get(v)
            st.success("Valori topografici applicati a OD/OS.")

# Clearance / curves
# STEP 3:
# il motore LAC e il decision layer sono stati spostati in:
# - modules/lac/lac_engine.py
# - modules/lac/lac_decision.py
# qui lasciamo solo la UI e gli export


# Fallback wrapper locali per non rompere il modulo se modules/lac/ non è disponibile
def _nearest_sheet_key(power_abs: float) -> str:
    vals = sorted(float(k) for k in ESA_DATA.keys())
    target = max(min(round(abs(power_abs) * 4) / 4, max(vals)), min(vals))
    nearest = min(vals, key=lambda x: abs(x - target))
    return f"{nearest:.2f}"

def _interp_row_by_k(rows, k):
    rows = sorted(rows, key=lambda r: r["K"])
    if k <= rows[0]["K"]:
        return dict(rows[0])
    if k >= rows[-1]["K"]:
        return dict(rows[-1])
    for a, b in zip(rows[:-1], rows[1:]):
        if a["K"] <= k <= b["K"]:
            t = 0 if b["K"] == a["K"] else (k - a["K"]) / (b["K"] - a["K"])
            out = {}
            for key in a.keys():
                out[key] = round(a[key] + t * (b[key] - a[key]), 3)
            return out
    return dict(rows[0])

def esa_lookup_self(k_med: float, power_abs: float):
    sk = _nearest_sheet_key(abs(power_abs))
    rows = ESA_DATA.get(sk)
    if not rows:
        return None
    res = _interp_row_by_k(rows, float(k_med))
    res["sheet_power"] = -abs(float(sk))
    return res

def toffoli_calc_self(k_med: float, target_myopia: float):
    target = abs(target_myopia) if target_myopia else 1.0
    r0 = round(k_med + 0.22 + 0.04 * target, 2)
    return {"RB": r0, "ZO": 6.0 if target <= 3 else 5.6, "r1": round(r0 - 0.85, 2), "r2": round(r0 - 0.40, 2), "r3": round(r0 - 0.05, 2), "r4": round(r0 + 1.55, 2), "r5": round(r0 + 1.85, 2), "d1": 7.2, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "PWR": 0.75}

def hyperopia_calc_self(k_med: float, hyper_d: float):
    rb = round(k_med - 0.08 - 0.03 * abs(hyper_d), 2)
    return {"RB": rb, "ZO": 5.0, "r1": round(rb + 0.65, 2), "r2": round(rb + 1.05, 2), "r3": round(rb + 1.40, 2), "r4": round(rb + 2.00, 2), "r5": round(rb + 2.35, 2), "d1": 6.8, "d2": 7.8, "d3": 9.0, "d4": 10.0, "TD": 10.8, "PWR": 0.50}

def astig_calc_self(k_flat: float, k_steep: float, cyl: float):
    rb_flat = round(k_flat + 0.10, 2)
    rb_steep = round(k_steep + 0.10, 2)
    return {"RB_flat": rb_flat, "RB_steep": rb_steep, "ZO": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "PWR": 0.50, "raccomandazione": "Design torico / AS TI consigliato"}

def presbyopia_calc_self(k_med: float, add_d: float):
    rb = round(k_med + 0.05, 2)
    q = round(-0.35 - max(abs(add_d) - 1.0, 0) * 0.10, 2)
    return {"RB": rb, "ZO": 5.6, "Q_target": q, "r1": round(rb - 0.45, 2), "r2": round(rb + 0.05, 2), "r3": round(rb + 0.55, 2), "r4": round(rb + 1.35, 2), "r5": round(rb + 1.95, 2), "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "PWR": 0.50}

def _estimate_clearance(k_med: float, ordine: dict, design: str) -> dict:
    rb = ordine.get("r0", ordine.get("RB", ordine.get("RB_flat", k_med)))
    zo = ordine.get("BOZD", ordine.get("ZO", 5.6))
    td = ordine.get("TD", 10.8)
    sag_delta = (float(rb) - float(k_med)) * 1000.0
    base_central = 110.0 + sag_delta * 0.80
    if design == "hyper":
        base_central += 30.0
    if design == "presb":
        base_central += 20.0
    if design == "toric":
        base_central += 10.0
    central = round(base_central, 1)
    reverse_zone = round(max(40.0, central + 55.0), 1)
    landing = round(max(20.0, central - 35.0), 1)
    edge = round(max(15.0, landing - 5.0), 1)
    if central < 70:
        pattern = "touch centrale"
        valutazione = "lente stretta / appoggio centrale"
    elif central > 180:
        pattern = "pooling centrale marcato"
        valutazione = "clearance eccessiva"
    else:
        pattern = "clearance centrale fisiologica"
        valutazione = "assetto centrale adeguato"
    return {"central_um": central, "reverse_um": reverse_zone, "landing_um": landing, "edge_um": edge, "pattern": pattern, "valutazione": valutazione, "zo": zo, "td": td}

def _build_curves(categoria, difetto, algoritmo, modello_prod, rx_sfera, rx_cil, rx_asse, rx_add, k1, k2, hvid, pupilla, target_orthok, e_val):
    k1 = float(k1); k2 = float(k2); k_med = round((k1 + k2) / 2, 2)
    cyl_sig = abs(rx_cil) >= 0.75
    modello = modello_prod if modello_prod != "Automatico" else ("C6 OBL MF" if abs(rx_add) >= 0.75 else ("C6 AS TI" if cyl_sig else "C6 OBL"))
    if categoria == "Ortho-K / Inversa" and algoritmo == "ESA 002" and rx_sfera < 0:
        esa = esa_lookup_self(k_med, abs(target_orthok) if target_orthok else abs(rx_sfera)); fluor = _estimate_clearance(k_med, esa, "mio")
        return {"modello_prod": modello if modello_prod != "Automatico" else "C6 OBL", "sottotipo": "ESA Ortho-6", "lente_bc_mm": esa["r0"], "lente_rb_mm": esa["r0"], "lente_diam_mm": esa["TD"], "lente_potere_d": esa["PWR"], "lente_cilindro_d": 0.0, "lente_asse_cil": None, "lente_add_d": 0.0, "ordine": esa, "fluor": fluor, "design": "mio"}
    if categoria == "Ortho-K / Inversa" and algoritmo == "Toffoli" and rx_sfera < 0:
        t = toffoli_calc_self(k_med, abs(target_orthok) if target_orthok else abs(rx_sfera)); fluor = _estimate_clearance(k_med, t, "mio")
        return {"modello_prod": modello if modello_prod != "Automatico" else "C6 OBL", "sottotipo": "Toffoli-inspired", "lente_bc_mm": t["RB"], "lente_rb_mm": t["RB"], "lente_diam_mm": t["TD"], "lente_potere_d": t["PWR"], "lente_cilindro_d": 0.0, "lente_asse_cil": None, "lente_add_d": 0.0, "ordine": t, "fluor": fluor, "design": "mio"}
    if rx_sfera > 0 and categoria in ("Custom avanzata", "RGP", "Ortho-K / Inversa"):
        h = hyperopia_calc_self(k_med, rx_sfera); fluor = _estimate_clearance(k_med, h, "hyper")
        return {"modello_prod": modello if modello_prod != "Automatico" else "C6 OBL", "sottotipo": "Ipermetropia inversa", "lente_bc_mm": h["RB"], "lente_rb_mm": h["RB"], "lente_diam_mm": h["TD"], "lente_potere_d": round(rx_sfera, 2), "lente_cilindro_d": 0.0, "lente_asse_cil": None, "lente_add_d": 0.0, "ordine": h, "fluor": fluor, "design": "hyper"}
    if cyl_sig and categoria in ("Torica", "RGP", "Custom avanzata", "Ortho-K / Inversa"):
        a = astig_calc_self(min(k1, k2), max(k1, k2), rx_cil); fluor = _estimate_clearance(k_med, a, "toric"); fluor["valutazione"] = a["raccomandazione"]
        return {"modello_prod": modello if modello_prod != "Automatico" else "C6 AS TI", "sottotipo": "Astigmatismo / torica", "lente_bc_mm": a["RB_flat"], "lente_rb_mm": a["RB_flat"], "lente_diam_mm": a["TD"], "lente_potere_d": round(rx_sfera, 2), "lente_cilindro_d": round(rx_cil, 2), "lente_asse_cil": int(rx_asse), "lente_add_d": 0.0, "ordine": a, "fluor": fluor, "design": "toric"}
    if abs(rx_add) >= 0.75 or categoria == "Multifocale / Presbiopia":
        p = presbyopia_calc_self(k_med, abs(rx_add)); fluor = _estimate_clearance(k_med, p, "presb")
        return {"modello_prod": modello if modello_prod != "Automatico" else "C6 OBL MF", "sottotipo": "Presbiopia / multifocale inversa", "lente_bc_mm": p["RB"], "lente_rb_mm": p["RB"], "lente_diam_mm": p["TD"], "lente_potere_d": round(rx_sfera, 2), "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0, "lente_asse_cil": int(rx_asse) if cyl_sig else None, "lente_add_d": round(rx_add, 2), "ordine": p, "fluor": fluor, "design": "presb"}
    bc = 8.60 if k_med >= 7.80 else 8.40; diam = 14.20 if hvid <= 11.8 else 14.40; ordine = {"BC": bc, "TD": diam}; fluor = _estimate_clearance(k_med, {"RB": bc, "TD": diam, "ZO": 5.6}, "base")
    return {"modello_prod": modello, "sottotipo": "Sferica base", "lente_bc_mm": bc, "lente_rb_mm": None, "lente_diam_mm": diam, "lente_potere_d": round(rx_sfera, 2), "lente_cilindro_d": 0.0, "lente_asse_cil": None, "lente_add_d": 0.0, "ordine": ordine, "fluor": fluor, "design": "base"}

# Fluorescein simulation / export
def _plot_fluorescein_simulation(proposta: dict, title: str = ""):
    fluor = proposta.get("fluor") or {}
    central = fluor.get("central_um", 110)
    reverse_u = fluor.get("reverse_um", 160)
    landing = fluor.get("landing_um", 70)
    edge = fluor.get("edge_um", 50)

    c_center = 0.15 if central < 70 else (0.95 if central > 180 else 0.65)
    c_reverse = 0.95 if reverse_u > 150 else (0.75 if reverse_u > 110 else 0.45)
    c_land = 0.20 if landing < 40 else (0.85 if landing > 100 else 0.55)
    c_edge = 0.90 if edge > 90 else (0.20 if edge < 30 else 0.55)

    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    ax.set_aspect("equal")
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.axis("off")
    ax.set_title(title)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, linewidth=1.2))
    ax.add_patch(Circle((0, 0), 0.95, color=str(1 - c_edge), alpha=0.65))
    ax.add_patch(Circle((0, 0), 0.75, color="white", alpha=1.0))
    ax.add_patch(Circle((0, 0), 0.72, color=str(1 - c_land), alpha=0.65))
    ax.add_patch(Circle((0, 0), 0.52, color="white", alpha=1.0))
    ax.add_patch(Circle((0, 0), 0.50, color=str(1 - c_reverse), alpha=0.75))
    ax.add_patch(Circle((0, 0), 0.26, color="white", alpha=1.0))
    ax.add_patch(Circle((0, 0), 0.24, color=str(1 - c_center), alpha=0.75))
    return fig

def _format_order_text(occhio, proposta):
    o = proposta.get("ordine", {})
    lines=[f"LENTE: {proposta.get('modello_prod','')}", f"OCCHIO: {occhio}", f"SOTTOTIPO: {proposta.get('sottotipo','')}", ""]
    for k in ["RB","RB_flat","RB_steep","BC","ZO","d1","d2","d3","d4","TD","r0","r1","r2","r3","r4","r5","Q_target","PWR","sheet_power"]:
        if k in o:
            lines.append(f"{k}: {o[k]}")
    if proposta.get("lente_cilindro_d"):
        lines.append(f"CIL: {proposta.get('lente_cilindro_d')}")
        lines.append(f"ASSE: {proposta.get('lente_asse_cil')}")
    if proposta.get("lente_add_d"):
        lines.append(f"ADD: {proposta.get('lente_add_d')}")
    fluor = proposta.get("fluor") or {}
    if fluor:
        lines += [
            "",
            "CLEARANCE / FLUORESCEINA",
            f"clearance_centrale_um: {fluor.get('central_um','')}",
            f"clearance_reverse_um: {fluor.get('reverse_um','')}",
            f"clearance_landing_um: {fluor.get('landing_um','')}",
            f"edge_lift_um: {fluor.get('edge_um','')}",
            f"Pattern: {fluor.get('pattern','')}",
            f"Valutazione: {fluor.get('valutazione','')}",
        ]
    return "\n".join(lines)

def _build_txt_export(od_prop, os_prop, paziente_label, data_scheda, operatore):
    parts = [
        "SCHEDA ORDINE LENTI A CONTATTO",
        f"Paziente: {paziente_label}",
        f"Data: {data_scheda}",
        f"Operatore: {operatore or '-'}",
        "",
        _format_order_text("OD", od_prop),
        "",
        "="*48,
        "",
        _format_order_text("OS", os_prop),
    ]
    return "\n".join(parts)

def _build_pdf_export(txt: str) -> bytes:
    if not REPORTLAB_OK:
        return b""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 18 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, "Scheda ordine lenti a contatto")
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    for line in txt.splitlines():
        if y < 18 * mm:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = h - 18 * mm
        c.drawString(15 * mm, y, str(line)[:120])
        y -= 4.5 * mm
    c.save()
    buf.seek(0)
    return buf.getvalue()

# UI pieces
def _ui_eye_form(prefix, label):
    st.markdown(f"### {label}")
    c1,c2,c3,c4 = st.columns(4)
    with c1: categoria = st.selectbox("Categoria lente", CATEGORIE, key=f"{prefix}_categoria")
    with c2: difetto = st.selectbox("Difetto principale", DIFFETTI, key=f"{prefix}_difetto")
    with c3: algoritmo = st.selectbox("Algoritmo", ALGORITMI, key=f"{prefix}_algoritmo")
    with c4: modello = st.selectbox("Modello produttore", MODELLI, key=f"{prefix}_modello")
    r1,r2,r3,r4 = st.columns(4)
    with r1: rx_sfera = st.number_input("Sfera", step=0.25, value=0.0, format="%.2f", key=f"{prefix}_sf")
    with r2: rx_cil = st.number_input("Cilindro", step=0.25, value=0.0, format="%.2f", key=f"{prefix}_cil")
    with r3: rx_asse = st.number_input("Asse", min_value=0, max_value=180, value=0, key=f"{prefix}_asse")
    with r4: rx_add = st.number_input("ADD", step=0.25, value=0.0, format="%.2f", key=f"{prefix}_add")
    t1,t2,t3,t4,t5 = st.columns(5)
    with t1: k1 = st.number_input("K1 (mm)", step=0.01, value=float(st.session_state.get(f"{prefix}_topo_k1",7.80)), format="%.2f", key=f"{prefix}_k1")
    with t2: k2 = st.number_input("K2 (mm)", step=0.01, value=float(st.session_state.get(f"{prefix}_topo_k2",7.90)), format="%.2f", key=f"{prefix}_k2")
    with t3: asse_k = st.number_input("Asse K", min_value=0, max_value=180, value=int(st.session_state.get(f"{prefix}_topo_assek",90)), key=f"{prefix}_assek")
    with t4: hvid = st.number_input("HVID", step=0.10, value=float(st.session_state.get(f"{prefix}_topo_hvid",11.8)), format="%.2f", key=f"{prefix}_hvid")
    with t5: pup = st.number_input("Pupilla", step=0.10, value=float(st.session_state.get(f"{prefix}_topo_pup",3.5)), format="%.2f", key=f"{prefix}_pup")
    a1,a2 = st.columns(2)
    with a1: target = st.number_input("Target Ortho-K (D)", step=0.25, value=0.0, format="%.2f", key=f"{prefix}_target")
    with a2: e_val = st.number_input("E-value", step=0.01, value=0.50, format="%.2f", key=f"{prefix}_e")
    v1,v2 = st.columns(2)
    with v1: av_lontano = st.text_input("AV lontano", value="", key=f"{prefix}_avl")
    with v2: av_vicino = st.text_input("AV vicino", value="", key=f"{prefix}_avv")
    n1,n2 = st.columns(2)
    with n1:
        materiale = st.text_input("Materiale", value="Da definire", key=f"{prefix}_mat")
        dominanza = st.selectbox("Dominanza", ["","OD","OS","Alternante"], key=f"{prefix}_dom")
    with n2:
        ricambio = st.text_input("Ricambio", value="Da definire", key=f"{prefix}_ric")
        stato = st.selectbox("Stato", STATI, key=f"{prefix}_stato")
    f1,f2,f3 = st.columns(3)
    with f1: fit_c = st.selectbox("Centro osservato", ["Neutro","Touch","Pooling"], key=f"{prefix}_fitc")
    with f2: fit_m = st.selectbox("Media periferia osservata", ["Uniforme","Stretto","Largo"], key=f"{prefix}_fitm")
    with f3: fit_b = st.selectbox("Bordo osservato", ["Adeguato","Stretto","Eccessivo"], key=f"{prefix}_fitb")
    fitting = st.text_area("Note fitting / fluoresceina", value="", height=80, key=f"{prefix}_fitting")
    note = st.text_area("Note lente / ordine", value="", height=100, key=f"{prefix}_note")
    return locals()

def _render_result_box(title, proposta):
    st.markdown(f"#### {title}")
    for k,v in [("Modello", proposta.get("modello_prod","")),("Sottotipo", proposta.get("sottotipo","")),("BC", proposta.get("lente_bc_mm","")),("RB", proposta.get("lente_rb_mm","")),("Diametro", proposta.get("lente_diam_mm","")),("Potere", proposta.get("lente_potere_d","")),("Cilindro", proposta.get("lente_cilindro_d","")),("Asse", proposta.get("lente_asse_cil","")),("ADD", proposta.get("lente_add_d",""))]:
        st.write(f"**{k}:** {v}")
    st.markdown("##### Curve costruttive")
    st.json(proposta.get("ordine", {}))
    fluor = proposta.get("fluor") or {}
    if fluor:
        st.markdown("##### Clearance stimata")
        st.write(f"Centrale: **{fluor.get('central_um','')} µm**")
        st.write(f"Reverse zone: **{fluor.get('reverse_um','')} µm**")
        st.write(f"Landing: **{fluor.get('landing_um','')} µm**")
        st.write(f"Edge lift: **{fluor.get('edge_um','')} µm**")
        st.caption(f"Pattern: {fluor.get('pattern','')} | {fluor.get('valutazione','')}")

def _build_payload(paziente_id, data_scheda, occhio, operatore, eye_input, proposta):
    now_iso = datetime.now().isoformat(timespec="seconds")
    return {
        "paziente_id": paziente_id, "data_scheda": _parse_date(data_scheda), "occhio": occhio,
        "categoria": eye_input["categoria"], "sottotipo": proposta.get("sottotipo"), "difetto": eye_input["difetto"], "algoritmo": eye_input["algoritmo"],
        "rx_sfera": eye_input["rx_sfera"], "rx_cilindro": eye_input["rx_cil"], "rx_asse": eye_input["rx_asse"], "rx_add": eye_input["rx_add"],
        "av_lontano": eye_input["av_lontano"], "av_vicino": eye_input["av_vicino"],
        "k1_mm": eye_input["k1"], "k2_mm": eye_input["k2"], "asse_k": eye_input["asse_k"], "diametro_hvid": eye_input["hvid"], "pupilla_mm": eye_input["pup"],
        "topografia_json": json.dumps({"dominanza": eye_input["dominanza"], "e_value": eye_input["e_val"], "ordine": proposta.get("ordine", {})}, ensure_ascii=False),
        "lente_rb_mm": proposta.get("lente_rb_mm"), "lente_diam_mm": proposta.get("lente_diam_mm"), "lente_bc_mm": proposta.get("lente_bc_mm"),
        "lente_potere_d": proposta.get("lente_potere_d"), "lente_cilindro_d": proposta.get("lente_cilindro_d"), "lente_asse_cil": proposta.get("lente_asse_cil"), "lente_add_d": proposta.get("lente_add_d"),
        "lente_materiale": eye_input["materiale"], "lente_ricambio": eye_input["ricambio"], "lente_note": eye_input["note"],
        "fitting_json": json.dumps({"centrale": eye_input["fit_c"], "media": eye_input["fit_m"], "bordo": eye_input["fit_b"], "note": eye_input["fitting"], "fluor_auto": proposta.get("fluor", {})}, ensure_ascii=False),
        "followup_json": json.dumps([], ensure_ascii=False), "stato": eye_input["stato"], "operatore": operatore, "created_at": now_iso, "updated_at": now_iso
    }

def salva_lente_contatto(conn, payload):
    keys = ["paziente_id","data_scheda","occhio","categoria","sottotipo","difetto","algoritmo","rx_sfera","rx_cilindro","rx_asse","rx_add","av_lontano","av_vicino","k1_mm","k2_mm","asse_k","diametro_hvid","pupilla_mm","topografia_json","lente_rb_mm","lente_diam_mm","lente_bc_mm","lente_potere_d","lente_cilindro_d","lente_asse_cil","lente_add_d","lente_materiale","lente_ricambio","lente_note","fitting_json","followup_json","stato","operatore","created_at","updated_at"]
    vals = [payload.get(k) for k in keys]
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            sql = f"INSERT INTO lenti_contatto ({', '.join(keys)}) VALUES ({_ph(len(keys), conn)}) RETURNING id"
            cur.execute(sql, vals)
            new_id = int(cur.fetchone()[0])
        else:
            sql = f"INSERT INTO lenti_contatto ({', '.join(keys)}) VALUES ({_ph(len(keys), conn)})"
            cur.execute(sql, vals)
            new_id = int(cur.lastrowid)
        conn.commit()
        return new_id
    finally:
        try: cur.close()
        except Exception: pass

def load_storico_paziente(conn, paziente_id:int):
    cur = conn.cursor()
    try:
        ph = "%s" if _is_postgres(conn) else "?"
        cur.execute(f"SELECT id,data_scheda,occhio,categoria,sottotipo,difetto,algoritmo,lente_bc_mm,lente_rb_mm,lente_diam_mm,lente_potere_d,lente_cilindro_d,lente_asse_cil,lente_add_d,stato,operatore FROM lenti_contatto WHERE paziente_id={ph} ORDER BY id DESC", (int(paziente_id),))
        return cur.fetchall() or []
    finally:
        try: cur.close()
        except Exception: pass

def ui_lenti_contatto():
    st.title("👁️ Lenti a contatto")
    st.caption("Versione self-contained: clearance, fluoresceina, curve costruttive, export TXT/PDF")
    try:
        conn = get_conn() if LAC_BRIDGE_OK else _get_conn()
        (init_db(conn) if LAC_BRIDGE_OK else init_lenti_contatto_db(conn))
    except Exception as e:
        st.error("Errore inizializzazione database.")
        st.exception(e)
        return

    with st.container(border=True):
        h1,h2,h3,h4 = st.columns([2,1,1,1])
        with h1: paziente_id, paziente_label = _select_paziente(conn)
        with h2: data_scheda = st.text_input("Data scheda", value=_today_str())
        with h3: operatore = st.text_input("Operatore", value="")
        with h4: salva_bil = st.checkbox("Salva entrambi", value=True)
    if not paziente_id:
        st.info("Seleziona un paziente per iniziare.")
        return

    tab0,tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["Import topografo","Nuova lente","Risultato","Fluoresceina","Ordine produttore","Salvataggio","Storico"])

    with tab0:
        _import_topographer_section()

    with tab1:
        od_tab,os_tab = st.tabs(["OD","OS"])
        with od_tab: od_input = _ui_eye_form("lac_od","Occhio destro")
        with os_tab: os_input = _ui_eye_form("lac_os","Occhio sinistro")

        if st.button("Calcola proposta lente", type="primary", use_container_width=True):
            od_prop = build_curves(od_input["categoria"], od_input["difetto"], od_input["algoritmo"], od_input["modello"], od_input["rx_sfera"], od_input["rx_cil"], od_input["rx_asse"], od_input["rx_add"], od_input["k1"], od_input["k2"], od_input["hvid"], od_input["pup"], od_input["target"], od_input["e_val"])
            os_prop = build_curves(os_input["categoria"], os_input["difetto"], os_input["algoritmo"], os_input["modello"], os_input["rx_sfera"], os_input["rx_cil"], os_input["rx_asse"], os_input["rx_add"], os_input["k1"], os_input["k2"], os_input["hvid"], os_input["pup"], os_input["target"], os_input["e_val"])
            st.session_state["lac_sc_input"] = {"paziente_id":paziente_id,"paziente_label":paziente_label,"data_scheda":data_scheda,"operatore":operatore,"od":od_input,"os":os_input,"salva_bil":salva_bil}
            st.session_state["lac_sc_prop"] = {"od":od_prop,"os":os_prop}
            st.success("Proposta calcolata.")

    with tab2:
        props = st.session_state.get("lac_sc_prop")
        if not props:
            st.info("Calcola prima una proposta lente.")
        else:
            c1,c2 = st.columns(2)
            with c1: _render_result_box("OD", props["od"])
            with c2: _render_result_box("OS", props["os"])

    with tab3:
        props = st.session_state.get("lac_sc_prop")
        if not props:
            st.info("Calcola prima una proposta lente.")
        else:
            c1,c2 = st.columns(2)
            with c1:
                st.markdown("#### Simulazione OD")
                fig = plot_fluorescein_simulation(props["od"], "OD") if LAC_BRIDGE_OK else _plot_fluorescein_simulation(props["od"], "OD")
                st.pyplot(fig, use_container_width=False)
            with c2:
                st.markdown("#### Simulazione OS")
                fig = plot_fluorescein_simulation(props["os"], "OS") if LAC_BRIDGE_OK else _plot_fluorescein_simulation(props["os"], "OS")
                st.pyplot(fig, use_container_width=False)

    with tab4:
        props = st.session_state.get("lac_sc_prop")
        data_in = st.session_state.get("lac_sc_input")
        if not props or not data_in:
            st.info("Calcola prima una proposta lente.")
        else:
            od_txt = _format_order_text("OD", props["od"])
            os_txt = _format_order_text("OS", props["os"])
            txt = _build_txt_export(props["od"], props["os"], data_in["paziente_label"], data_in["data_scheda"], data_in["operatore"])
            c1,c2 = st.columns(2)
            with c1:
                st.text_area("Ordine produttore OD", value=od_txt, height=420, key="ordprod_od")
            with c2:
                st.text_area("Ordine produttore OS", value=os_txt, height=420, key="ordprod_os")
            st.download_button("Esporta ordine TXT", data=txt.encode("utf-8"), file_name="ordine_lenti_contatto.txt", mime="text/plain", use_container_width=True)
            if REPORTLAB_OK:
                pdf = _build_pdf_export(txt)
                st.download_button("Esporta ordine PDF", data=pdf, file_name="ordine_lenti_contatto.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.info("Export PDF non disponibile: manca reportlab.")

    with tab5:
        data_in = st.session_state.get("lac_sc_input"); props = st.session_state.get("lac_sc_prop")
        if not data_in or not props:
            st.info("Niente da salvare: calcola prima la proposta.")
        else:
            st.markdown(f"**Paziente:** {data_in['paziente_label']}")
            if st.button("Salva lente/i nel database", type="primary", use_container_width=True):
                try:
                    ids=[]
                    ids.append(salva_lente_contatto(conn, (build_payload(data_in["paziente_id"], data_in["data_scheda"], "OD", data_in["operatore"], data_in["od"], props["od"]) if LAC_BRIDGE_OK else _build_payload(data_in["paziente_id"], data_in["data_scheda"], "OD", data_in["operatore"], data_in["od"], props["od"]))))
                    if data_in.get("salva_bil", True):
                        ids.append(salva_lente_contatto(conn, (build_payload(data_in["paziente_id"], data_in["data_scheda"], "OS", data_in["operatore"], data_in["os"], props["os"]) if LAC_BRIDGE_OK else _build_payload(data_in["paziente_id"], data_in["data_scheda"], "OS", data_in["operatore"], data_in["os"], props["os"]))))
                    st.success(f"Lente/i salvate correttamente. ID: {', '.join(map(str, ids))}")
                except Exception as e:
                    st.error("Errore durante il salvataggio.")
                    st.exception(e)

    with tab6:
        try:
            rows = load_storico_paziente(conn, paziente_id)
            if not rows:
                st.info("Nessuna lente salvata per questo paziente.")
            else:
                data=[]
                for r in rows:
                    data.append({"ID":_row_get(r,"id"),"Data":_row_get(r,"data_scheda"),"Occhio":_row_get(r,"occhio"),"Categoria":_row_get(r,"categoria"),"Sottotipo":_row_get(r,"sottotipo"),"Difetto":_row_get(r,"difetto"),"Algoritmo":_row_get(r,"algoritmo"),"BC":_row_get(r,"lente_bc_mm"),"RB":_row_get(r,"lente_rb_mm"),"Diam":_row_get(r,"lente_diam_mm"),"Potere":_row_get(r,"lente_potere_d"),"Cil":_row_get(r,"lente_cilindro_d"),"Asse":_row_get(r,"lente_asse_cil"),"ADD":_row_get(r,"lente_add_d"),"Stato":_row_get(r,"stato"),"Operatore":_row_get(r,"operatore")})
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Errore caricamento storico.")
            st.exception(e)
