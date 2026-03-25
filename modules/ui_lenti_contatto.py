# -*- coding: utf-8 -*-
"""
Modulo: Lenti a Contatto (livello clinico completo)
Gestionale The Organism – PNEV
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st


def _is_postgres(conn) -> bool:
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    try:
        mod = type(conn).__module__ or ""
        if "psycopg2" in mod or "psycopg" in mod:
            return True
    except Exception:
        pass
    return False


def _ph(n: int, conn) -> str:
    mark = "%s" if _is_postgres(conn) else "?"
    return ", ".join([mark] * n)


def _get_conn():
    try:
        from modules.app_core import get_connection
        return get_connection()
    except Exception:
        pass
    import sqlite3
    conn = sqlite3.connect("organism.db")
    conn.row_factory = sqlite3.Row
    return conn


def _row_get(row, key, default=None):
    try:
        v = row[key]
        return v if v is not None else default
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
    data_scheda TEXT,
    occhio TEXT,
    categoria TEXT,
    sottotipo TEXT,
    difetto TEXT,
    algoritmo TEXT,
    rx_sfera DOUBLE PRECISION,
    rx_cilindro DOUBLE PRECISION,
    rx_asse INTEGER,
    rx_add DOUBLE PRECISION,
    av_lontano TEXT,
    av_vicino TEXT,
    k1_mm DOUBLE PRECISION,
    k2_mm DOUBLE PRECISION,
    asse_k INTEGER,
    diametro_hvid DOUBLE PRECISION,
    pupilla_mm DOUBLE PRECISION,
    topografia_json TEXT,
    lente_rb_mm DOUBLE PRECISION,
    lente_diam_mm DOUBLE PRECISION,
    lente_bc_mm DOUBLE PRECISION,
    lente_potere_d DOUBLE PRECISION,
    lente_cilindro_d DOUBLE PRECISION,
    lente_asse_cil INTEGER,
    lente_add_d DOUBLE PRECISION,
    lente_materiale TEXT,
    lente_ricambio TEXT,
    lente_note TEXT,
    fitting_json TEXT,
    followup_json TEXT,
    stato TEXT,
    operatore TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""

_SQL_SL = """
CREATE TABLE IF NOT EXISTS lenti_contatto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paziente_id INTEGER NOT NULL,
    data_scheda TEXT,
    occhio TEXT,
    categoria TEXT,
    sottotipo TEXT,
    difetto TEXT,
    algoritmo TEXT,
    rx_sfera REAL,
    rx_cilindro REAL,
    rx_asse INTEGER,
    rx_add REAL,
    av_lontano TEXT,
    av_vicino TEXT,
    k1_mm REAL,
    k2_mm REAL,
    asse_k INTEGER,
    diametro_hvid REAL,
    pupilla_mm REAL,
    topografia_json TEXT,
    lente_rb_mm REAL,
    lente_diam_mm REAL,
    lente_bc_mm REAL,
    lente_potere_d REAL,
    lente_cilindro_d REAL,
    lente_asse_cil INTEGER,
    lente_add_d REAL,
    lente_materiale TEXT,
    lente_ricambio TEXT,
    lente_note TEXT,
    fitting_json TEXT,
    followup_json TEXT,
    stato TEXT,
    operatore TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""


def init_lenti_contatto_db(conn) -> None:
    cur = conn.cursor()
    try:
        cur.execute(_SQL_PG if _is_postgres(conn) else _SQL_SL)
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _detect_patient_table_and_cols(conn):
    try:
        from modules.app_core import _detect_patient_table_and_cols
        return _detect_patient_table_and_cols(conn)
    except Exception:
        return None, {}


def fetch_pazienti_for_select(conn, limit=5000):
    try:
        from modules.app_core import fetch_pazienti_for_select
        return fetch_pazienti_for_select(conn, limit=limit)
    except Exception:
        table, colmap = _detect_patient_table_and_cols(conn)
        if not table:
            return [], None, None
        return [], table, colmap


