# -*- coding: utf-8 -*-
"""
Modulo PECS - Picture Exchange Communication System
Gestionale Studio The Organism

    from modules.pecs import ui_pecs
    ui_pecs.render()

Prima esecuzione (una tantum, per creare le tabelle):

    from modules.pecs import db_pecs
    db_pecs.inizializza_schema()
"""

__all__ = ["db_pecs", "ui_pecs", "pdf_pecs", "pecs_contenuti"]
__version__ = "1.0.0"
