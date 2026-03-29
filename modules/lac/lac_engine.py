from __future__ import annotations
from typing import Any, Dict


def _src():
    from modules import ui_lenti_contatto as src
    return src


def _clone_dict(d: dict | None) -> dict:
    return dict(d) if isinstance(d, dict) else {}


@property
def ESA_DATA() -> dict:
    return _src().ESA_DATA


def get_esa_data() -> dict:
    return dict(_src().ESA_DATA)


def esa_lookup(k_med: float, power_abs: float) -> Dict[str, Any] | None:
    res = _src().esa_lookup_self(k_med, power_abs)
    return _clone_dict(res) if res else None


def toffoli_calc(k_med: float, target_myopia: float) -> Dict[str, Any]:
    return _clone_dict(_src().toffoli_calc_self(k_med, target_myopia))


def hyperopia_calc(k_med: float, hyper_d: float) -> Dict[str, Any]:
    return _clone_dict(_src().hyperopia_calc_self(k_med, hyper_d))


def astig_calc(k_flat: float, k_steep: float, cyl: float) -> Dict[str, Any]:
    return _clone_dict(_src().astig_calc_self(k_flat, k_steep, cyl))


def presbyopia_calc(k_med: float, add_d: float) -> Dict[str, Any]:
    return _clone_dict(_src().presbyopia_calc_self(k_med, add_d))


def estimate_clearance(k_med: float, ordine: dict, design: str) -> Dict[str, Any]:
    return _clone_dict(_src()._estimate_clearance(k_med, ordine, design))
