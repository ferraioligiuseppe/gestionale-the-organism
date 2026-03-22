# -*- coding: utf-8 -*-
"""Compatibility shim: importa dal modulo canonico in modules/."""
from modules.schema_manager import (  # noqa: F401
    ensure_all_schemas,
    ensure_auth_schema,
    ensure_core_schema,
    ensure_vision_schema,
    ensure_osteo_schema,
)
