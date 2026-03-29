from __future__ import annotations
from typing import Any, Dict


def _src():
    from modules import ui_lenti_contatto as src
    return src


def build_curves(
    categoria,
    difetto,
    algoritmo,
    modello_prod,
    rx_sfera,
    rx_cil,
    rx_asse,
    rx_add,
    k1,
    k2,
    hvid,
    pupilla,
    target_orthok,
    e_val,
) -> Dict[str, Any]:
    src = _src()
    res = src._build_curves(
        categoria,
        difetto,
        algoritmo,
        modello_prod,
        rx_sfera,
        rx_cil,
        rx_asse,
        rx_add,
        k1,
        k2,
        hvid,
        pupilla,
        target_orthok,
        e_val,
    )
    return dict(res) if isinstance(res, dict) else res
