# -*- coding: utf-8 -*-
"""Routing principale delle sezioni non uditive.

Step 6 safe: il router richiama i moduli dedicati e non dipende più da una
lunga lista di callback passati da app_core. Questo riduce il rischio di
errori quando si modifica il file centrale.
"""

from typing import Callable, Any
from .app_sections import (
    SECTION_PAZIENTI,
    SECTION_PNEV,
    SECTION_VISION,
    SECTION_SEDUTE,
    SECTION_OSTEOPATIA,
    SECTION_COUPON,
    SECTION_DASHBOARD,
    SECTION_RELAZIONI,
    SECTION_EVOLUTIVA,
    SECTION_PRIVACY,
    SECTION_DEBUG,
    SECTION_IMPORT,
    SECTION_UTENTI,
)
from .pazienti import render_pazienti_section
from .anamnesi import render_anamnesi_section
from .privacy import render_privacy_section
from .pnev import render_pnev_section
from .sections import (
    render_vision_section,
    render_sedute_section,
    render_osteopatia_section,
    render_coupon_section,
    render_dashboard_section,
    render_relazioni_section,
    render_evolutiva_section,
    render_debug_section,
    render_import_section,
    render_utenti_section,
)


def dispatch_main_section(*, sezione: str, get_connection: Callable[..., Any]) -> bool:
    if sezione == SECTION_PAZIENTI:
        render_pazienti_section()
        return True
    if sezione == SECTION_PNEV:
        render_pnev_section()
        return True
    if sezione == SECTION_VISION:
        render_vision_section()
        return True
    if sezione == SECTION_SEDUTE:
        render_sedute_section()
        return True
    if sezione == SECTION_OSTEOPATIA:
        render_osteopatia_section()
        return True
    if sezione == SECTION_COUPON:
        render_coupon_section()
        return True
    if sezione == SECTION_DASHBOARD:
        render_dashboard_section()
        return True
    if sezione == SECTION_RELAZIONI:
        render_relazioni_section()
        return True
    if sezione == SECTION_EVOLUTIVA:
        render_evolutiva_section()
        return True
    if sezione == SECTION_PRIVACY:
        render_privacy_section()
        return True
    if sezione == SECTION_DEBUG:
        render_debug_section()
        return True
    if sezione == SECTION_IMPORT:
        render_import_section()
        return True
    if sezione == SECTION_UTENTI:
        render_utenti_section(get_connection)
        return True
    return False
