# -*- coding: utf-8 -*-
"""Compatibility shim: importa dal modulo canonico in modules/."""
from modules.letterhead_pdf import (  # noqa: F401
    make_overlay_pdf,
    merge_overlay_on_template,
    build_pdf_with_letterhead,
)
