# -*- coding: utf-8 -*-
"""
Modulo: Lenti a Contatto (nuovo)
Gestionale The Organism – PNEV
"""

from __future__ import annotations

import json
from datetime import date, datetime

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
    try:
        cur_type = type(conn.cursor()).__name__
        if "Pg" in cur_type:
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
        key="lac_new_paziente_select",
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


def _calcola_lente_base(categoria, rx_sfera, rx_cil, rx_asse, rx_add, k1, k2, hvid):
    k_med = round((k1 + k2) / 2, 2) if k1 and k2 else 7.80

    if categoria == "Morbida sferica":
        bc = 8.60 if k_med >= 7.80 else 8.40
        diam = 14.20 if hvid <= 11.8 else 14.40
        return {
            "lente_bc_mm": bc,
            "lente_diam_mm": diam,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
            "sottotipo": "Sferica morbida",
        }

    if categoria == "Torica":
        bc = 8.60 if k_med >= 7.80 else 8.40
        diam = 14.50
        return {
            "lente_bc_mm": bc,
            "lente_diam_mm": diam,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse or 0),
            "lente_add_d": 0.0,
            "sottotipo": "Torica morbida",
        }

    if categoria == "Multifocale / Presbiopia":
        return {
            "lente_bc_mm": 8.60,
            "lente_diam_mm": 14.20,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse or 0) if abs(rx_cil) >= 0.75 else None,
            "lente_add_d": round(rx_add, 2),
            "sottotipo": "Multifocale",
        }

    if categoria == "RGP":
        rb = round(k_med - 0.05, 2)
        return {
            "lente_rb_mm": rb,
            "lente_bc_mm": rb,
            "lente_diam_mm": 9.60,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse or 0) if abs(rx_cil) >= 0.75 else None,
            "lente_add_d": round(rx_add, 2) if rx_add else 0.0,
            "sottotipo": "RGP",
        }

    if categoria == "Ortho-K / Inversa":
        rb = round(k_med + 0.30, 2)
        return {
            "lente_rb_mm": rb,
            "lente_bc_mm": rb,
            "lente_diam_mm": 10.60,
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse or 0) if abs(rx_cil) >= 0.75 else None,
            "lente_add_d": 0.0,
            "sottotipo": "Ortho-K base",
        }

    rb = round(k_med, 2)
    return {
        "lente_rb_mm": rb,
        "lente_bc_mm": rb,
        "lente_diam_mm": 14.20,
        "lente_potere_d": round(rx_sfera, 2),
        "lente_cilindro_d": round(rx_cil, 2),
        "lente_asse_cil": int(rx_asse or 0) if abs(rx_cil) >= 0.75 else None,
        "lente_add_d": round(rx_add, 2),
        "sottotipo": "Custom base",
    }


def salva_lente_contatto(conn, payload):
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


