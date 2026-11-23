# -*- coding: utf-8 -*-
"""
catalogo_adhd.py - Strumenti del modulo ADHD (PNEV).

COSA C'E' E COSA NON C'E'
- Delle scale (Vanderbilt, SCARED) qui ci sono SOLO struttura e regole di
  punteggio: numero di item, sottoscale, soglie. Il testo degli item NON e'
  nel codice: si carica una volta dalla scheda «Testi e licenze» (resta nel
  database dello studio). Finche' il testo non c'e', la scala funziona come
  foglio risposte: si riportano le risposte dal modulo cartaceo.
- Per la Vanderbilt c'e' una breve etichetta d'argomento per item (parole
  nostre, serve all'operatore per non perdere il segno): NON e' l'item e non
  va letta al genitore al posto dell'item.
- La checklist dei criteri e' una scheda PNEV per il clinico, con parole
  nostre: non riproduce il testo del DSM-5.
- I test proprietari (Conners 3, BIA, Rey, BVSCO, WISC-V...) entrano solo
  come punteggi gia' calcolati dal clinico sul materiale originale.
"""

# ------------------------------------------------------------------ risposte
FREQ_0_3 = [(0, "Mai"), (1, "Qualche volta"), (2, "Spesso"), (3, "Molto spesso")]
REND_1_5 = [(1, "Eccellente"), (2, "Sopra la media"), (3, "Nella media"),
            (4, "Qualche problema"), (5, "Problematico")]
SCARED_0_2 = [(0, "Non vero o quasi mai"), (1, "A volte vero"), (2, "Molto vero o spesso")]

# ---------------------------------------------------------------- etichette
_DIS = ["Errori di distrazione", "Attenzione prolungata", "Ascolto quando gli si parla",
        "Portare a termine le consegne", "Organizzazione di compiti e attività",
        "Evita lo sforzo mentale prolungato", "Perde gli oggetti necessari",
        "Distraibilità da stimoli esterni", "Dimenticanze nelle attività quotidiane"]
_IPE = ["Irrequietezza di mani e piedi", "Si alza quando dovrebbe stare seduto",
        "Corre o si arrampica fuori luogo", "Gioco tranquillo", "Sempre in movimento",
        "Parla troppo", "Risponde prima che la domanda sia finita",
        "Attesa del proprio turno", "Interrompe o si intromette"]

_VG = _DIS + _IPE + [
    # 19-26 oppositivita'
    "Discute con gli adulti", "Perde la calma", "Sfida o rifiuta le regole",
    "Infastidisce di proposito", "Incolpa gli altri", "Suscettibile, facilmente irritato",
    "Arrabbiato o risentito", "Dispettoso, vendicativo",
    # 27-40 condotta
    "Prepotenze, minacce", "Inizia scontri fisici", "Bugie per evitare obblighi",
    "Assenze da scuola senza permesso", "Crudeltà fisica verso persone",
    "Furti di oggetti di valore", "Distruzione volontaria di cose altrui",
    "Uso di oggetti come arma", "Crudeltà fisica verso animali", "Appicca fuochi",
    "Effrazione in casa, negozio o auto", "Fuori di notte senza permesso",
    "Fuga da casa di notte", "Costrizione sessuale",
    # 41-47 ansia / umore
    "Paure, ansia, preoccupazioni", "Timore di sbagliare nelle cose nuove",
    "Senso di inferiorità", "Senso di colpa", "Si sente solo o non voluto",
    "Tristezza, infelicità", "Imbarazzo, timidezza",
    # 48-55 rendimento
    "Rendimento scolastico generale", "Lettura", "Scrittura", "Matematica",
    "Rapporto con i genitori", "Rapporto con i fratelli", "Rapporto con i coetanei",
    "Attività organizzate (es. squadre)"]

