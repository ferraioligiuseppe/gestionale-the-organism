# -*- coding: utf-8 -*-
"""Entry point modulare della sezione Pazienti.

Step 6 safe: il router non passa più callback dal file centrale.
Il modulo importa in modo lazy la funzione storica da app_core,
così il comportamento resta invariato ma le dipendenze sono più pulite.
"""

def render_pazienti_section(*args, **kwargs):
    from app_core import ui_pazienti
    return ui_pazienti(*args, **kwargs)
