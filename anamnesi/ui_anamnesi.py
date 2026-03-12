# -*- coding: utf-8 -*-
"""Entry point modulare per la sezione Anamnesi / Valutazione PNEV.

Step 7 safe: punto di accesso canonico del modulo Anamnesi.
"""

def render_anamnesi_section(*args, **kwargs):
    from app_core import ui_anamnesi
    return ui_anamnesi(*args, **kwargs)
