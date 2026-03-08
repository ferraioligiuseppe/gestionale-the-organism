# -*- coding: utf-8 -*-
"""Entry point modulare per la sezione Pazienti.

Step 7 safe: punto di accesso canonico del modulo Pazienti.
La logica clinica resta ancora in app_core, ma da qui in avanti gli import
esterni possono puntare a questo file stabile.
"""

def render_pazienti_section(*args, **kwargs):
    from app_core import ui_pazienti
    return ui_pazienti(*args, **kwargs)
