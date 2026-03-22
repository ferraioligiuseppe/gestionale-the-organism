# -*- coding: utf-8 -*-
"""
Helper condiviso: conversione bidirezionale Raggio ↔ Potere (Diottrie)
Formula cheratometrica standard: D = 337.5 / r_mm  |  r_mm = 337.5 / D

Utilizzato in:
  - ui_lenti_inverse.py
  - ui_lac_ametropie.py
  - ui_calcolatore_lac.py
  - ui_esa_ortho6.py
  - ui_valutazioni_visive (cheratometria K1/K2) in app_core.py
"""

import streamlit as st

CK = 337.5  # Costante cheratometrica (indice n=1.3375)

def r_to_d(r_mm: float) -> float:
    """Raggio (mm) → Diottrie."""
    if r_mm and r_mm > 0:
        return round(CK / r_mm, 2)
    return 0.0

def d_to_r(d: float) -> float:
    """Diottrie → Raggio (mm)."""
    if d and d > 0:
        return round(CK / d, 3)
    return 0.0


def raggio_potere_widget(
    label_r: str,
    label_d: str,
    key_r: str,
    key_d: str,
    default_r: float = 7.80,
    min_r: float = 5.0,
    max_r: float = 14.0,
    step_r: float = 0.01,
    min_d: float = 20.0,
    max_d: float = 70.0,
    help_r: str = "",
    help_d: str = "",
    col_r=None,
    col_d=None,
) -> tuple[float, float]:
    """
    Mostra due number_input collegati raggio ↔ diottrie.
    Quando l'utente modifica uno, l'altro si aggiorna automaticamente
    tramite session_state on_change.

    Ritorna (raggio_mm, diottrie).
    """

    # Inizializza session_state se necessario
    if key_r not in st.session_state:
        st.session_state[key_r] = default_r
    if key_d not in st.session_state:
        st.session_state[key_d] = round(CK / default_r, 2)

    def _on_r_change():
        r = st.session_state[key_r]
        if r and r > 0:
            st.session_state[key_d] = round(CK / r, 2)

    def _on_d_change():
        d = st.session_state[key_d]
        if d and d > 0:
            st.session_state[key_r] = round(CK / d, 3)

    # Usa le colonne passate oppure crea inline
    if col_r is not None and col_d is not None:
        with col_r:
            r = st.number_input(
                label_r, min_value=min_r, max_value=max_r,
                step=step_r, format="%.2f",
                key=key_r, on_change=_on_r_change,
                help=help_r or f"Modifica → aggiorna {label_d} automaticamente",
            )
        with col_d:
            d = st.number_input(
                label_d, min_value=min_d, max_value=max_d,
                step=0.25, format="%.2f",
                key=key_d, on_change=_on_d_change,
                help=help_d or f"Modifica → aggiorna {label_r} automaticamente",
            )
    else:
        c1, c2 = st.columns(2)
        with c1:
            r = st.number_input(
                label_r, min_value=min_r, max_value=max_r,
                step=step_r, format="%.2f",
                key=key_r, on_change=_on_r_change,
                help=help_r or f"Modifica → aggiorna {label_d} automaticamente",
            )
        with c2:
            d = st.number_input(
                label_d, min_value=min_d, max_value=max_d,
                step=0.25, format="%.2f",
                key=key_d, on_change=_on_d_change,
                help=help_d or f"Modifica → aggiorna {label_r} automaticamente",
            )

    return r, d


