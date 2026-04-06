# -*- coding: utf-8 -*-
"""Raccolta di wrapper clinici rimasti in app_core.

Step 7 safe: centralizza in un file dedicato i wrapper di sezioni storiche,
così app_main_router resta più leggibile e gli accessi futuri sono uniformi.
"""

def render_vision_section(*args, **kwargs):
    from modules.app_core import ui_valutazioni_visive
    return ui_valutazioni_visive(*args, **kwargs)


def render_sedute_section(*args, **kwargs):
    from modules.app_core import ui_sedute
    return ui_sedute(*args, **kwargs)


def render_osteopatia_section(*args, **kwargs):
    from modules.app_core import ui_osteopatia_section
    return ui_osteopatia_section(*args, **kwargs)


def render_coupon_section(*args, **kwargs):
    from modules.app_core import ui_coupons
    return ui_coupons(*args, **kwargs)


def render_dashboard_section(*args, **kwargs):
    from modules.app_core import ui_dashboard
    return ui_dashboard(*args, **kwargs)


def render_relazioni_section(*args, **kwargs):
    from modules.referti.ui_referti_section import render_referti_section
    return render_referti_section(*args, **kwargs)


def render_evolutiva_section(*args, **kwargs):
    from modules.app_core import ui_dashboard_evolutiva
    return ui_dashboard_evolutiva(*args, **kwargs)


def render_debug_section(*args, **kwargs):
    from modules.app_core import ui_debug_db
    return ui_debug_db(*args, **kwargs)


def render_import_section(*args, **kwargs):
    from modules.app_core import ui_import_pazienti
    return ui_import_pazienti(*args, **kwargs)


def render_utenti_section(get_connection, *args, **kwargs):
    from modules.app_core import ui_gestione_utenti
    return ui_gestione_utenti(get_connection, *args, **kwargs)


def render_gaze_section(*args, **kwargs):
    from modules.app_core import ui_gaze_tracking_section
    return ui_gaze_tracking_section(*args, **kwargs)
