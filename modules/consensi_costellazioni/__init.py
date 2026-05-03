# -*- coding: utf-8 -*-
"""
Modulo Consensi Costellazioni Familiari.

Roadmap completata:
- F1 ✓ db_schema + seeder
- F2 ✓ services (firma, revoca, validazione, token)
- F3 ✓ pdf_generator
- F4 ✓ ui/pannello_paziente
- F5 ✓ ui/form_firma (click_studio)
- F6 ✓ ui/form_cartaceo
- F7 ✓ pages/firma_consenso_pubblico.py (link_paziente)

Esempio integrazione minima nel gestionale:

    # In modules/schema_manager.py
    from modules.consensi_costellazioni.db_schema import apply_schema as _apply_cf
    def ensure_consensi_costellazioni_schema(conn, backend="postgres"):
        _apply_cf(conn, db_backend=backend)
    # E aggiungi alla lista di ensure_all_schemas

    # Nella scheda paziente del gestionale:
    from modules.consensi_costellazioni.ui import render_pannello_consensi
    render_pannello_consensi(paziente_id, paziente_nome)

    # Seed una tantum (in sezione admin):
    from modules.consensi_costellazioni.seeders.costellazioni import seed_template
    seed_template(conn, percorso_md="docs/consensi_costellazioni.md")
"""

__version__ = "1.0.0-mvp-completo"

# F1
from .db_schema import apply_schema, drop_schema, init_db_hook

# F2
from .services import (
    firma_consenso,
    revoca_consenso,
    rinnova_consenso,
    consensi_attivi_paziente,
    firma_attiva_per_codice,
    template_attivo_per_codice,
    template_per_id,
    verifica_consensi_richiesti,
    AZIONI_CONSENSI_RICHIESTI,
    crea_token_firma,
    valida_token_firma,
    VoceValidationError,
)

# F3
from .pdf_generator import (
    genera_pdf_consenso,
    genera_pdf_revoca,
)

__all__ = [
    # F1
    "apply_schema",
    "drop_schema",
    "init_db_hook",
    # F2
    "firma_consenso",
    "revoca_consenso",
    "rinnova_consenso",
    "consensi_attivi_paziente",
    "firma_attiva_per_codice",
    "template_attivo_per_codice",
    "template_per_id",
    "verifica_consensi_richiesti",
    "AZIONI_CONSENSI_RICHIESTI",
    "crea_token_firma",
    "valida_token_firma",
    "VoceValidationError",
    # F3
    "genera_pdf_consenso",
    "genera_pdf_revoca",
]