_VI = _DIS + _IPE + [
    # 19-28 oppositivita' / condotta
    "Perde la calma", "Sfida o rifiuta le regole", "Arrabbiato o risentito",
    "Dispettoso, vendicativo", "Prepotenze, minacce", "Inizia scontri fisici",
    "Bugie per evitare obblighi", "Crudeltà fisica verso persone",
    "Furti di oggetti di valore", "Distruzione volontaria di cose altrui",
    # 29-35 ansia / umore
    "Paure, ansia, preoccupazioni", "Imbarazzo, timidezza",
    "Timore di sbagliare nelle cose nuove", "Senso di inferiorità", "Senso di colpa",
    "Si sente solo o non voluto", "Tristezza, infelicità",
    # 36-43 rendimento
    "Lettura", "Matematica", "Espressione scritta", "Rapporto con i coetanei",
    "Segue le indicazioni", "Disturba la lezione", "Completa i compiti assegnati",
    "Capacità organizzative"]


def _r(a, b):
    return list(range(a, b + 1))


# ------------------------------------------------------------------- scale
SCALE = {
    "VAND_GEN": {
        "nome": "Vanderbilt (NICHQ) — genitori",
        "informatore": "Genitore",
        "eta": (6, 12),
        "n_item": 55,
        "etichette": _VG,
        "sezioni": [
            ("Disattenzione", _r(1, 9), FREQ_0_3),
            ("Iperattività / impulsività", _r(10, 18), FREQ_0_3),
            ("Oppositività", _r(19, 26), FREQ_0_3),
            ("Condotta", _r(27, 40), FREQ_0_3),
            ("Ansia / umore", _r(41, 47), FREQ_0_3),
            ("Rendimento e relazioni", _r(48, 55), REND_1_5),
        ],
        "regole": {
            "disattenzione": (_r(1, 9), 6),
            "iperattivita": (_r(10, 18), 6),
            "oppositivita": (_r(19, 26), 4),
            "condotta": (_r(27, 40), 3),
            "ansia_umore": (_r(41, 47), 3),
            "rendimento": _r(48, 55),
        },
        "credito": ("NICHQ Vanderbilt Assessment Scales, 1ª edizione — © 2002 American Academy "
                    "of Pediatrics e National Initiative for Children's Healthcare Quality. "
                    "Adattate dalle Vanderbilt Rating Scales di Mark L. Wolraich, MD."),
        "nota": ("Soglie dalle istruzioni di punteggio originali (USA): non ci sono norme "
                 "italiane. È uno screening: da sola non fa diagnosi."),
    },
    "VAND_INS": {
        "nome": "Vanderbilt (NICHQ) — insegnanti",
        "informatore": "Insegnante",
        "eta": (6, 12),
        "n_item": 43,
        "etichette": _VI,
        "sezioni": [
            ("Disattenzione", _r(1, 9), FREQ_0_3),
            ("Iperattività / impulsività", _r(10, 18), FREQ_0_3),
            ("Oppositività / condotta", _r(19, 28), FREQ_0_3),
            ("Ansia / umore", _r(29, 35), FREQ_0_3),
            ("Rendimento e comportamento in classe", _r(36, 43), REND_1_5),
        ],
        "regole": {
            "disattenzione": (_r(1, 9), 6),
            "iperattivita": (_r(10, 18), 6),
            "oppositivita_condotta": (_r(19, 28), 3),
            "ansia_umore": (_r(29, 35), 3),
            "rendimento": _r(36, 43),
        },
        "credito": ("NICHQ Vanderbilt Assessment Scales, 1ª edizione — © 2002 American Academy "
                    "of Pediatrics e National Initiative for Children's Healthcare Quality. "
                    "Adattate dalle Vanderbilt Rating Scales di Mark L. Wolraich, MD."),
        "nota": ("Soglie dalle istruzioni di punteggio originali (USA): non ci sono norme "
                 "italiane. È uno screening: da sola non fa diagnosi."),
    },
    "SCARED_B": {
        "nome": "SCARED — bambino/ragazzo",
        "informatore": "Bambino/ragazzo",
        "eta": (8, 18),
        "n_item": 41,
        "etichette": None,
        "sezioni": [("Item 1–41 (ultimi 3 mesi)", _r(1, 41), SCARED_0_2)],
        "credito": ("Screen for Child Anxiety Related Emotional Disorders (SCARED) — Birmaher, "
                    "Khetarpal, Cully, Brent, McKenzie; Western Psychiatric Institute and Clinic, "
                    "University of Pittsburgh (1995; revisione a 41 item 1999)."),
        "nota": "Screening dell'ansia: un punteggio sopra soglia va approfondito, non è una diagnosi.",
    },
    "SCARED_G": {
        "nome": "SCARED — genitore",
        "informatore": "Genitore",
        "eta": (8, 18),
        "n_item": 41,
        "etichette": None,
        "sezioni": [("Item 1–41 (ultimi 3 mesi)", _r(1, 41), SCARED_0_2)],
        "credito": ("Screen for Child Anxiety Related Emotional Disorders (SCARED) — Birmaher, "
                    "Khetarpal, Cully, Brent, McKenzie; Western Psychiatric Institute and Clinic, "
                    "University of Pittsburgh (1995; revisione a 41 item 1999)."),
        "nota": "Screening dell'ansia: un punteggio sopra soglia va approfondito, non è una diagnosi.",
    },
}

