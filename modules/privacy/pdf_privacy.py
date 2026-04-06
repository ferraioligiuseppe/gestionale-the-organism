# -*- coding: utf-8 -*-
"""Helper modulari per template privacy.

Non sposta ancora la logica dal core: reindirizza in modo sicuro.
"""

def privacy_templates_info():
    from modules.app_core import (
        PDF_PRIVACY_ADULTO_TEMPLATE,
        PDF_PRIVACY_MINORE_TEMPLATE,
        PDF_PRIVACY_ADULTO_SIGN_TEMPLATE,
        PDF_PRIVACY_MINORE_SIGN_TEMPLATE,
    )
    return {
        "adulto_stampabile": PDF_PRIVACY_ADULTO_TEMPLATE,
        "minore_stampabile": PDF_PRIVACY_MINORE_TEMPLATE,
        "adulto_firma_online": PDF_PRIVACY_ADULTO_SIGN_TEMPLATE,
        "minore_firma_online": PDF_PRIVACY_MINORE_SIGN_TEMPLATE,
    }

def resolve_privacy_path(path: str) -> str:
    from modules.app_core import _privacy_abs_path
    return _privacy_abs_path(path)

def check_privacy_templates_ui():
    from modules.app_core import _check_privacy_templates_ui
    return _check_privacy_templates_ui()