def _select_paziente(conn):
    rows, _, _ = fetch_pazienti_for_select(conn, limit=5000)
    if not rows:
        st.warning("Nessun paziente disponibile.")
        return None, ""
    options = []
    for r in rows:
        pid, cogn, nome, dn, scuola, eta = r
        label = f"{cogn} {nome} • {dn or ''} • id {pid}"
        options.append((int(pid), label))
    sel = st.selectbox(
        "Paziente",
        options=options,
        format_func=lambda x: x[1],
        key="lac_clinic_paziente_select",
    )
    return sel[0], sel[1]


CATEGORIE = [
    "Morbida sferica",
    "Torica",
    "Multifocale / Presbiopia",
    "RGP",
    "Ortho-K / Inversa",
    "Custom avanzata",
]

DIFFETTI = [
    "Miopia",
    "Ipermetropia",
    "Astigmatismo",
    "Presbiopia",
    "Miopia + Astigmatismo",
    "Ipermetropia + Astigmatismo",
    "Presbiopia + Astigmatismo",
    "Presbiopia + Miopia",
    "Presbiopia + Ipermetropia",
]

ALGORITMI = [
    "Standard",
    "Tabelle produttore",
    "Toffoli",
    "Calossi",
    "Clinico personalizzato",
]

STATI = ["Calcolata", "Provata", "Ordinata", "Consegnata"]


def _vertex_comp(power: float) -> float:
    try:
        power = float(power)
    except Exception:
        return 0.0
    if abs(power) > 4:
        try:
            return round(power / (1 - 0.012 * power), 2)
        except Exception:
            return round(power, 2)
    return round(power, 2)


def _pick_subtype(categoria: str, rx_cil: float, rx_add: float) -> str:
    cyl_sig = abs(rx_cil or 0) >= 0.75
    add_sig = abs(rx_add or 0) >= 0.75

    if categoria == "Morbida sferica":
        return "Sferica morbida"
    if categoria == "Torica":
        return "Torica stabilizzata"
    if categoria == "Multifocale / Presbiopia":
        return "Multifocale torica" if cyl_sig else "Multifocale"
    if categoria == "RGP":
        return "RGP torica" if cyl_sig else "RGP sferica"
    if categoria == "Ortho-K / Inversa":
        return "Ortho-K torica" if cyl_sig else "Ortho-K"
    if categoria == "Custom avanzata":
        if add_sig and cyl_sig:
            return "Custom multifocale torica"
        if add_sig:
            return "Custom multifocale"
        if cyl_sig:
            return "Custom torica"
        return "Custom sferica"
    return categoria


def _clinical_or_default(val: Optional[float], default: float) -> float:
    try:
        if val is None:
            return float(default)
        return float(val)
    except Exception:
        return float(default)


