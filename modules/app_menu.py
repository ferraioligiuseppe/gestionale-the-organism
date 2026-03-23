# -*- coding: utf-8 -*-
"""Menu principale del gestionale."""

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

def build_sections(is_admin: bool, app_mode: str) -> list[str]:
    sections = list(BASE_SECTIONS)
    if is_admin:
        sections.extend(ADMIN_SECTIONS)
    return sections
