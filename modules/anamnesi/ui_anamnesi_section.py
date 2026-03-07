# -*- coding: utf-8 -*-
"""Entry point modulare della sezione Anamnesi / Valutazione PNEV.

Step 6 safe: il router richiama direttamente il modulo dedicato,
senza più passare callback dal file centrale.
"""

def render_anamnesi_section(*args, **kwargs):
    from app_core import ui_anamnesi
    return ui_anamnesi(*args, **kwargs)