def _calcola_lente_clinica(
    *,
    categoria: str,
    algoritmo: str,
    rx_sfera: float,
    rx_cil: float,
    rx_asse: int,
    rx_add: float,
    k1: float,
    k2: float,
    hvid: float,
    pupilla: float,
    target_orthok: float = 0.0,
    dominanza: str = "",
) -> Dict[str, Any]:
    k1 = _clinical_or_default(k1, 7.80)
    k2 = _clinical_or_default(k2, 7.90)
    hvid = _clinical_or_default(hvid, 11.8)
    pupilla = _clinical_or_default(pupilla, 3.5)

    k_med = round((k1 + k2) / 2, 2)
    rx_sfera_eff = _vertex_comp(rx_sfera)
    cyl_sig = abs(rx_cil or 0) >= 0.75
    subtype = _pick_subtype(categoria, rx_cil, rx_add)

    bc_soft = 8.60 if k_med >= 7.80 else 8.40
    diam_soft = 14.20 if hvid <= 11.8 else 14.40

    if categoria == "Morbida sferica":
        return {
            "sottotipo": subtype,
            "lente_bc_mm": bc_soft,
            "lente_rb_mm": None,
            "lente_diam_mm": diam_soft,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
        }

    if categoria == "Torica":
        return {
            "sottotipo": subtype,
            "lente_bc_mm": bc_soft,
            "lente_rb_mm": None,
            "lente_diam_mm": 14.50,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse or 0),
            "lente_add_d": 0.0,
        }

    if categoria == "Multifocale / Presbiopia":
        return {
            "sottotipo": subtype,
            "lente_bc_mm": 8.60,
            "lente_rb_mm": None,
            "lente_diam_mm": 14.20,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0,
            "lente_asse_cil": int(rx_asse or 0) if cyl_sig else None,
            "lente_add_d": round(rx_add, 2),
        }

    if categoria == "RGP":
        rb = round(k_med - 0.05, 2)
        if algoritmo == "Calossi":
            rb = round(k_med - 0.03, 2)
        return {
            "sottotipo": subtype,
            "lente_bc_mm": rb,
            "lente_rb_mm": rb,
            "lente_diam_mm": 9.60,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0,
            "lente_asse_cil": int(rx_asse or 0) if cyl_sig else None,
            "lente_add_d": round(rx_add, 2) if abs(rx_add or 0) >= 0.75 else 0.0,
        }

    if categoria == "Ortho-K / Inversa":
        target = abs(target_orthok) if target_orthok else abs(rx_sfera or 0)
        if algoritmo == "Toffoli":
            rb = round(k_med + (target * 0.08), 2)
            diam = 10.60 if hvid < 12.0 else 10.80
        elif algoritmo == "Calossi":
            rb = round(k_med + (target * 0.10), 2)
            diam = 10.70 if hvid < 12.0 else 10.90
        else:
            rb = round(k_med + (target * 0.09), 2)
            diam = 10.60 if hvid < 12.0 else 10.80

        return {
            "sottotipo": subtype,
            "lente_bc_mm": rb,
            "lente_rb_mm": rb,
            "lente_diam_mm": diam,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0,
            "lente_asse_cil": int(rx_asse or 0) if cyl_sig else None,
            "lente_add_d": 0.0,
        }

    rb = round(k_med, 2)
    if algoritmo == "Toffoli":
        rb = round(k_med - 0.02, 2)
    elif algoritmo == "Calossi":
        rb = round(k_med + 0.02, 2)

    return {
        "sottotipo": subtype,
        "lente_bc_mm": 8.60,
        "lente_rb_mm": rb,
        "lente_diam_mm": 14.20,
        "lente_potere_d": rx_sfera_eff,
        "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0,
        "lente_asse_cil": int(rx_asse or 0) if cyl_sig else None,
        "lente_add_d": round(rx_add, 2) if abs(rx_add or 0) >= 0.75 else 0.0,
    }


def salva_lente_contatto(conn, payload: Dict[str, Any]) -> int:
    keys = [
        "paziente_id", "data_scheda", "occhio", "categoria", "sottotipo", "difetto", "algoritmo",
        "rx_sfera", "rx_cilindro", "rx_asse", "rx_add", "av_lontano", "av_vicino",
        "k1_mm", "k2_mm", "asse_k", "diametro_hvid", "pupilla_mm", "topografia_json",
        "lente_rb_mm", "lente_diam_mm", "lente_bc_mm", "lente_potere_d", "lente_cilindro_d",
        "lente_asse_cil", "lente_add_d", "lente_materiale", "lente_ricambio", "lente_note",
        "fitting_json", "followup_json", "stato", "operatore", "created_at", "updated_at"
    ]
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
        try:
            cur.close()
        except Exception:
            pass


