"""Pacchetto LAC modulare — step 1 safe.
Bridge modules che riusano il codice già presente in modules.ui_lenti_contatto.
"""

from .lac_engine import (
    ESA_DATA,
    esa_lookup,
    toffoli_calc,
    hyperopia_calc,
    astig_calc,
    presbyopia_calc,
    estimate_clearance,
)

from .lac_decision import build_curves
from .lac_topography import parse_xyz_file, parse_csv_topographer, parse_zcs_file, parse_any_topo
from .lac_fluoro import plot_fluorescein_simulation
from .lac_storage import get_conn, init_db, build_payload, load_storico_paziente
