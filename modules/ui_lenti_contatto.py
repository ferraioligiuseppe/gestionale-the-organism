# -*- coding: utf-8 -*-
"""
Modulo: Lenti a Contatto (upgrade clinico)
Gestionale The Organism – PNEV
"""

from __future__ import annotations
import json
from datetime import date, datetime
import pandas as pd
import streamlit as st


# ========================
# DB HELPERS
# ========================

def _is_postgres(conn) -> bool:
    try:
        return "psycopg" in str(type(conn))
    except:
        return False


def _ph(n: int, conn) -> str:
    return ", ".join(["%s" if _is_postgres(conn) else "?"] * n)


def _get_conn():
    from modules.app_core import get_connection
    return get_connection()


def _today_str():
    return date.today().strftime("%d/%m/%Y")


def _parse_date(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return date.today().isoformat()


# ========================
# CALCOLO CLINICO (UPGRADE)
# ========================

def _calcola_lente_base(categoria, rx_sfera, rx_cil, rx_asse, rx_add, k1, k2, hvid):

    k_med = round((k1 + k2) / 2, 2) if k1 and k2 else 7.80

    # vertex semplificato
    def vertex(power):
        if abs(power) > 4:
            return round(power / (1 - 0.012 * power), 2)
        return round(power, 2)

    rx_sfera_eff = vertex(rx_sfera)
    cilindro_significativo = abs(rx_cil) >= 0.75

    # ----------------
    if categoria == "Morbida sferica":
        return {
            "lente_bc_mm": 8.60 if k_med >= 7.80 else 8.40,
            "lente_diam_mm": 14.20 if hvid <= 11.8 else 14.40,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
            "sottotipo": "Sferica morbida",
        }

    # ----------------
    if categoria == "Torica":
        return {
            "lente_bc_mm": 8.60,
            "lente_diam_mm": 14.50,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse),
            "sottotipo": "Torica stabilizzata",
        }

    # ----------------
    if categoria == "Multifocale / Presbiopia":
        return {
            "lente_bc_mm": 8.60,
            "lente_diam_mm": 14.20,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2) if cilindro_significativo else 0.0,
            "lente_asse_cil": int(rx_asse) if cilindro_significativo else None,
            "lente_add_d": round(rx_add, 2),
            "sottotipo": "Multifocale avanzata",
        }

    # ----------------
    if categoria == "RGP":
        rb = round(k_med - 0.05, 2)
        return {
            "lente_rb_mm": rb,
            "lente_bc_mm": rb,
            "lente_diam_mm": 9.60,
            "lente_potere_d": rx_sfera_eff,
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse) if cilindro_significativo else None,
            "sottotipo": "RGP dinamica",
        }

    # ----------------
    if categoria == "Ortho-K / Inversa":
        target = abs(rx_sfera)
        rb = round(k_med + (target * 0.1), 2)

        return {
            "lente_rb_mm": rb,
            "lente_bc_mm": rb,
            "lente_diam_mm": 10.60,
            "lente_potere_d": rx_sfera,
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse),
            "sottotipo": "Ortho-K evoluta",
        }

    return {
        "lente_bc_mm": 8.60,
        "lente_diam_mm": 14.20,
        "lente_potere_d": rx_sfera_eff,
        "lente_cilindro_d": round(rx_cil, 2),
        "lente_asse_cil": int(rx_asse),
        "sottotipo": "Custom",
    }


# ========================
# UI
# ========================

def ui_lenti_contatto():

    st.title("👁️ Lenti a contatto – modulo clinico")

    conn = _get_conn()

    st.subheader("Paziente")
    paziente_id = st.number_input("ID paziente", step=1)

    if not paziente_id:
        st.info("Inserisci ID paziente")
        return

    categoria = st.selectbox("Categoria", [
        "Morbida sferica",
        "Torica",
        "Multifocale / Presbiopia",
        "RGP",
        "Ortho-K / Inversa"
    ])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rx_sfera = st.number_input("Sfera", step=0.25)
    with col2:
        rx_cil = st.number_input("Cil", step=0.25)
    with col3:
        rx_asse = st.number_input("Asse", 0, 180)
    with col4:
        rx_add = st.number_input("ADD", step=0.25)

    k1 = st.number_input("K1", value=7.80)
    k2 = st.number_input("K2", value=7.90)
    hvid = st.number_input("HVID", value=11.8)

    if st.button("Calcola lente", use_container_width=True):

        risultato = _calcola_lente_base(
            categoria, rx_sfera, rx_cil, rx_asse, rx_add, k1, k2, hvid
        )

        st.success("Calcolo completato")

        st.json(risultato)
