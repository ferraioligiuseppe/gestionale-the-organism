# -*- coding: utf-8 -*-
"""Entry point modulare canonico per referti / relazioni cliniche."""

def render_referti_section(*args, **kwargs):
    from modules.app_core import ui_relazioni_cliniche
    return ui_relazioni_cliniche(*args, **kwargs)
