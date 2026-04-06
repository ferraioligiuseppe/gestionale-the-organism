# -*- coding: utf-8 -*-
"""Entry point modulare canonico per la sezione Privacy."""

def render_privacy_section(*args, **kwargs):
    from modules.app_core import ui_privacy_pdf
    return ui_privacy_pdf(*args, **kwargs)