def load_storico_paziente(conn, paziente_id: int):
    cur = conn.cursor()
    try:
        sql = """
            SELECT id, data_scheda, occhio, categoria, sottotipo, difetto, algoritmo,
                   lente_bc_mm, lente_rb_mm, lente_diam_mm, lente_potere_d,
                   lente_cilindro_d, lente_asse_cil, lente_add_d, stato, operatore
            FROM lenti_contatto
            WHERE paziente_id = {ph}
            ORDER BY id DESC
        """.format(ph="%s" if _is_postgres(conn) else "?")
        cur.execute(sql, (int(paziente_id),))
        return cur.fetchall() or []
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _ui_eye_form(prefix: str, label: str, category_default: str, algorithm_default: str):
    st.markdown(f"### {label}")

    c1, c2, c3 = st.columns(3)
    with c1:
        categoria = st.selectbox("Categoria lente", CATEGORIE, index=CATEGORIE.index(category_default), key=f"{prefix}_categoria")
    with c2:
        difetto = st.selectbox("Difetto principale", DIFFETTI, key=f"{prefix}_difetto")
    with c3:
        algoritmo = st.selectbox("Algoritmo", ALGORITMI, index=ALGORITMI.index(algorithm_default), key=f"{prefix}_algoritmo")

    st.markdown("#### Refrazione")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        rx_sfera = st.number_input("Sfera", step=0.25, value=0.00, format="%.2f", key=f"{prefix}_sfera")
    with r2:
        rx_cil = st.number_input("Cilindro", step=0.25, value=0.00, format="%.2f", key=f"{prefix}_cil")
    with r3:
        rx_asse = st.number_input("Asse", min_value=0, max_value=180, value=0, step=1, key=f"{prefix}_asse")
    with r4:
        rx_add = st.number_input("ADD", step=0.25, value=0.00, format="%.2f", key=f"{prefix}_add")

    r5, r6 = st.columns(2)
    with r5:
        av_lontano = st.text_input("AV lontano", value="", key=f"{prefix}_avl")
    with r6:
        av_vicino = st.text_input("AV vicino", value="", key=f"{prefix}_avv")

    st.markdown("#### Dati corneali / topografici")
    k1c, k2c, akc, hvc = st.columns(4)
    with k1c:
        k1 = st.number_input("K1 (mm)", step=0.01, value=7.80, format="%.2f", key=f"{prefix}_k1")
    with k2c:
        k2 = st.number_input("K2 (mm)", step=0.01, value=7.90, format="%.2f", key=f"{prefix}_k2")
    with akc:
        asse_k = st.number_input("Asse K", min_value=0, max_value=180, value=90, key=f"{prefix}_assek")
    with hvc:
        hvid = st.number_input("HVID / diametro corneale", step=0.10, value=11.8, format="%.2f", key=f"{prefix}_hvid")

    p1, p2 = st.columns(2)
    with p1:
        pupilla = st.number_input("Diametro pupilla (mm)", step=0.10, value=3.5, format="%.2f", key=f"{prefix}_pup")
    with p2:
        target_orthok = st.number_input("Target Ortho-K (D)", step=0.25, value=0.0, format="%.2f", key=f"{prefix}_target")

    st.markdown("#### Note cliniche / PNEV")
    n1, n2 = st.columns(2)
    with n1:
        dominanza = st.selectbox("Dominanza oculare", ["", "OD", "OS", "Alternante"], key=f"{prefix}_dom")
        materiale = st.text_input("Materiale", value="Da definire", key=f"{prefix}_mat")
    with n2:
        ricambio = st.text_input("Ricambio", value="Da definire", key=f"{prefix}_ric")
        stato = st.selectbox("Stato", STATI, key=f"{prefix}_stato")

    fitting = st.text_area("Fitting / fluoresceina / appoggio", value="", height=90, key=f"{prefix}_fitting")
    note = st.text_area("Note lente / note PNEV", value="", height=110, key=f"{prefix}_note")

    return {
        "categoria": categoria,
        "difetto": difetto,
        "algoritmo": algoritmo,
        "rx_sfera": rx_sfera,
        "rx_cil": rx_cil,
        "rx_asse": rx_asse,
        "rx_add": rx_add,
        "av_lontano": av_lontano,
        "av_vicino": av_vicino,
        "k1": k1,
        "k2": k2,
        "asse_k": asse_k,
        "hvid": hvid,
        "pupilla": pupilla,
        "target_orthok": target_orthok,
        "dominanza": dominanza,
        "materiale": materiale,
        "ricambio": ricambio,
        "stato": stato,
        "fitting": fitting,
        "note": note,
    }


def _render_result_box(title: str, proposta: Dict[str, Any]):
    st.markdown(f"#### {title}")
    st.write(f"**Sottotipo:** {proposta.get('sottotipo', '')}")
    st.write(f"**BC:** {proposta.get('lente_bc_mm', '')}")
    st.write(f"**RB:** {proposta.get('lente_rb_mm', '')}")
    st.write(f"**Diametro:** {proposta.get('lente_diam_mm', '')}")
    st.write(f"**Potere:** {proposta.get('lente_potere_d', '')}")
    st.write(f"**Cilindro:** {proposta.get('lente_cilindro_d', '')}")
    st.write(f"**Asse:** {proposta.get('lente_asse_cil', '')}")
    st.write(f"**ADD:** {proposta.get('lente_add_d', '')}")


