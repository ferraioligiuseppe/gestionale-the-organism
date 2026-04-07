# -*- coding: utf-8 -*-
"""Routing principale delle sezioni non uditive."""

from typing import Callable, Any

import streamlit as st

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
    SECTION_GAZE,
    SECTION_READING_DOM,
    SECTION_UTENTI,
)
from .pazienti import render_pazienti_section
from .anamnesi import render_anamnesi_section
from .privacy.ui_privacy_section import render_privacy_section
from .pnev.ui_pnev import render_pnev_section
from .sections.ui_cliniche import (
    render_vision_section,
    render_sedute_section,
    render_osteopatia_section,
    render_coupon_section,
    render_dashboard_section,
    render_relazioni_section,
    render_evolutiva_section,
    render_debug_section,
    render_import_section,
    render_gaze_section,
    render_utenti_section,
)
from .ui_lenti_contatto import ui_lenti_contatto

SECTION_LENTI_CONTATTO = "👁️ Lenti a contatto"
SECTION_PHOTOREF = "📸 Photoref AI"


def dispatch_main_section(*, sezione: str, get_connection: Callable[..., Any]) -> bool:
    photoref_token = st.query_params.get("photoref_token", "")
    if isinstance(photoref_token, list):
        photoref_token = photoref_token[0] if photoref_token else ""

    if photoref_token:
        try:
            from .photoref_ai.ui_photoref_mobile import ui_photoref_mobile
            ui_photoref_mobile(conn=get_connection())
        except Exception as e:
            st.error("Modulo Photoref Mobile non disponibile.")
            st.exception(e)
        return True

    if sezione == SECTION_PAZIENTI:
        render_pazienti_section()
        return True

    if sezione == SECTION_PNEV:
        render_pnev_section()
        return True

    if sezione == SECTION_VISION:
        render_vision_section()
        return True

    if sezione == SECTION_LENTI_CONTATTO:
        ui_lenti_contatto()
        return True

    if sezione == SECTION_PHOTOREF:
        try:
            from .photoref_ai.ui_photoref import ui_photoref
            ui_photoref()
        except Exception as e:
            st.error("Modulo Photoref AI non disponibile.")
            st.exception(e)
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

    if sezione == SECTION_GAZE:
        render_gaze_section()
        return True

    if sezione == SECTION_READING_DOM:
        try:
            from .reading.ui_reading_dom import ui_reading_dom
        except Exception as e:
            st.error("Modulo Lettura Avanzata DOM non disponibile.")
            st.exception(e)
            st.info(
                "Verifica che nella repo esistano i file di modules/reading "
                "e che la dipendenza streamlit-javascript sia installata."
            )
            return True

        ui_reading_dom()
        return True

    if sezione == SECTION_UTENTI:
        render_utenti_section(get_connection)
        return True

    return False