def ui_lenti_contatto():
    st.title("👁️ Lenti a contatto")
    st.caption("Nuovo modulo unico contattologia – ripartenza da zero")

    try:
        conn = _get_conn()
        init_lenti_contatto_db(conn)
    except Exception as e:
        st.error("Errore inizializzazione database.")
        st.exception(e)
        return

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            paziente_id, paziente_label = _select_paziente(conn)
        with c2:
            data_scheda = st.text_input("Data scheda", value=_today_str())
        with c3:
            occhio = st.selectbox("Occhio", ["OD", "OS", "BIL"], index=2)

    if not paziente_id:
        st.info("Seleziona un paziente per iniziare.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Nuova lente", "Risultato", "Salvataggio", "Storico"])

    with tab1:
        st.subheader("1. Dati clinici")
        a1, a2, a3 = st.columns(3)
        with a1:
            categoria = st.selectbox("Categoria lente", CATEGORIE)
        with a2:
            difetto = st.selectbox("Difetto principale", DIFFETTI)
        with a3:
            algoritmo = st.selectbox("Algoritmo", ALGORITMI)

        st.markdown("#### Refrazione")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            rx_sfera = st.number_input("Sfera", step=0.25, value=0.00, format="%.2f")
        with r2:
            rx_cil = st.number_input("Cilindro", step=0.25, value=0.00, format="%.2f")
        with r3:
            rx_asse = st.number_input("Asse", min_value=0, max_value=180, value=0, step=1)
        with r4:
            rx_add = st.number_input("ADD", step=0.25, value=0.00, format="%.2f")

        r5, r6 = st.columns(2)
        with r5:
            av_lontano = st.text_input("AV lontano", value="")
        with r6:
            av_vicino = st.text_input("AV vicino", value="")

        st.markdown("#### Dati corneali / topografici")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            k1 = st.number_input("K1 (mm)", step=0.01, value=7.80, format="%.2f")
        with c2:
            k2 = st.number_input("K2 (mm)", step=0.01, value=7.90, format="%.2f")
        with c3:
            asse_k = st.number_input("Asse K", min_value=0, max_value=180, value=90)
        with c4:
            hvid = st.number_input("HVID / diametro corneale", step=0.10, value=11.8, format="%.2f")

        c5, c6 = st.columns(2)
        with c5:
            pupilla = st.number_input("Diametro pupilla (mm)", step=0.10, value=3.5, format="%.2f")
        with c6:
            operatore = st.text_input("Operatore", value="")

        topografia_note = st.text_area("Topografia / note corneali", value="", height=100)

        if st.button("Calcola proposta lente", type="primary", use_container_width=True):
            proposta = _calcola_lente_base(categoria, rx_sfera, rx_cil, rx_asse, rx_add, k1, k2, hvid)
            st.session_state["lac_new_proposta"] = proposta
            st.session_state["lac_new_input"] = {
                "paziente_id": paziente_id,
                "paziente_label": paziente_label,
                "data_scheda": data_scheda,
                "occhio": occhio,
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
                "topografia_note": topografia_note,
                "operatore": operatore,
            }
            st.success("Proposta calcolata. Vai nella tab 'Risultato'.")

    with tab2:
        st.subheader("2. Risultato lente")
        proposta = st.session_state.get("lac_new_proposta")
        dati_in = st.session_state.get("lac_new_input")

        if not proposta or not dati_in:
            st.info("Calcola prima una proposta lente.")
        else:
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("#### Parametri suggeriti")
                st.write(f"**Sottotipo:** {proposta.get('sottotipo', '')}")
                st.write(f"**BC:** {proposta.get('lente_bc_mm', '')}")
                st.write(f"**RB:** {proposta.get('lente_rb_mm', '')}")
                st.write(f"**Diametro:** {proposta.get('lente_diam_mm', '')}")
                st.write(f"**Potere:** {proposta.get('lente_potere_d', '')}")
                st.write(f"**Cilindro:** {proposta.get('lente_cilindro_d', '')}")
                st.write(f"**Asse:** {proposta.get('lente_asse_cil', '')}")
                st.write(f"**ADD:** {proposta.get('lente_add_d', '')}")

            with d2:
                st.markdown("#### Rifinitura finale")
                lente_materiale = st.text_input("Materiale", value="Da definire", key="lac_mat")
                lente_ricambio = st.text_input("Ricambio", value="Da definire", key="lac_ric")
                stato = st.selectbox("Stato", ["Calcolata", "Provata", "Ordinata", "Consegnata"], key="lac_stato")
                lente_note = st.text_area("Note lente", value="", height=120, key="lac_note")

                st.session_state["lac_new_finalize"] = {
                    "lente_materiale": lente_materiale,
                    "lente_ricambio": lente_ricambio,
                    "stato": stato,
                    "lente_note": lente_note,
                }

    with tab3:
        st.subheader("3. Salvataggio")
        proposta = st.session_state.get("lac_new_proposta")
        dati_in = st.session_state.get("lac_new_input")
        finalize = st.session_state.get("lac_new_finalize", {})

        if not proposta or not dati_in:
            st.info("Niente da salvare: manca la proposta.")
        else:
            if st.button("Salva lente nel database", type="primary", use_container_width=True):
                now_iso = datetime.now().isoformat(timespec="seconds")
                payload = {
                    "paziente_id": dati_in["paziente_id"],
                    "data_scheda": _parse_date(dati_in["data_scheda"]),
                    "occhio": dati_in["occhio"],
                    "categoria": dati_in["categoria"],
                    "sottotipo": proposta.get("sottotipo"),
                    "difetto": dati_in["difetto"],
                    "algoritmo": dati_in["algoritmo"],
                    "rx_sfera": dati_in["rx_sfera"],
                    "rx_cilindro": dati_in["rx_cil"],
                    "rx_asse": dati_in["rx_asse"],
                    "rx_add": dati_in["rx_add"],
                    "av_lontano": dati_in["av_lontano"],
                    "av_vicino": dati_in["av_vicino"],
                    "k1_mm": dati_in["k1"],
                    "k2_mm": dati_in["k2"],
                    "asse_k": dati_in["asse_k"],
                    "diametro_hvid": dati_in["hvid"],
                    "pupilla_mm": dati_in["pupilla"],
                    "topografia_json": json.dumps({"note": dati_in["topografia_note"]}, ensure_ascii=False),
                    "lente_rb_mm": proposta.get("lente_rb_mm"),
                    "lente_diam_mm": proposta.get("lente_diam_mm"),
                    "lente_bc_mm": proposta.get("lente_bc_mm"),
                    "lente_potere_d": proposta.get("lente_potere_d"),
                    "lente_cilindro_d": proposta.get("lente_cilindro_d"),
                    "lente_asse_cil": proposta.get("lente_asse_cil"),
                    "lente_add_d": proposta.get("lente_add_d"),
                    "lente_materiale": finalize.get("lente_materiale", ""),
                    "lente_ricambio": finalize.get("lente_ricambio", ""),
                    "lente_note": finalize.get("lente_note", ""),
                    "fitting_json": json.dumps({}, ensure_ascii=False),
                    "followup_json": json.dumps([], ensure_ascii=False),
                    "stato": finalize.get("stato", "Calcolata"),
                    "operatore": dati_in["operatore"],
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
                try:
                    new_id = salva_lente_contatto(conn, payload)
                    st.success(f"Lente salvata correttamente. ID: {new_id}")
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
