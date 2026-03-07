# -*- coding: utf-8 -*-
"""Entry point modulare della sezione Anamnesi / Valutazione PNEV.

Step 3 safe: il contenuto resta in app_core, ma il punto di accesso viene
stabilizzato in un modulo dedicato, così i prossimi step potranno spostare
la logica interna senza rompere il router principale.
"""

from typing import Callable, Any


def render_anamnesi_section(ui_anamnesi: Callable[..., Any]) -> Any:
    return ui_anamnesi()
