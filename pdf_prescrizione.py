# -*- coding: utf-8 -*-
"""Entry point modulare canonico per area PNEV / questionari."""

def render_pnev_section(*args, **kwargs):
    from app_core import ui_anamnesi
    return ui_anamnesi(*args, **kwargs)
