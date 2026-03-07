# -*- coding: utf-8 -*-
"""Entry point modulare per la sezione Valutazione PNEV."""

def render_pnev_section(*args, **kwargs):
    from app_core import ui_anamnesi
    return ui_anamnesi(*args, **kwargs)
