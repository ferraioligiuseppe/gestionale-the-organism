# -*- coding: utf-8 -*-
"""
Modulo INPP — Valutazione Diagnostica dello Sviluppo Neurologico
Studio The Organism — gestionale.

Struttura:
- protocollo.py  : definizione data-driven delle 10 sezioni e delle ~150 prove
- db_inpp.py     : layer database (schema + CRUD)
- ui_inpp.py     : UI Streamlit (lista valutazioni + editor + tab per sezione)
- pdf_inpp.py    : generatore PDF referto

Entry point dal router: ui_inpp.render_inpp(conn, paziente_id, paziente_nome).
"""

from .ui_inpp import render_inpp  # re-export comodo

__all__ = ["render_inpp"]
