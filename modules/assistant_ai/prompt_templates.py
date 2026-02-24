from __future__ import annotations
from typing import Dict, Any, List

PROFESSIONALI = [
    "Osteopata",
    "Psicologo/Psicoterapeuta",
    "Optometrista/Visione",
    "Logopedista",
    "Neuropsicomotricista",
    "Fisioterapista",
    "Altro",
]

def build_system_instructions(professionista: str) -> str:
    return f"""
Sei un assistente clinico per la redazione di relazioni professionali in italiano.
Stai scrivendo per: {professionista}.
Regole:
- Stile: chiaro, professionale, sintetico ma completo.
- Non inventare dati: usa SOLO i campi forniti.
- Se mancano dati, segnala "Dato non disponibile".
- Rispetta la privacy: non includere dati identificativi se non presenti nel prompt.
- Output: JSON conforme allo schema richiesto.
""".strip()

def build_user_prompt(
    professionista: str,
    paziente_label: str,
    contesto: Dict[str, Any],
    anamnesi: Dict[str, Any] | None,
    sedute: List[Dict[str, Any]],
    note_libere: str = "",
) -> str:
    return f"""
PROFESSIONISTA: {professionista}
PAZIENTE: {paziente_label}

DATI/CONTESTO (dal gestionale):
{contesto}

ANAMNESI (se presente):
{anamnesi if anamnesi else "Nessuna anamnesi selezionata."}

SEDUTE (lista):
{sedute if sedute else "Nessuna seduta nel periodo."}

NOTE AGGIUNTIVE (facoltative):
{note_libere if note_libere else "-"}

OBIETTIVO:
Genera una relazione personalizzata per il professionista indicato, con:
- Sintesi problema / domanda
- Valutazione iniziale (se presente)
- Intervento/percorsi (sedute) con progressione
- Risultati / osservazioni
- Indicazioni e raccomandazioni
- Piano proposto / follow-up

Ricorda: NON aggiungere diagnosi mediche se non presenti nei dati.
""".strip()

def relazione_schema() -> Dict[str, Any]:
    return {
        "name": "relazione_clinica",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "titolo": {"type": "string"},
                "professionista": {"type": "string"},
                "paziente": {"type": "string"},
                "periodo": {"type": "string"},
                "sintesi": {"type": "string"},
                "valutazione_iniziale": {"type": "string"},
                "intervento_e_progressione": {"type": "string"},
                "risultati": {"type": "string"},
                "indicazioni": {"type": "string"},
                "piano_followup": {"type": "string"},
                "avvertenze": {"type": "string"},
            },
            "required": [
                "titolo","professionista","paziente","periodo","sintesi",
                "valutazione_iniziale","intervento_e_progressione","risultati",
                "indicazioni","piano_followup","avvertenze"
            ],
        },
        "strict": True,
    }
