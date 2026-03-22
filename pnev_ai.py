# -*- coding: utf-8 -*-
"""Compatibility shim: importa dal modulo canonico in modules/."""
from modules.pnev_ai import (  # noqa: F401
    generate_hypothesis,
    generate_plan,
    apply_to_session,
)
