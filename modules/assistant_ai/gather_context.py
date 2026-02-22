from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List

from .providers.osteopatia import load_osteopatia_dataset
from .providers.generic import load_generic_dataset, load_single_row

# Sorgenti REALI rilevate dal tuo DB (public schema)
AVAILABLE_SOURCES = [
    ("Osteopatia (auto)", "osteopatia"),
    ("Anamnesi (generale)", "anamnesi"),
    ("Sedute (generale)", "sedute"),
    ("Valutazioni visive", "valutazioni_visive"),
    ("Relazioni cliniche", "relazioni_cliniche"),
    ("Documenti (metadati)", "documenti"),
    ("Consensi privacy", "consensi_privacy"),
]

def gather_dataset(conn, paziente_id: int, date_from: dt.date, date_to: dt.date, sources: List[str], include_deleted: bool = False) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "fonte": "Gestionale The Organism",
        "paziente_id": paziente_id,
        "periodo": f"{date_from} → {date_to}",
        "sezioni": {},
    }

    if "osteopatia" in sources:
        data["sezioni"].update(load_osteopatia_dataset(conn, paziente_id, date_from, date_to, include_deleted=include_deleted))

    if "anamnesi" in sources:
        data["sezioni"].update(load_generic_dataset(conn, "anamnesi", paziente_id, date_from, date_to, include_deleted=include_deleted))

    if "sedute" in sources:
        data["sezioni"].update(load_generic_dataset(conn, "sedute", paziente_id, date_from, date_to, include_deleted=include_deleted))

    if "valutazioni_visive" in sources:
        data["sezioni"].update(load_generic_dataset(conn, "valutazioni_visive", paziente_id, date_from, date_to, include_deleted=include_deleted))

    if "relazioni_cliniche" in sources:
        data["sezioni"].update(load_generic_dataset(conn, "relazioni_cliniche", paziente_id, date_from, date_to, include_deleted=include_deleted))

    if "documenti" in sources:
        data["sezioni"].update(load_generic_dataset(conn, "documenti", paziente_id, date_from, date_to, include_deleted=include_deleted, limit=100))

    if "consensi_privacy" in sources:
        # spesso basta l'ultimo consenso
        data["sezioni"].update(load_single_row(conn, "consensi_privacy", paziente_id, include_deleted=include_deleted))

    return data
