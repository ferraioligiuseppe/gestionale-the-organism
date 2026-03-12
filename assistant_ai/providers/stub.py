from __future__ import annotations
from typing import Any, Dict

def load_dataset_stub(nome_modulo: str) -> Dict[str, Any]:
    return {
        nome_modulo: {
            "nota": f"Provider '{nome_modulo}' non ancora collegato allo schema del tuo gestionale. Dimmi tabelle/colonne e lo aggancio.",
            "dati": None,
        }
    }
