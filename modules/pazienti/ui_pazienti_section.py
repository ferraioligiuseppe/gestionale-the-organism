# -*- coding: utf-8 -*-
"""Entry point modulare della sezione Pazienti.

Step 3 safe: non sposta ancora la logica clinica interna da app_core,
ma centralizza il punto di ingresso in un modulo dedicato per evitare che
il routing principale dipenda direttamente dalle funzioni storiche.
"""

from typing import Callable, Any


def render_pazienti_section(ui_pazienti: Callable[..., Any]) -> Any:
    return ui_pazienti()
