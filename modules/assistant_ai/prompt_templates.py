from __future__ import annotations
from typing import Dict, Any, List

# elenco esteso (puoi aggiungerne quanti vuoi)
PROFESSIONALI = [
    "Osteopata",
    "Psicologo/Psicoterapeuta",
    "Optometrista/Visione",
    "Logopedista",
    "Neuropsicomotricista",
    "Fisioterapista",
    "Terapista occupazionale",
    "Dietista/Nutrizionista",
    "Medico",
    "Educatore",
    "Tutor DSA",
    "Optometrista Comportamentale / VVF",
    "Neuropsicomotricista / PNEV",
    "Altro (custom)",
]

# profili di scrittura per professione (tono/struttura)
PROFILI = {
    "Osteopata": {"tone": "clinico-sintetico", "focus": "dolore, funzionalità, risposta al trattamento"},
    "Optometrista Comportamentale / VVF": {
        "tone": "tecnico-funzionale",
        "focus": "risultati batteria visiva, diagnosi funzionale, piano Vision Therapy, indicazioni",
    },
    "Neuropsicomotricista / PNEV": {
        "tone": "neuroevolutivo-integrato",
        "focus": "profilo PNEV, immaturità neuromotoria, riflessologia primitiva, obiettivi terapeutici",
    },
    "Psicologo/Psicoterapeuta": {"tone": "clinico-relazionale", "focus": "funzionamento, obiettivi, progressi"},
    "Optometrista/Visione": {"tone": "tecnico", "focus": "risultati test, follow-up, indicazioni"},
    "Logopedista": {"tone": "riabilitativo", "focus": "abilità, esercizi, progressi"},
    "Neuropsicomotricista": {"tone": "sviluppo-neuroevolutivo", "focus": "motricità, integrazione, obiettivi"},
    "Fisioterapista": {"tone": "funzionale", "focus": "ROM, forza, dolore, esercizi"},
}

def build_system_instructions(professionista: str, custom_profile: str = "") -> str:
    prof = PROFILI.get(professionista, {})
    tone = prof.get("tone", "professionale")
    focus = prof.get("focus", "riassunto clinico e indicazioni")

    extra = f"\nProfilo personalizzato:\n{custom_profile.strip()}\n" if custom_profile.strip() else ""
    return f"""
Sei un assistente clinico per la redazione di relazioni professionali in italiano.
Stai scrivendo per: {professionista}.
Stile: {tone}. Focus: {focus}.

Regole:
- Non inventare dati: usa SOLO i campi forniti.
- Se mancano dati, scrivi 'Dato non disponibile'.
- Evita diagnosi mediche se non presenti nei dati.
- Output: JSON conforme allo schema richiesto.
{extra}
""".strip()

def build_user_prompt(
    professionista: str,
    paziente_label: str,
    periodo: str,
    dataset: Dict[str, Any],
    note_libere: str = "",
) -> str:
    return f"""
PROFESSIONISTA: {professionista}
PAZIENTE: {paziente_label}
PERIODO: {periodo}

DATI ESTRATTI DAL GESTIONALE (solo paziente selezionato):
{dataset}

NOTE AGGIUNTIVE (facoltative):
{note_libere if note_libere else "-"}

OBIETTIVO:
Genera una relazione personalizzata per il professionista indicato.

Se nei dati è presente "diagnosi_automatica", usala come base per le diagnosi funzionali.
Se nei dati sono presenti risultati di test (DEM, K-D, TVPS, VMI, Fisher, ecc.), riportali
con i valori numerici e la loro interpretazione clinica.

Struttura relazione:
- Motivo della valutazione
- Anamnesi rilevante (perinatale, sviluppo, storia clinica)
- Risultati test oggettivi (con valori numerici e interpretazione)
- Diagnosi funzionale (usa diagnosi_automatica se disponibile)
- Indicazioni terapeutiche (Vision Therapy, riabilitazione, invii)
- Piano e follow-up proposto
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
