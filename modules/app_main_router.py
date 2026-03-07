# -*- coding: utf-8 -*-
"""Routing principale delle sezioni non uditive.

Step 2 della modularizzazione: il menu generale non vive più in app_core.
Qui passiamo solo callback, così il comportamento resta invariato ma il file
centrale diventa più sicuro da modificare.
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


def dispatch_main_section(
    *,
    sezione: str,
    get_connection: Callable[..., Any],
    ui_pazienti: Callable[..., Any],
    ui_anamnesi: Callable[..., Any],
    ui_valutazioni_visive: Callable[..., Any],
    ui_sedute: Callable[..., Any],
    ui_osteopatia_section: Callable[..., Any],
    ui_coupons: Callable[..., Any],
    ui_dashboard: Callable[..., Any],
    ui_relazioni_cliniche: Callable[..., Any],
    ui_dashboard_evolutiva: Callable[..., Any],
    ui_privacy_pdf: Callable[..., Any],
    ui_debug_db: Callable[..., Any],
    ui_import_pazienti: Callable[..., Any],
    ui_gestione_utenti: Callable[..., Any],
) -> bool:
    if sezione == SECTION_PAZIENTI:
        ui_pazienti()
        return True
    if sezione == SECTION_PNEV:
        ui_anamnesi()
        return True
    if sezione == SECTION_VISION:
        ui_valutazioni_visive()
        return True
    if sezione == SECTION_SEDUTE:
        ui_sedute()
        return True
    if sezione == SECTION_OSTEOPATIA:
        ui_osteopatia_section()
        return True
    if sezione == SECTION_COUPON:
        ui_coupons()
        return True
    if sezione == SECTION_DASHBOARD:
        ui_dashboard()
        return True
    if sezione == SECTION_RELAZIONI:
        ui_relazioni_cliniche()
        return True
    if sezione == SECTION_EVOLUTIVA:
        ui_dashboard_evolutiva()
        return True
    if sezione == SECTION_PRIVACY:
        ui_privacy_pdf()
        return True
    if sezione == SECTION_DEBUG:
        ui_debug_db()
        return True
    if sezione == SECTION_IMPORT:
        ui_import_pazienti()
        return True
    if sezione == SECTION_UTENTI:
        ui_gestione_utenti(get_connection)
        return True
    return False