def kera_widget_od_os(prefix: str, label: str = "K") -> dict:
    """
    Widget completo cheratometria OD e OS con conversione automatica.
    Ritorna dict con k1_od_mm, k1_od_D, k2_od_mm, k2_od_D,
                     k1_os_mm, k1_os_D, k2_os_mm, k2_os_D.
    """
    st.markdown(f"**{label} – Occhio Destro (ODx)**")
    c1, c2, c3, c4 = st.columns(4)

    # K1 OD
    if f"{prefix}_k1_od_mm" not in st.session_state:
        st.session_state[f"{prefix}_k1_od_mm"] = 7.80
        st.session_state[f"{prefix}_k1_od_D"]  = round(CK / 7.80, 2)
    if f"{prefix}_k2_od_mm" not in st.session_state:
        st.session_state[f"{prefix}_k2_od_mm"] = 7.70
        st.session_state[f"{prefix}_k2_od_D"]  = round(CK / 7.70, 2)

    def _k1_od_r(): st.session_state[f"{prefix}_k1_od_D"] = round(CK / st.session_state[f"{prefix}_k1_od_mm"], 2)
    def _k1_od_D(): st.session_state[f"{prefix}_k1_od_mm"] = round(CK / st.session_state[f"{prefix}_k1_od_D"], 3)
    def _k2_od_r(): st.session_state[f"{prefix}_k2_od_D"] = round(CK / st.session_state[f"{prefix}_k2_od_mm"], 2)
    def _k2_od_D(): st.session_state[f"{prefix}_k2_od_mm"] = round(CK / st.session_state[f"{prefix}_k2_od_D"], 3)

    with c1:
        k1_od_mm = st.number_input("K1 OD (mm)", 6.0, 9.5, step=0.01, format="%.2f",
            key=f"{prefix}_k1_od_mm", on_change=_k1_od_r)
    with c2:
        k1_od_D = st.number_input("K1 OD (D)", 35.0, 52.0, step=0.25, format="%.2f",
            key=f"{prefix}_k1_od_D", on_change=_k1_od_D)
    with c3:
        k2_od_mm = st.number_input("K2 OD (mm)", 6.0, 9.5, step=0.01, format="%.2f",
            key=f"{prefix}_k2_od_mm", on_change=_k2_od_r)
    with c4:
        k2_od_D = st.number_input("K2 OD (D)", 35.0, 52.0, step=0.25, format="%.2f",
            key=f"{prefix}_k2_od_D", on_change=_k2_od_D)

    st.markdown(f"**{label} – Occhio Sinistro (OSn)**")
    c5, c6, c7, c8 = st.columns(4)

    if f"{prefix}_k1_os_mm" not in st.session_state:
        st.session_state[f"{prefix}_k1_os_mm"] = 7.80
        st.session_state[f"{prefix}_k1_os_D"]  = round(CK / 7.80, 2)
    if f"{prefix}_k2_os_mm" not in st.session_state:
        st.session_state[f"{prefix}_k2_os_mm"] = 7.70
        st.session_state[f"{prefix}_k2_os_D"]  = round(CK / 7.70, 2)

    def _k1_os_r(): st.session_state[f"{prefix}_k1_os_D"] = round(CK / st.session_state[f"{prefix}_k1_os_mm"], 2)
    def _k1_os_D(): st.session_state[f"{prefix}_k1_os_mm"] = round(CK / st.session_state[f"{prefix}_k1_os_D"], 3)
    def _k2_os_r(): st.session_state[f"{prefix}_k2_os_D"] = round(CK / st.session_state[f"{prefix}_k2_os_mm"], 2)
    def _k2_os_D(): st.session_state[f"{prefix}_k2_os_mm"] = round(CK / st.session_state[f"{prefix}_k2_os_D"], 3)

    with c5:
        k1_os_mm = st.number_input("K1 OS (mm)", 6.0, 9.5, step=0.01, format="%.2f",
            key=f"{prefix}_k1_os_mm", on_change=_k1_os_r)
    with c6:
        k1_os_D = st.number_input("K1 OS (D)", 35.0, 52.0, step=0.25, format="%.2f",
            key=f"{prefix}_k1_os_D", on_change=_k1_os_D)
    with c7:
        k2_os_mm = st.number_input("K2 OS (mm)", 6.0, 9.5, step=0.01, format="%.2f",
            key=f"{prefix}_k2_os_mm", on_change=_k2_os_r)
    with c8:
        k2_os_D = st.number_input("K2 OS (D)", 35.0, 52.0, step=0.25, format="%.2f",
            key=f"{prefix}_k2_os_D", on_change=_k2_os_D)

    # Mostra astigmatismo corneale calcolato
    ast_od = abs(k1_od_D - k2_od_D)
    ast_os = abs(k1_os_D - k2_os_D)
    if ast_od > 0.1 or ast_os > 0.1:
        st.caption(
            f"Astigmatismo corneale → OD: **{ast_od:.2f} D** | OS: **{ast_os:.2f} D**"
        )

    return {
        "k1_od_mm": k1_od_mm, "k1_od_D": k1_od_D,
        "k2_od_mm": k2_od_mm, "k2_od_D": k2_od_D,
        "k1_os_mm": k1_os_mm, "k1_os_D": k1_os_D,
        "k2_os_mm": k2_os_mm, "k2_os_D": k2_os_D,
    }
