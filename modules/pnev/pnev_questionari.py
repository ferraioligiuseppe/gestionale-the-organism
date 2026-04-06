# -*- coding: utf-8 -*-
"""Wrapper per questionari pubblici e link tokenizzati."""

def render_public_questionario_if_needed(*args, **kwargs):
    from modules.app_core import maybe_handle_public_questionario
    return maybe_handle_public_questionario(*args, **kwargs)
