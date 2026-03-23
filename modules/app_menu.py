# -*- coding: utf-8 -*-
"""Menu principale del gestionale.

Step 1-2 della modularizzazione: qui vivono le definizioni delle voci sidebar,
riusando costanti condivise con il routing.
"""

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

BASE_SECTIONS = [
    SECTION_DASHBOARD,
    SECTION_PAZIENTI,
    SECTION_PNEV,
    SECTION_VISION,
    SECTION_READING_DOM,
    SECTION_SEDUTE,
    SECTION_OSTEOPATIA,
    SECTION_COUPON,
    SECTION_RELAZIONI,
    SECTION_EVOLUTIVA,
    SECTION_PRIVACY,
    SECTION_DEBUG,
    SECTION_IMPORT,
    SECTION_GAZE,
]

ADMIN_SECTIONS = [
    SECTION_UTENTI,
]


UDITO_PROD_SECTIONS = [
    "🎧 ORL + EQ (MODULO)",
    "🎧 Genera stimolazione (JOB)",
    "🎧 Stimolazione uditiva (TEST)",
]

UDITO_TEST_ONLY_SECTIONS = [
    "🔧 Calibrazione cuffie",
    "🎧 Audiogramma funzionale (TEST)",
    "🩺 Esami ORL – soglie tonali (TEST)",
    "🎚️ EQ stimolazione uditiva (TEST)",
    "🔧 Calibrazione cuffie (TEST)",
    "🧹 Pulizia DB (TEST)",
]


def build_sections(is_admin: bool, app_mode: str) -> list[str]:
    sections = list(BASE_SECTIONS)
    if is_admin:
        sections.extend(ADMIN_SECTIONS)
    sections.extend(UDITO_PROD_SECTIONS)
    if str(app_mode).lower().strip() == "test":
        sections.extend(UDITO_TEST_ONLY_SECTIONS)
    return sections
