# -*- coding: utf-8 -*-
"""
catalogo_raven.py - Struttura delle Matrici Progressive di Raven (CPM, SPM).

Qui c'e' solo la STRUTTURA delle prove (serie, numero di item, numero di
alternative) e lo schema di classificazione in gradi. Le figure, la chiave di
correzione e le tabelle normative sono materiale protetto dell'editore: NON
stanno nel codice. Chiave e norme le carica ogni studio dal proprio manuale
(scheda «Norme e chiave») e restano nel database dello studio.
"""

FORME = {
    "CPM": {
        "nome": "Matrici Progressive Colorate (CPM)",
        "breve": "CPM",
        "serie": ["A", "Ab", "B"],
        "item": 12,
        "alternative": {"A": 6, "Ab": 6, "B": 6},
        "uso": "bambini dai 3 agli 11 anni circa, anziani, persone con difficoltà cognitive",
        "descrizione": (
            "Le Matrici Progressive Colorate di Raven (CPM) sono una prova non verbale di "
            "ragionamento per analogie visive: viene mostrata una figura incompleta e si chiede di "
            "scegliere, fra sei alternative, quella che la completa. Valutano la capacità di cogliere "
            "relazioni fra elementi visivi e di ragionare su materiale nuovo (intelligenza fluida), "
            "con un peso ridotto del linguaggio e delle conoscenze scolastiche. La prova comprende "
            "36 item, in tre serie (A, Ab, B) di difficoltà crescente."),
    },
    "SPM": {
        "nome": "Matrici Progressive Standard (SPM)",
        "breve": "SPM",
        "serie": ["A", "B", "C", "D", "E"],
        "item": 12,
        "alternative": {"A": 6, "B": 6, "C": 8, "D": 8, "E": 8},
        "uso": "dai 6 anni circa all'età adulta",
        "descrizione": (
            "Le Matrici Progressive Standard di Raven (SPM) sono una prova non verbale di "
            "ragionamento per analogie visive: viene mostrata una figura incompleta e si chiede di "
            "scegliere, fra più alternative, quella che la completa. Valutano la capacità di cogliere "
            "relazioni fra elementi visivi e di ragionare su materiale nuovo (intelligenza fluida), "
            "con un peso ridotto del linguaggio e delle conoscenze scolastiche. La prova comprende "
            "60 item, in cinque serie (A, B, C, D, E) di difficoltà crescente."),
    },
}

# Punti percentili con cui i manuali riportano le norme (grezzo per ogni fascia d'eta')
PUNTI = [5, 10, 25, 50, 75, 90, 95]

# Classificazione in gradi (schema generale di Raven) -> (fascia percentile, lettura)
GRADI = {
    "I":    ("pari o superiore al 95° percentile", "molto superiore alla media"),
    "II+":  ("fra il 90° e il 95° percentile", "superiore alla media"),
    "II":   ("fra il 75° e il 90° percentile", "superiore alla media"),
    "III+": ("fra il 50° e il 75° percentile", "nella media (fascia medio-alta)"),
    "III":  ("al 50° percentile", "nella media"),
    "III-": ("fra il 25° e il 50° percentile", "nella media (fascia medio-bassa)"),
    "IV":   ("fra il 10° e il 25° percentile", "inferiore alla media"),
    "IV-":  ("fra il 5° e il 10° percentile", "nettamente inferiore alla media"),
    "V":    ("pari o inferiore al 5° percentile", "molto inferiore alla media"),
}

# Scarto (in punti) fra punteggio di serie osservato e atteso oltre il quale
# la composizione del totale si considera atipica.
SCARTO_MAX = 2

COLLABORAZIONE = ["—", "adeguata", "discontinua", "scarsa"]
ATTENZIONE = ["—", "adeguata per tutta la prova", "in calo nella seconda parte", "fluttuante", "scarsa"]
STILE = ["—", "riflessivo", "rapido e accurato", "impulsivo (risposte date senza esplorare le alternative)",
         "lento e incerto"]

AVVERTENZA = ("Il punteggio alle Matrici di Raven descrive una sola componente del funzionamento "
              "cognitivo (il ragionamento non verbale). Va letto insieme al colloquio, all'osservazione "
              "e alle altre prove: da solo non consente conclusioni diagnostiche.")
