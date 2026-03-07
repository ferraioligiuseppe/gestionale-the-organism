# -*- coding: utf-8 -*-
"""Wrapper sicuri per l'area Privacy / Consensi.

Step 5: separazione architetturale senza modificare il comportamento esistente.
"""

from .ui_privacy import render_privacy_section
from .sign_page import render_public_sign_page
from .pdf_privacy import privacy_templates_info

__all__ = [
    "render_privacy_section",
    "render_public_sign_page",
    "privacy_templates_info",
]