# SCARED: sottoscala -> (item, soglia)
SCARED_SOTTOSCALE = {
    "Panico / sintomi somatici": ([1, 6, 9, 12, 15, 18, 19, 22, 24, 27, 30, 34, 38], 7),
    "Ansia generalizzata": ([5, 7, 14, 21, 23, 28, 33, 35, 37], 9),
    "Ansia da separazione": ([4, 8, 13, 16, 20, 25, 29, 31], 5),
    "Ansia sociale": ([3, 10, 26, 32, 39, 40, 41], 8),
    "Evitamento della scuola": ([2, 11, 17, 36], 3),
}
SCARED_SOGLIA_TOTALE = 25

# ------------------------------------------------- checklist criteri (clinico)
CRITERI_DISATTENZIONE = [
    "Sbaglia per disattenzione, trascura i dettagli",
    "Fatica a restare attento su compiti o giochi",
    "Sembra non ascoltare quando gli si parla direttamente",
    "Non segue le istruzioni fino in fondo, lascia i compiti a metà",
    "Fatica a organizzare compiti e attività",
    "Evita o affronta malvolentieri ciò che chiede sforzo mentale prolungato",
    "Perde gli oggetti che gli servono",
    "Si distrae facilmente per stimoli esterni",
    "È sbadato nelle attività di ogni giorno",
]
CRITERI_IPERATTIVITA = [
    "Muove mani e piedi, si dimena sulla sedia",
    "Si alza quando dovrebbe restare seduto",
    "Corre o si arrampica dove non è il caso (negli adulti: irrequietezza)",
    "Non riesce a giocare o a svagarsi in modo tranquillo",
    "È sempre in movimento, come «spinto da un motore»",
    "Parla troppo",
    "Risponde prima che la domanda sia finita",
    "Fatica ad aspettare il proprio turno",
    "Interrompe gli altri o si intromette",
]
CONTESTI = ["Casa", "Scuola / lavoro", "Con i coetanei", "Sport / attività extrascolastiche",
            "In studio (osservazione diretta)"]
GRAVITA = ["Lieve", "Moderata", "Grave"]

