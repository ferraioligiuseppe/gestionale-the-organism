# -*- coding: utf-8 -*-
"""UI del modulo Consensi Costellazioni Familiari (Streamlit)."""

from .pannello_paziente import render_pannello_consensi
from .form_firma import render_form_firma_click_studio
from .form_cartaceo import render_form_firma_cartaceo

__all__ = [
    "render_pannello_consensi",
    "render_form_firma_click_studio",
    "render_form_firma_cartaceo",
]
