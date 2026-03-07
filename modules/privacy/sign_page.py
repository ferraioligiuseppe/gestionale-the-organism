# -*- coding: utf-8 -*-
"""Entry point modulare per la pagina pubblica firma online."""

def render_public_sign_page(*args, **kwargs):
    from app_core import ui_public_sign_page
    return ui_public_sign_page(*args, **kwargs)