def _build_payload(
    *,
    paziente_id: int,
    data_scheda: str,
    occhio: str,
    operatore: str,
    eye_input: Dict[str, Any],
    proposta: Dict[str, Any],
) -> Dict[str, Any]:
    now_iso = datetime.now().isoformat(timespec="seconds")
    return {
        "paziente_id": paziente_id,
        "data_scheda": _parse_date(data_scheda),
        "occhio": occhio,
        "categoria": eye_input["categoria"],
        "sottotipo": proposta.get("sottotipo"),
        "difetto": eye_input["difetto"],
        "algoritmo": eye_input["algoritmo"],
        "rx_sfera": eye_input["rx_sfera"],
        "rx_cilindro": eye_input["rx_cil"],
        "rx_asse": eye_input["rx_asse"],
        "rx_add": eye_input["rx_add"],
        "av_lontano": eye_input["av_lontano"],
        "av_vicino": eye_input["av_vicino"],
        "k1_mm": eye_input["k1"],
        "k2_mm": eye_input["k2"],
        "asse_k": eye_input["asse_k"],
        "diametro_hvid": eye_input["hvid"],
        "pupilla_mm": eye_input["pupilla"],
        "topografia_json": json.dumps(
            {
                "dominanza": eye_input["dominanza"],
                "target_orthok": eye_input["target_orthok"],
            },
            ensure_ascii=False,
        ),
        "lente_rb_mm": proposta.get("lente_rb_mm"),
        "lente_diam_mm": proposta.get("lente_diam_mm"),
        "lente_bc_mm": proposta.get("lente_bc_mm"),
        "lente_potere_d": proposta.get("lente_potere_d"),
        "lente_cilindro_d": proposta.get("lente_cilindro_d"),
        "lente_asse_cil": proposta.get("lente_asse_cil"),
        "lente_add_d": proposta.get("lente_add_d"),
        "lente_materiale": eye_input["materiale"],
        "lente_ricambio": eye_input["ricambio"],
        "lente_note": eye_input["note"],
        "fitting_json": json.dumps({"fitting": eye_input["fitting"]}, ensure_ascii=False),
        "followup_json": json.dumps([], ensure_ascii=False),
        "stato": eye_input["stato"],
        "operatore": operatore,
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def ui_lenti_contatto():
    st.title("👁️ Lenti a contatto")
    st.caption("Modulo clinico completo – The Organism / PNEV")

    try:
        conn = _get_conn()
        init_lenti_contatto_db(conn)
    except Exception as e:
        st.error("Errore inizializzazione database.")
        st.exception(e)
        return

    with st.container(border=True):
        h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
        with h1:
            paziente_id, paziente_label = _select_paziente(conn)
        with h2:
            data_scheda = st.text_input("Data scheda", value=_today_str())
        with h3:
            operatore = st.text_input("Operatore", value="")
        with h4:
            salva_bil = st.checkbox("Salva entrambi gli occhi", value=True)

    if not paziente_id:
        st.info("Seleziona un paziente per iniziare.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "Nuova lente",
        "Risultato",
        "Salvataggio",
        "Storico",
    ])

    with tab1:
        st.subheader("1. Dati clinici")
        od_tab, os_tab = st.tabs(["OD", "OS"])
        with od_tab:
            od_input = _ui_eye_form("lac_od", "Occhio destro", "Morbida sferica", "Standard")
        with os_tab:
            os_input = _ui_eye_form("lac_os", "Occhio sinistro", "Morbida sferica", "Standard")

        if st.button("Calcola proposta lente", type="primary", use_container_width=True):
            od_prop = _calcola_lente_clinica(
                categoria=od_input["categoria"],
                algoritmo=od_input["algoritmo"],
                rx_sfera=od_input["rx_sfera"],
                rx_cil=od_input["rx_cil"],
                rx_asse=od_input["rx_asse"],
                rx_add=od_input["rx_add"],
                k1=od_input["k1"],
                k2=od_input["k2"],
                hvid=od_input["hvid"],
                pupilla=od_input["pupilla"],
                target_orthok=od_input["target_orthok"],
                dominanza=od_input["dominanza"],
            )
            os_prop = _calcola_lente_clinica(
                categoria=os_input["categoria"],
                algoritmo=os_input["algoritmo"],
                rx_sfera=os_input["rx_sfera"],
                rx_cil=os_input["rx_cil"],
                rx_asse=os_input["rx_asse"],
                rx_add=os_input["rx_add"],
                k1=os_input["k1"],
                k2=os_input["k2"],
                hvid=os_input["hvid"],
                pupilla=os_input["pupilla"],
                target_orthok=os_input["target_orthok"],
                dominanza=os_input["dominanza"],
            )

            st.session_state["lac_complete_input"] = {
                "paziente_id": paziente_id,
                "paziente_label": paziente_label,
                "data_scheda": data_scheda,
                "operatore": operatore,
                "od": od_input,
                "os": os_input,
                "salva_bil": salva_bil,
            }
            st.session_state["lac_complete_prop"] = {
                "od": od_prop,
                "os": os_prop,
            }
            st.success("Proposta calcolata. Vai nella tab 'Risultato'.")

    with tab2:
        st.subheader("2. Risultato lente")
        props = st.session_state.get("lac_complete_prop")
        if not props:
            st.info("Calcola prima una proposta lente.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                _render_result_box("OD", props["od"])
            with c2:
                _render_result_box("OS", props["os"])

    with tab3:
        st.subheader("3. Salvataggio")
        data_in = st.session_state.get("lac_complete_input")
        props = st.session_state.get("lac_complete_prop")

        if not data_in or not props:
            st.info("Niente da salvare: calcola prima la proposta.")
        else:
            st.markdown(f"**Paziente:** {data_in['paziente_label']}")
            st.markdown(f"**Operatore:** {data_in['operatore'] or '-'}")
            st.markdown(f"**Data scheda:** {data_in['data_scheda']}")
            if st.button("Salva lente/i nel database", type="primary", use_container_width=True):
                try:
                    saved_ids = []

                    od_payload = _build_payload(
                        paziente_id=data_in["paziente_id"],
                        data_scheda=data_in["data_scheda"],
                        occhio="OD",
                        operatore=data_in["operatore"],
                        eye_input=data_in["od"],
                        proposta=props["od"],
                    )
                    saved_ids.append(salva_lente_contatto(conn, od_payload))

                    if data_in.get("salva_bil", True):
                        os_payload = _build_payload(
                            paziente_id=data_in["paziente_id"],
                            data_scheda=data_in["data_scheda"],
                            occhio="OS",
                            operatore=data_in["operatore"],
                            eye_input=data_in["os"],
                            proposta=props["os"],
                        )
                        saved_ids.append(salva_lente_contatto(conn, os_payload))

                    st.success(f"Lente/i salvate correttamente. ID: {', '.join(map(str, saved_ids))}")
                except Exception as e:
                    st.error("Errore durante il salvataggio.")
                    st.exception(e)

    with tab4:
        st.subheader("4. Storico paziente")
        try:
            rows = load_storico_paziente(conn, paziente_id)
            if not rows:
                st.info("Nessuna lente salvata per questo paziente.")
            else:
                data = []
                for r in rows:
                    data.append({
                        "ID": _row_get(r, "id"),
                        "Data": _row_get(r, "data_scheda"),
                        "Occhio": _row_get(r, "occhio"),
                        "Categoria": _row_get(r, "categoria"),
                        "Sottotipo": _row_get(r, "sottotipo"),
                        "Difetto": _row_get(r, "difetto"),
                        "Algoritmo": _row_get(r, "algoritmo"),
                        "BC": _row_get(r, "lente_bc_mm"),
                        "RB": _row_get(r, "lente_rb_mm"),
                        "Diam": _row_get(r, "lente_diam_mm"),
                        "Potere": _row_get(r, "lente_potere_d"),
                        "Cil": _row_get(r, "lente_cilindro_d"),
                        "Asse": _row_get(r, "lente_asse_cil"),
                        "ADD": _row_get(r, "lente_add_d"),
                        "Stato": _row_get(r, "stato"),
                        "Operatore": _row_get(r, "operatore"),
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Errore caricamento storico.")
            st.exception(e)