# ---------------------------------------------------------- prove a schermo
PROVE = {
    "attenzione": {
        "nome": "Attenzione sostenuta",
        "cosa": "Lettere una alla volta: si preme solo quando compare la X.",
        "misura": "Omissioni, false risposte, tempi di reazione e loro variabilità, tenuta nel tempo.",
        "eta_min": 6,
        "durate": {"Breve (3 min)": 120, "Standard (6 min)": 240, "Lunga (9 min)": 360},
        "config": {"p_target": 0.2, "stim_ms": 250, "isi_ms": 1500},
    },
    "gonogo": {
        "nome": "Go / No-Go (inibizione)",
        "cosa": "Si preme a ogni cerchio verde; NON si preme quando il cerchio è rosso.",
        "misura": "Risposte non trattenute (errori di commissione), omissioni, tempi di reazione.",
        "eta_min": 5,
        "durate": {"Breve (2 min)": 100, "Standard (4 min)": 200},
        "config": {"p_target": 0.75, "stim_ms": 400, "isi_ms": 1200},
    },
    "stroop": {
        "nome": "Stroop colori (interferenza)",
        "cosa": "Si tocca il COLORE in cui è scritta la parola, non quello che la parola dice.",
        "misura": "Differenza di tempo ed errori tra parole coerenti e incoerenti.",
        "eta_min": 8,
        "durate": {"Breve (32 prove)": 32, "Standard (64 prove)": 64},
        "config": {"p_incongruente": 0.5, "limite_ms": 4000},
    },
    "span": {
        "nome": "Span di cifre (avanti e indietro)",
        "cosa": "Cifre una alla volta sullo schermo: si ripetono nello stesso ordine, poi al contrario.",
        "misura": "Lunghezza massima ricordata in avanti e all'indietro.",
        "eta_min": 6,
        "durate": {"Standard": 0},
        "config": {"cifra_ms": 800, "pausa_ms": 300, "partenza": 2, "massimo": 9},
    },
}

# ------------------------------------------------------- test esterni (punteggi)
# metrica -> (media, deviazione standard)
METRICHE = {
    "T": ("Punto T", 50.0, 10.0),
    "QI": ("Punteggio standard (media 100, ds 15)", 100.0, 15.0),
    "POND": ("Punteggio ponderato (media 10, ds 3)", 10.0, 3.0),
    "Z": ("Punto z", 0.0, 1.0),
    "PERC": ("Percentile", None, None),
    "GREZZO": ("Punteggio grezzo (senza conversione)", None, None),
}

# verso: "alto" = un valore alto segnala difficolta' (scale di sintomi);
#        "basso" = un valore basso segnala difficolta' (prove di abilita')
TEST_ESTERNI = {
    "Conners 3 — genitori": {
        "metrica": "T", "verso": "alto",
        "scale": ["Inattenzione", "Iperattività / impulsività", "Problemi di apprendimento",
                  "Funzioni esecutive", "Provocazione / aggressività", "Relazioni con i pari",
                  "Indice globale"]},
    "Conners 3 — insegnanti": {
        "metrica": "T", "verso": "alto",
        "scale": ["Inattenzione", "Iperattività / impulsività",
                  "Problemi di apprendimento / funzioni esecutive",
                  "Provocazione / aggressività", "Relazioni con i pari", "Indice globale"]},
    "Conners 3 — autovalutazione": {
        "metrica": "T", "verso": "alto",
        "scale": ["Inattenzione", "Iperattività / impulsività", "Problemi di apprendimento",
                  "Provocazione / aggressività", "Relazioni familiari"]},
    "WISC-V": {
        "metrica": "QI", "verso": "basso",
        "scale": ["Comprensione verbale (ICV)", "Visuo-spaziale (IVS)", "Ragionamento fluido (IRF)",
                  "Memoria di lavoro (IML)", "Velocità di elaborazione (IVE)",
                  "QI totale (QIT)", "Abilità generale (IAG)", "Competenza cognitiva (ICC)"]},
    "BIA — Batteria Italiana per l'ADHD": {
        "metrica": "PERC", "verso": "basso",
        "scale": ["CP — attenzione sostenuta visiva", "TAU — attenzione uditiva",
                  "MF — impulsività", "Completamento alternativo di frasi",
                  "Test delle ranette", "Stroop numerico", "Memoria strategica"]},
    "Figura complessa di Rey": {
        "metrica": "Z", "verso": "basso",
        "scale": ["Copia", "Riproduzione a memoria"]},
    "BVSCO — velocità di scrittura": {
        "metrica": "Z", "verso": "basso",
        "scale": ["le", "uno", "Numeri in parola"]},
    "Altro test": {"metrica": "Z", "verso": "basso", "scale": []},
}

AVVERTENZA = ("Questo modulo raccoglie e ordina i dati. La diagnosi resta un atto clinico: "
              "richiede colloquio, storia di sviluppo, più informatori e l'esclusione di altre "
              "spiegazioni. Nessun punteggio, da solo, la stabilisce.")
