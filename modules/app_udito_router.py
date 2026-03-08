# -*- coding: utf-8 -*-
"""Routing dedicato ai moduli uditivi."""

from typing import Callable, Any

SECTION_ORL_EQ = "🎧 ORL + EQ (MODULO)"
SECTION_GENERA = "🎧 Genera stimolazione (JOB)"
SECTION_STIM = "🎧 Stimolazione uditiva"
SECTION_AUDIOGRAMMA = "🎧 Audiogramma funzionale"
SECTION_ESAMI_ORL = "🩺 Esami ORL – soglie tonali"
SECTION_EQ_TEST = "🎚️ EQ stimolazione uditiva"
SECTION_CALIB = "🔧 Calibrazione cuffie"
SECTION_CLEANUP = "🧹 Pulizia DB (TEST)"


def dispatch_udito_section(
    *,
    sezione: str,
    app_mode: str,
    get_connection: Callable[..., Any],
    paziente_selector_fn: Callable[..., Any],
    ui_orl_eq: Callable[..., Any],
    ui_generatore_stimolazione: Callable[..., Any],
    ui_sessione_stimolazione_uditiva_test: Callable[..., Any],
    ui_audiogramma_test: Callable[..., Any],
    ui_esami_orl_tonali_test: Callable[..., Any],
    ui_eq_stimolazione_uditiva_test: Callable[..., Any],
    ui_calibrazione_cuffie_test: Callable[..., Any],
    ui_db_cleanup: Callable[..., Any],
) -> bool:
    if sezione == SECTION_ORL_EQ:
        ui_orl_eq(get_connection, paziente_selector_fn=paziente_selector_fn)
        return True

    if sezione == SECTION_GENERA:
        ui_generatore_stimolazione(get_connection, paziente_selector_fn=paziente_selector_fn)
        return True

    if sezione == SECTION_STIM:
        ui_sessione_stimolazione_uditiva_test()
        return True

    if sezione == SECTION_AUDIOGRAMMA:
        ui_audiogramma_test()
        return True

    if sezione == SECTION_ESAMI_ORL:
        ui_esami_orl_tonali_test()
        return True

    if sezione == SECTION_EQ_TEST:
        ui_eq_stimolazione_uditiva_test()
        return True

    if sezione == SECTION_CALIB:
        ui_calibrazione_cuffie_test()
        return True

    if sezione == SECTION_CLEANUP:
        if str(app_mode).lower().strip() == "test":
            ui_db_cleanup()
            return True
        return False

    return False
