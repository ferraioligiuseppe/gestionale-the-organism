# -*- coding: utf-8 -*-
"""Compatibility shim: importa dal modulo canonico in modules/."""
from modules.pnev_module import (  # noqa: F401
    pnev_default,
    pnev_load,
    pnev_dump,
    pnev_pack_visita,
    pnev_collect_ui,
    pnev_summary_from_json,
)
