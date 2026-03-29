from __future__ import annotations


def _src():
    from modules import ui_lenti_contatto as src
    return src


def plot_fluorescein_simulation(proposta: dict, title: str = ""):
    return _src()._plot_fluorescein_simulation(proposta, title=title)
