# -*- coding: utf-8 -*-
"""Compatibility shim: importa dal modulo canonico in modules/."""
from modules.db_jobs import (  # noqa: F401
    ensure_jobs_schema,
    seed_tomatis_presets,
)
