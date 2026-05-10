# -*- coding: utf-8 -*-
"""
Definizione completa del protocollo INPP — Formulario di Valutazione
Diagnostica dello Sviluppo Neurologico.

Fonti:
- Formulario INPP rev. 01/22 (Annesso 1 — scheda di compilazione)
- INPP One Year Training Course 2019-2020, Secondo Modulo
  "La Valutazione Diagnostica" — manuale operativo

Questo file è la SORGENTE DI VERITÀ per tutto il modulo INPP:
- ui_inpp.py legge da qui per costruire i form
- db_inpp.py salva i dati con questi id come chiavi
- pdf_inpp.py legge da qui per costruire il referto

Per modificare/aggiungere una prova, basta cambiare questo file.

═══════════════════════════════════════════════════════════════════════════
STRUTTURA DI UNA PROVA
═══════════════════════════════════════════════════════════════════════════

Campi OBBLIGATORI:
- id           : identificatore unico (chiave per il salvataggio in DB)
- label        : etichetta visibile nella UI
- scoring      : tipo di scoring (vedi sotto)

Campi OPZIONALI di guida clinica (si popolano gradualmente dal manuale):
- istruzioni   : testo delle istruzioni da dare al paziente
                 (es. "Disteso pancia in su, fra poco ti chiederò...")
- osservazioni : criteri di osservazione clinica per il valutatore
                 (es. "Come si alza, c'è posizione gambe a W, è stabile...")
- scoring_specifico : dict {0: "...", 1: "...", 2: "...", 3: "...", 4: "..."}
                      con la descrizione SPECIFICA per QUESTA prova.
                      Se assente, viene usata la legenda generica SCORING_LABELS.
- video_url    : URL diretto a un video esplicativo (Dropbox raw=1, YouTube,
                 ecc.). Se presente, l'UI mostra un player.
- posturale    : bool — True se è un riflesso posturale (lo scoring si inverte
                 clinicamente: 0=assenza riflesso, 4=riflesso completo)

Tipi di scoring:
- "0-4"          : scoring INPP standard (legenda in SCORING_LABELS)
- "si_no"        : sì / no
- "lateralita"   : sx / dx (preferenza laterale)
- "numerico"     : campi numerici (es. n.ripetizioni, secondi)
- "testo"        : testo libero
- "scelta"       : una scelta da una lista predefinita (vedi 'opzioni')
"""

from typing import Any

# -----------------------------------------------------------------------------
# Legende scoring 0-4
# -----------------------------------------------------------------------------

# Legenda generica universale (manuale corso INPP 2019-2020, pag. 3)
# Usata come fallback quando una prova non ha scoring_specifico.
# È neutra rispetto al tipo di prova: vale per coordinazione, cerebellare,
# disdiadococinesia, oculomotori, ecc.
SCORING_LABELS: dict[int, str] = {
    0: "N.A. — Nessuna anomalia",
    1: "Disfunzione del 25% — Minima",
    2: "Disfunzione del 50% — Moderata",
    3: "Disfunzione del 75% — Marcata",
    4: "Disfunzione del 100% — Completa",
}

# Legenda specifica per i RIFLESSI (Formulario rev. 01/22, pag. 2)
# Usata in fallback solo quando nella sezione "riflessi" una prova non ha
# scoring_specifico — terminologia clinicamente più precisa per il riflessi.
SCORING_LABELS_RIFLESSI: dict[int, str] = {
    0: "Nessuna anomalia",
    1: "Minima presenza residua di un riflesso primitivo / Minima mancanza di sviluppo di un riflesso posturale",
    2: "Riflesso primitivo residuo / Assenza parziale di un riflesso posturale",
    3: "Riflesso primitivo presente in gran parte / Quasi totale assenza di un riflesso posturale",
    4: "Riflesso primitivo completamente ritenuto / Assenza completa di un riflesso posturale",
}

# Alias mantenuto per compatibilità; ora coincide con la legenda generica
SCORING_LABELS_PERCENTUALE: dict[int, str] = SCORING_LABELS

# -----------------------------------------------------------------------------
# Le 10 sezioni del Formulario INPP
# Ogni sezione ha: id, label, descrizione, e una lista di 'gruppi'.
# Ogni gruppo è un blocco logico di prove (es. "Riflesso Tonico Asimmetrico
# del Collo") che contiene 1+ prove.
# -----------------------------------------------------------------------------

PROTOCOLLO_INPP: list[dict[str, Any]] = [
    # =========================================================================
    # SEZIONE 2 — COORDINAZIONE GROSSO-MOTORIA ED EQUILIBRIO
    # =========================================================================
    {
        "id": "coordinazione_equilibrio",
        "label": "Coordinazione grosso-motoria ed equilibrio",
        "icon": "🚶",
        "gruppi": [
            {
                "id": "recupero",
                "label": "Recupero della posizione verticale",
                "prove": [
                    {
                        "id": "rec_supino",
                        "label": "Da supino",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Disteso pancia in su. Fra poco ti chiederò di alzarti il più "
                            "velocemente possibile, e quando sarai in piedi, dovrai rimanere "
                            "con i piedi insieme e le braccia e mani sui fianchi, come un soldato."
                        ),
                        "osservazioni": (
                            "• Come si alza? La sequenza normale è: alzare la testa, sollevare il "
                            "tronco, utilizzare le mani come appoggio e poi spostare i piedi.\n"
                            "• C'è posizione delle gambe a W (RTSC)?\n"
                            "• È stabile quando raggiunge la posizione? La stabilità può essere "
                            "disturbata da fattori vestibolari, di cervelletto, di riflessi o per "
                            "una situazione di bassa pressione sanguigna."
                        ),
                        "scoring_specifico": {
                            0: "N.A. — Nessuna anomalia",
                            1: "Lento",
                            2: "Lento e scoordinato",
                            3: "Marcato dondolio quando raggiunge la posizione in piede",
                            4: "Dondola e perde l'equilibrio — sposta lateralmente uno dei piedi",
                        },
                    },
                    {
                        "id": "rec_prono",
                        "label": "Da prono",
                        "scoring": "0-4",
                        "istruzioni": "Come il test precedente, ma disteso prono (pancia in giù).",
                        "osservazioni": (
                            "• Sequenza normale: appoggiarsi sulle braccia come sostegno, piegare "
                            "le ginocchia e spingere fino ad alzarsi.\n"
                            "• Punteggio in base a:\n"
                            "  a) il livello di scostamento dalla sequenza normale\n"
                            "  b) stabilità dell'equilibrio statico in piede"
                        ),
                        "scoring_specifico": {
                            0: "N.A. — Nessuna anomalia",
                            1: "Lieve scostamento dalla sequenza",
                            2: "Scostamento moderato / lieve instabilità statica",
                            3: "Scostamento marcato / instabilità marcata",
                            4: "Incapacità di completare la sequenza o perdita di equilibrio",
                        },
                    },
                ],
            },
            {
                "id": "romberg",
                "label": "Test di Romberg",
                "prove": [
                    {
                        "id": "romberg_aperti",
                        "label": "Occhi aperti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "In piedi, con i piedi insieme e le mani e le braccia sui fianchi, "
                            "guarda dritto in avanti. I bambini sopra i 4 anni dovrebbero essere "
                            "in grado di mantenere la posizione fino a 10 secondi senza perdere "
                            "l'equilibrio."
                        ),
                        "osservazioni": (
                            "Test standardizzato che valuta il controllo dell'equilibrio statico "
                            "e la propriocezione.\n"
                            "• C'è dondolio? Verso che lato?\n"
                            "• C'è aggiustamento posturale verso un lato?\n"
                            "• C'è presa con le dita dei piedi?\n"
                            "• Negli adulti, può essere utile chiedere la sensazione soggettiva di "
                            "dondolio (scala 1-10), non da includere nel punteggio ma utile "
                            "indicatore di fatica/compensazione."
                        ),
                        "scoring_specifico": {
                            0: "Capace di mantenersi stabile senza dondolio o perdita dell'equilibrio",
                            1: "Lieve dondolio (annotare la direzione) o minimo coinvolgimento di altre parti del corpo",
                            2: "Dondolio evidente e/o coinvolgimento delle mani o delle braccia",
                            3: "Difficoltà significativa nel mantenere l'equilibrio",
                            4: "Perde l'equilibrio",
                        },
                    },
                    {
                        "id": "romberg_chiusi",
                        "label": "Occhi chiusi",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere lo stesso test con gli occhi chiusi. Il punteggio deve essere "
                            "dato separatamente, con le stesse osservazioni."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni del Romberg a occhi aperti.\n"
                            "• Se si osserva un peggioramento significativo a occhi chiusi, può "
                            "essere un indicatore di difficoltà propriocettive o di equilibrio."
                        ),
                        "scoring_specifico": {
                            0: "Capace di mantenersi stabile senza dondolio o perdita dell'equilibrio",
                            1: "Lieve dondolio o minimo coinvolgimento di altre parti del corpo",
                            2: "Dondolio evidente e/o coinvolgimento delle mani o delle braccia",
                            3: "Difficoltà significativa nel mantenere l'equilibrio",
                            4: "Perde l'equilibrio",
                        },
                    },
                ],
            },
            {
                "id": "mann",
                "label": "Test di Mann (Romberg avanzato)",
                "prove": [
                    {
                        "id": "mann_aperti",
                        "label": "Occhi aperti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Rimani fermo in piedi con un piede davanti all'altro, con il tallone "
                            "toccando la punta dell'altro piede e con le mani sui fianchi."
                        ),
                        "osservazioni": (
                            "• Riesce il sistema vestibolare ad adattarsi al cambiamento di "
                            "posizione e di distribuzione dei pesi?\n"
                            "• Problemi nella linea media?\n"
                            "• Se si \"sentono\" instabili ma non c'è evidenza di ciò, potrebbe "
                            "indicare \"mismatch\" vestibolare-propriocettivo.\n"
                            "• Vertigine soggettiva: \"tutto in torno a me è fermo, io mi muovo\"\n"
                            "• Vertigine oggettiva: \"io sono fermo, ma è la stanza a muoversi\"\n"
                            "• Coinvolgimento delle braccia per mantenere l'equilibrio."
                        ),
                        "scoring_specifico": {
                            0: "Capace di mantenersi stabile senza dondolio o perdita dell'equilibrio",
                            1: "Lieve dondolio (annotare la direzione) o minimo coinvolgimento di altre parti del corpo",
                            2: "Dondolio evidente e/o coinvolgimento delle mani o delle braccia",
                            3: "Difficoltà significativa nel mantenere l'equilibrio",
                            4: "Perde l'equilibrio",
                        },
                    },
                    {
                        "id": "mann_chiusi",
                        "label": "Occhi chiusi",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere lo stesso test con gli occhi chiusi. Il punteggio deve essere "
                            "dato separatamente, con le stesse osservazioni."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni del Mann a occhi aperti. Un peggioramento "
                            "significativo ad occhi chiusi può indicare difficoltà propriocettive "
                            "o di equilibrio."
                        ),
                        "scoring_specifico": {
                            0: "Capace di mantenersi stabile senza dondolio o perdita dell'equilibrio",
                            1: "Lieve dondolio o minimo coinvolgimento di altre parti del corpo",
                            2: "Dondolio evidente e/o coinvolgimento delle mani o delle braccia",
                            3: "Difficoltà significativa nel mantenere l'equilibrio",
                            4: "Perde l'equilibrio",
                        },
                    },
                ],
            },
            {
                "id": "cammino_mezzo_giro",
                "label": "Cammino e mezzo giro",
                "prove": [
                    {
                        "id": "cammino_mezzo_giro",
                        "label": "Cammino e mezzo giro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Cammina da un lato all'altro della stanza. Continua camminando "
                            "finché ti dirò \"fermo!\". Allora fermati, girati per guardare verso "
                            "il lato opposto, e rimani fermo \"sull'attenti\", con i piedi insieme. "
                            "(Dimostrare i primi passi)."
                        ),
                        "osservazioni": (
                            "Durante il cammino osservare:\n"
                            "1. Mancanza di coordinazione grosso-motoria\n"
                            "2. Schema del cammino (crociato, omolaterale...)\n"
                            "3. Difficoltà nella sincronia dei movimenti\n\n"
                            "• Diventa omolaterale dopo il giro?\n"
                            "• Cammino tipo \"RTSC\" (flessione)?\n"
                            "• Coinvolgimento degli arti superiori?\n"
                            "• Si destabilizza dopo il giro? (giramento di testa)\n"
                            "• Ricorda tutte le istruzioni? (elaborazione uditiva)\n\n"
                            "Schema normale: cammino in schema incrociato con coinvolgimento di "
                            "braccia e gambe, senza perdita di equilibrio o stabilità per effetto "
                            "del giro.\n\n"
                            "Riflessi possibilmente coinvolti: RTAC, RTSC, mancanza di riflessi "
                            "di rotazione segmentaria (es. nessuna differenziazione a livello del "
                            "bacino)."
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Movimenti asincroni o movimenti inadeguati delle braccia",
                            2: "Cambio a cammino omolaterale durante il giro",
                            3: "Omolaterale o senza movimento delle braccia",
                            4: "Non ci riesce",
                        },
                    },
                ],
            },
            {
                "id": "punte",
                "label": "Camminare sulle punte",
                "prove": [
                    {
                        "id": "punte_avanti",
                        "label": "Avanti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Mettiti sulle punte, e LENTAMENTE cammina lungo la stanza guardando "
                            "dritto in avanti. (Dimostrare i primi passi)."
                        ),
                        "osservazioni": (
                            "• Riflesso prensile nei piedi?\n"
                            "• Coinvolgimento del viso\n"
                            "• Fissazione dello sguardo sul target\n"
                            "• Rigidità muscolare\n"
                            "• Grado di sforzo/difficoltà\n"
                            "• C'è deviazione in diagonale quando va all'indietro? (problemi vestibolari)\n"
                            "• Passi di \"giapponesina\" (deambulazione cerebellare)?\n"
                            "• Cammino con le gambe a \"forbice\"? Oppure minore inclinazione "
                            "di uno dei due piedi."
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Non completamente sulle punte, piccole difficoltà",
                            2: "Lieve deviazione dalla normalità o lieve perdita dell'equilibrio",
                            3: "Deviazione moderata/perdita di equilibrio",
                            4: "Incapacità o perdita totale dell'equilibrio",
                        },
                    },
                    {
                        "id": "punte_indietro",
                        "label": "Indietro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere il test camminando sulle punte all'indietro. Annotare ogni "
                            "differenza di abilità nel compito in avanti e all'indietro."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni del cammino sulle punte in avanti. La deviazione "
                            "in diagonale all'indietro è particolarmente indicativa di problemi "
                            "vestibolari."
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Non completamente sulle punte, piccole difficoltà",
                            2: "Lieve deviazione dalla normalità o lieve perdita dell'equilibrio",
                            3: "Deviazione moderata/perdita di equilibrio",
                            4: "Incapacità o perdita totale dell'equilibrio",
                        },
                    },
                ],
            },
            {
                "id": "tandem",
                "label": "Tallone-Punta (tandem walk), dai 7 anni",
                "prove": [
                    {
                        "id": "tandem_avanti",
                        "label": "Avanti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Lentamente cammina lungo la stanza collocando un piede davanti "
                            "all'altro, tallone toccando la punta e guardando sempre fisso in "
                            "avanti. (Dimostrare i primi passi)."
                        ),
                        "osservazioni": (
                            "• Precisione nella collocazione dei piedi (propriocezione)\n"
                            "• Dondolamento\n"
                            "• Posizione della testa, fissazione dello sguardo\n"
                            "• Equilibrio\n"
                            "• Coinvolgimento delle braccia, mani o viso\n"
                            "• Difficoltà nella linea media"
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lievi difficoltà d'equilibrio o di collocazione dei piedi, tendenza a perdere la fissazione degli occhi, lieve coinvolgimento del viso, tendenza a guardare verso i piedi, lieve coinvolgimento delle mani o braccia",
                            2: "Maggior grado delle osservazioni precedenti, utilizzo delle braccia per mantenere l'equilibrio, difficoltà a mantenersi nella linea media",
                            3: "Quasi perdita di equilibrio, braccia aperte, ondeggiamento delle braccia o del corpo, imprecisione nell'appoggio dei piedi",
                            4: "Perdita di equilibrio con o senza presenza significativa delle osservazioni precedenti",
                        },
                    },
                    {
                        "id": "tandem_indietro",
                        "label": "Indietro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere il test all'indietro. Segnalare ogni differenza significativa "
                            "nello svolgimento del compito all'indietro."
                        ),
                        "osservazioni": "Stesse osservazioni del tandem walk in avanti.",
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lievi difficoltà d'equilibrio o di collocazione dei piedi",
                            2: "Maggior grado delle osservazioni precedenti, difficoltà nella linea media",
                            3: "Quasi perdita di equilibrio, ondeggiamento, imprecisione nell'appoggio",
                            4: "Perdita di equilibrio",
                        },
                    },
                ],
            },
            {
                "id": "fog",
                "label": "Camminare sull'esterno dei piedi (Fog walk)",
                "prove": [
                    {
                        "id": "fog_avanti",
                        "label": "Avanti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Lentamente cammina lungo la stanza appoggiandoti solo sulla parte "
                            "esterna dei tuoi piedi. Guarda dritto in avanti.\n\n"
                            "Questo test può essere utilizzato in termini qualitativi dai 7-7 anni "
                            "e mezzo, ma è normale osservare movimenti compensatori fino ai 10-13 "
                            "anni di età."
                        ),
                        "osservazioni": (
                            "Questo test rivela ogni difficoltà a livello di equilibrio o "
                            "coordinazione. Osservare se ha bisogno di fare una pausa dopo ogni "
                            "passo, e qualsiasi cambiamento nella postura, nella posizione di "
                            "mani/braccia e coinvolgimento del viso.\n\n"
                            "• Riesce a rimanere sull'esterno dei piedi tutto il tempo?\n"
                            "• Iperestensione degli alluci?\n"
                            "• Gambe rigide, gambe molto separate? (cervelletto)\n"
                            "• Cammino tipo \"scimmia\"\n"
                            "• Rotazione delle mani come formando una \"tazzina\" o emiplegia "
                            "nelle mani?"
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lieve coinvolgimento involontario di una delle mani",
                            2: "Coinvolgimento delle mani in entrambi i lati del corpo e/o lieve alterazione posturale, o non completamente sull'esterno dei piedi e/o movimenti del viso/bocca",
                            3: "Postura tipo \"scimmia\" o deambulazione rigida con movimenti omolaterali o emiplegia molto evidente",
                            4: "Postura tipo \"scimmia\" molto evidente, incapace di muoversi o completare il compito",
                        },
                    },
                    {
                        "id": "fog_indietro",
                        "label": "Indietro",
                        "scoring": "0-4",
                        "istruzioni": "Ripetere il test all'indietro e dare punteggi separati.",
                        "osservazioni": "Stesse osservazioni del Fog walk in avanti.",
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lieve coinvolgimento involontario di una delle mani",
                            2: "Coinvolgimento bilaterale delle mani e/o lieve alterazione posturale",
                            3: "Postura \"scimmia\" o deambulazione rigida con movimenti omolaterali",
                            4: "Postura \"scimmia\" molto evidente, incapace di completare",
                        },
                    },
                ],
            },
            {
                "id": "slalom",
                "label": "Camminare in slalom (dai 7-8 anni)",
                "prove": [
                    {
                        "id": "slalom_avanti",
                        "label": "Avanti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Cammina lungo la stanza alzando una gamba a livello del ginocchio e "
                            "incrociando davanti all'altra gamba, guardando sempre in avanti."
                        ),
                        "osservazioni": (
                            "• Difficoltà per incrociare la linea media\n"
                            "• Difficoltà nel sollevare la gamba a livello del ginocchio (RTL)\n"
                            "• Equilibrio e stabilità, controllo dei movimenti\n"
                            "• Livello di coinvolgimento di altre parti del corpo"
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lievi difficoltà nelle osservazioni indicate",
                            2: "Difficoltà moderate",
                            3: "Difficoltà marcate",
                            4: "Incapacità di completare il compito",
                        },
                    },
                    {
                        "id": "slalom_indietro",
                        "label": "Indietro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere il test all'indietro. È in grado di capire come invertire il "
                            "movimento da solo? Altrimenti può indicare difficoltà nella "
                            "programmazione dei movimenti. Dare punteggi separati per entrambi i compiti."
                        ),
                        "osservazioni": "Stesse osservazioni dello slalom in avanti.",
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Lievi difficoltà",
                            2: "Difficoltà moderate",
                            3: "Difficoltà marcate",
                            4: "Incapacità di completare",
                        },
                    },
                ],
            },
            {
                "id": "talloni",
                "label": "Camminare sui talloni (dai 7-8 anni)",
                "prove": [
                    {
                        "id": "talloni",
                        "label": "Camminare sui talloni",
                        "scoring": "0-4",
                        "istruzioni": (
                            "In piedi sui talloni, cammina lungo la stanza appoggiandoti sempre "
                            "solo sui talloni, alzando la gamba il più possibile, guardando sempre "
                            "in avanti. (Dimostrare i primi passi)."
                        ),
                        "osservazioni": (
                            "• Riesce a fare la dorsi-flessione dei piedi?\n"
                            "• Piega le ginocchia o c'è un aumento della rigidità?\n"
                            "• Coinvolgimento esagerato delle mani o braccia?\n"
                            "• Livello di \"overflow\" (compensazioni) di movimenti di altre "
                            "parti del corpo?"
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Osservazioni lievi come sopra",
                            2: "Osservazioni moderate come sopra",
                            3: "Coinvolgimento molto importante delle braccia e movimenti \"strani\" al compito per mantenere l'equilibrio",
                            4: "Non riesce a completare il compito",
                        },
                    },
                ],
            },
            {
                "id": "saltellare",
                "label": "Saltellare su una gamba (dai 4 anni)",
                "prove": [
                    {
                        "id": "saltellare",
                        "label": "Saltellare su una gamba (destra / sinistra)",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Salta su una sola gamba spostandoti in avanti lungo tutta la stanza "
                            "finché ti chiederò di fermarti. Eseguire su entrambi i lati."
                        ),
                        "osservazioni": (
                            "• Equilibrio\n"
                            "• Riesce a controllare la velocità del movimento? È fluido?\n"
                            "• Riesce a fermarsi?\n"
                            "• Cambia piede quando torna indietro?\n"
                            "• C'è dorsiflessione del piede o c'è qualche livello di \"piede piatto\"?\n"
                            "• Segnalare che piede utilizza."
                        ),
                        "scoring_specifico": {
                            0: "N.A.",
                            1: "Movimento non abbastanza controllato",
                            2: "Piede piatto",
                            3: "Equilibrio instabile, postura spostata in avanti",
                            4: "Cade",
                        },
                    },
                ],
            },
            {
                "id": "schema_incrociato",
                "label": "Saltellare in schema incrociato (dai 5 anni)",
                "prove": [
                    {
                        "id": "schema_incrociato",
                        "label": "Saltellare in schema incrociato (\"skipping without a rope\")",
                        "scoring": "0-4",
                        "istruzioni": "Saltella in avanti lungo la stanza finché ti chiederò di fermarti.",
                        "osservazioni": (
                            "• Riesce a farlo?\n"
                            "• Lo fa in schema incrociato?"
                        ),
                        "scoring_specifico": {
                            0: "N.A. — Saltella correttamente in schema incrociato",
                            1: "Schema incrociato presente ma con lievi difficoltà",
                            2: "Schema incrociato impreciso o con compensazioni",
                            3: "Tendenza allo schema omolaterale",
                            4: "Non riesce o schema completamente omolaterale",
                        },
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 3 — SCHEMI DI SVILUPPO MOTORIO
    # Nella scheda interna del manuale: celle libere per descrizione testuale,
    # niente scoring 0-4 né checkbox.
    # =========================================================================
    {
        "id": "schemi_sviluppo",
        "label": "Schemi di sviluppo motorio",
        "icon": "🌀",
        "no_total": True,  # niente totale numerico
        "gruppi": [
            {
                "id": "striscio",
                "label": "Striscio",
                "prove": [
                    {"id": "striscio_omologo", "label": "Omologo", "scoring": "testo"},
                    {"id": "striscio_omolaterale", "label": "Omolaterale", "scoring": "testo"},
                    {"id": "striscio_incrociato", "label": "Incrociato", "scoring": "testo"},
                ],
            },
            {
                "id": "carponi",
                "label": "Carponi",
                "prove": [
                    {"id": "carponi_omologo", "label": "Omologo", "scoring": "testo"},
                    {"id": "carponi_omolaterale", "label": "Omolaterale", "scoring": "testo"},
                    {"id": "carponi_incrociato", "label": "Incrociato", "scoring": "testo"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 4 — FUNZIONALITÀ CEREBELLARE
    # =========================================================================
    {
        "id": "cerebellare",
        "label": "Funzionalità cerebellare",
        "icon": "🧠",
        "gruppi": [
            {
                "id": "tallone_tibia",
                "label": "Tallone su tibia",
                "prove": [
                    {
                        "id": "tallone_sx_su_dx",
                        "label": "Sx su Dx",
                        "scoring": "0-4",
                        "istruzioni": (
                            "\"Disteso pancia in su, mani accanto ai fianchi. Piegare un ginocchio "
                            "e collocare il tallone di quel piede sull'altra gamba, appena sotto "
                            "il ginocchio. Lentamente fare scorrere il tallone lungo la tibia "
                            "dell'altra gamba dal ginocchio fino alla caviglia.\" (Dimostrare).\n\n"
                            "Ripetere il movimento due volte lentamente e un'altra un po' più "
                            "velocemente. Ripetere il test con l'altra gamba."
                        ),
                        "osservazioni": (
                            "Il cervelletto si occupa del controllo fine dei movimenti ed è il "
                            "mediatore dell'apprendimento motorio. Possono evincersi segni o "
                            "sintomi di danno cerebellare come atassia, dissinergia, ecc.\n\n"
                            "C'è ATASSIA quando c'è un errore nella coordinazione muscolare anche "
                            "se la forza necessaria per fare il movimento è presente (es. quando "
                            "non c'è inibizione dei movimenti necessari per raffinare il movimento "
                            "quando si vuole mantenere la posizione di una parte del corpo).\n\n"
                            "È molto infrequente trovare segni di danno cerebellare in questi test "
                            "in una popolazione di bambini con difficoltà di apprendimento; più "
                            "spesso si osserva una DISFUNZIONE che potrebbe essere collegata a un "
                            "funzionamento immaturo del cervelletto causato da riflessi posturali "
                            "non sviluppati o dalla interferenza di attività persistente dei "
                            "riflessi primitivi.\n\n"
                            "* Notare se riesce a trovare la posizione iniziale. Se il problema è "
                            "solo per LOCALIZZARE il punto appena sotto il ginocchio, può indicare "
                            "scarsa propriocezione. Se invece si trova difficoltà nel POSIZIONARE "
                            "il tallone sull'altra gamba, può indicare un problema a livello del "
                            "cervelletto. A volte, entrambi i problemi possono essere presenti.\n"
                            "* Ci sono difficoltà per controllare il movimento lungo la tibia?\n"
                            "* Si alza il tallone sistematicamente dell'altra gamba? Questo può "
                            "indicare problemi cerebellari.\n"
                            "* Succede su uno solo o su entrambi i lati? Il cervelletto controlla "
                            "lo stesso lato del corpo (ipsilaterale), mentre il cortex motorio "
                            "controlla il lato opposto del corpo (controlaterale)."
                        ),
                        "scoring_specifico": {
                            0: "Nulla da segnalare. Il movimento è fluido e controllato. Il soggetto riesce a localizzare il ginocchio e posizionare il tallone dell'altro piede",
                            1: "Minima difficoltà sia nel controllo del movimento che nel posizionare il tallone sulla tibia",
                            2: "Evidenza lieve di dissinergia o atassia nel controllo del movimento o nell'essere capace di collocare il tallone sulla tibia",
                            3: "Difficoltà significative nel controllo del movimento o nell'atto di posizionare il tallone sulla tibia",
                            4: "Il tallone sfugge sistematicamente dalla tibia. Non è capace di collocare il tallone nell'obiettivo prefissato",
                        },
                    },
                    {
                        "id": "tallone_dx_su_sx",
                        "label": "Dx su Sx",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Stesso test sull'altra gamba. Lentamente fare scorrere il tallone "
                            "destro lungo la tibia sinistra dal ginocchio fino alla caviglia. "
                            "Ripetere due volte lentamente e una un po' più velocemente."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni del lato sinistro. Annotare differenze "
                            "significative tra i due lati: il cervelletto controlla "
                            "ipsilateralmente, quindi una differenza marcata fra dx e sx può "
                            "essere indicativa di disfunzione cerebellare unilaterale."
                        ),
                        "scoring_specifico": {
                            0: "Nulla da segnalare. Il movimento è fluido e controllato. Il soggetto riesce a localizzare il ginocchio e posizionare il tallone dell'altro piede",
                            1: "Minima difficoltà sia nel controllo del movimento che nel posizionare il tallone sulla tibia",
                            2: "Evidenza lieve di dissinergia o atassia nel controllo del movimento o nell'essere capace di collocare il tallone sulla tibia",
                            3: "Difficoltà significative nel controllo del movimento o nell'atto di posizionare il tallone sulla tibia",
                            4: "Il tallone sfugge sistematicamente dalla tibia. Non è capace di collocare il tallone nell'obiettivo prefissato",
                        },
                    },
                ],
            },
            {
                "id": "approssimazione",
                "label": "Approssimazione digitale (linea mediana)",
                "prove": [
                    {
                        "id": "appr_aperti",
                        "label": "Occhi aperti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "\"In piedi con i piedi insieme. Stendere entrambe le braccia "
                            "lateralmente a livello delle spalle. Avvicinare lentamente le punte "
                            "degli indici sulla linea mediana, davanti al naso, finché si toccano. "
                            "Alternare la posizione lentamente 4 volte.\"\n\n"
                            "Ripetere prima a occhi aperti, poi a occhi chiusi."
                        ),
                        "osservazioni": (
                            "Si conteggia il numero di volte che il soggetto riesce a raggiungere "
                            "l'obiettivo con movimenti precisi e morbidi.\n\n"
                            "• Le punte degli indici si incontrano sulla linea mediana?\n"
                            "• Movimento fluido e simmetrico, o c'è dissinergia/tremore?\n"
                            "• C'è differenza fra entrambi i lati?\n"
                            "• Differenza nella localizzazione (propriocezione) o nella collocazione "
                            "(cerebellare)?"
                        ),
                        # Nessun scoring_specifico: il manuale non dà 5 livelli per questo test.
                        # Cade sulla legenda generica percentuale (SCORING_LABELS).
                    },
                    {
                        "id": "appr_chiusi",
                        "label": "Occhi chiusi",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere lo stesso test con gli occhi chiusi. Si conteggia il numero "
                            "di volte che il soggetto riesce a raggiungere l'obiettivo con "
                            "movimenti precisi e morbidi."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni a occhi aperti. Un peggioramento significativo a "
                            "occhi chiusi può indicare difficoltà propriocettive (sistema "
                            "vestibolare-propriocettivo che lavora senza il supporto della vista)."
                        ),
                    },
                ],
            },
            {
                "id": "dito_naso",
                "label": "Dito-naso (dai 7 anni — Accardo)",
                "prove": [
                    {
                        "id": "dn_aperti",
                        "label": "Occhi aperti",
                        "scoring": "0-4",
                        "istruzioni": (
                            "\"In piedi con i piedi insieme. Collocare la punta di uno degli "
                            "indici sulla punta del naso. Stendere l'altro braccio e dito indice "
                            "lateralmente a livello della spalla. Alternare la posizione "
                            "lentamente 4 volte.\""
                        ),
                        "osservazioni": (
                            "Si conteggia il numero di volte che il soggetto riesce a raggiungere "
                            "l'obiettivo con movimenti precisi e morbidi.\n\n"
                            "• Tocca il naso con la punta del dito senza difficoltà?\n"
                            "• Riesce a fare in modo che entrambi i lati svolgano movimenti "
                            "indipendenti?\n"
                            "• Il movimento diventa sincronizzato fra entrambi i lati del corpo?\n"
                            "• Segue la testa il movimento del braccio? (RTAC)\n"
                            "• Si stancano e si abbassano le braccia? (RTL)\n"
                            "• C'è differenza nella localizzazione (propriocezione) o nella "
                            "collocazione (cerebellare) del dito sul naso?\n"
                            "• Ci sono differenze fra entrambi i lati?"
                        ),
                    },
                    {
                        "id": "dn_chiusi",
                        "label": "Occhi chiusi",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere il test con gli occhi chiusi. Si conteggia il numero di volte "
                            "che il soggetto riesce a raggiungere l'obiettivo con movimenti precisi "
                            "e morbidi."
                        ),
                        "osservazioni": (
                            "Stesse osservazioni a occhi aperti. Differenza significativa fra "
                            "occhi aperti e occhi chiusi suggerisce dipendenza dalla vista per il "
                            "controllo del movimento (propriocezione debole)."
                        ),
                    },
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 5 — DISDIADOCOCINESIA (manuale + orale)
    # =========================================================================
    {
        "id": "disdiadococinesia",
        "label": "Disdiadococinesia",
        "icon": "✋",
        "gruppi": [
            {
                "id": "dita",
                "label": "Dita",
                "prove": [
                    {"id": "dita_sx", "label": "Mano sinistra", "scoring": "0-4"},
                    {"id": "dita_dx", "label": "Mano destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "mani",
                "label": "Mani",
                "prove": [
                    {"id": "mani_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "mani_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "piedi",
                "label": "Piedi",
                "prove": [
                    {"id": "piedi_sx", "label": "Sinistro", "scoring": "0-4"},
                    {"id": "piedi_dx", "label": "Destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "orale",
                "label": "Disdiadococinesia orale (registrare ripetizioni e secondi)",
                "prove": [
                    {"id": "orale_pa_rep", "label": "/pʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pa_sec", "label": "/pʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_ta_rep", "label": "/tʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_ta_sec", "label": "/tʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_ka_rep", "label": "/kʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_ka_sec", "label": "/kʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_pata_rep", "label": "/pʌtə/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pata_sec", "label": "/pʌtə/ — secondi", "scoring": "numerico"},
                    {"id": "orale_pataka_rep", "label": "/pʌtəkə/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pataka_sec", "label": "/pʌtəkə/ — secondi", "scoring": "numerico"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 6 — ORIENTAMENTO SPAZIALE + PROPRIOCEZIONE
    # =========================================================================
    {
        "id": "orientamento_propriocezione",
        "label": "Orientamento spaziale e propriocezione",
        "icon": "🧭",
        "gruppi": [
            {
                "id": "orientamento",
                "label": "Orientamento spaziale (sì/no)",
                "prove": [
                    {"id": "orient_dx_sx", "label": "Problemi di discriminazione destra/sinistra",
                     "scoring": "si_no"},
                    {"id": "orient_orientamento", "label": "Problemi di orientamento", "scoring": "si_no"},
                    {"id": "orient_spaziali", "label": "Problemi spaziali", "scoring": "si_no"},
                ],
            },
            {
                "id": "gold",
                "label": "Test di Gold (toccare e indicare)",
                "prove": [
                    {"id": "gold_dx_su_sx", "label": "Destra su sinistra", "scoring": "0-4"},
                    {"id": "gold_sx_su_dx", "label": "Sinistra su destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "specchio",
                "label": "Test dei movimenti a specchio",
                "prove": [
                    {"id": "specchio_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "specchio_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 7 — RIFLESSI DELLO SVILUPPO (la più grande)
    # =========================================================================
    {
        "id": "riflessi",
        "label": "Riflessi dello sviluppo",
        "icon": "🧬",
        "gruppi": [
            {
                "id": "rtac",
                "label": "Riflesso Tonico Asimmetrico del Collo (RTAC)",
                "prove": [
                    # ─── Test Standard (supino) — scala unica del manuale ───
                    # Le 4 caselle (Br Sx, Gb Sx, Br Dx, Gb Dx) condividono la
                    # stessa scala ufficiale del manuale 2019-2020 pag. 29.
                    {
                        "id": "rtac_std_br_sx",
                        "label": "Standard — Braccio sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard (supino). Collocare il soggetto in posizione supina. "
                            "Chiedere al paziente di rimanere il più fermo e rilassato possibile, "
                            "mentre noi facciamo girare lentamente la testa verso un lato prima e "
                            "poi l'altro. Fare sempre una pausa di almeno 3 secondi in seguito ad "
                            "ogni rotazione verso uno dei lati e verso la linea media."
                        ),
                        "osservazioni": (
                            "Spesso può accadere che risulti evidente il movimento/aumento del "
                            "tono flessore negli arti del lato occipitale. Osservare entrambi i "
                            "lati del corpo (braccia e gambe)."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento di dita, braccia o gambe",
                            1: "Movimento delle dita o lieve movimento del braccio o gamba frontali",
                            2: "Movimento del braccio di 3-5 cm o movimento di torsione del corpo",
                            3: "Movimento del braccio di più di 5 cm e/o movimento della gamba, o movimento del corpo seguendo la rotazione della testa",
                            4: "Allungamento del braccio e/o gamba frontale, o flessione del braccio occipitale",
                        },
                    },
                    {
                        "id": "rtac_std_gb_sx",
                        "label": "Standard — Gamba sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard (supino). Stessa procedura. Osservare la gamba sinistra "
                            "durante la rotazione della testa."
                        ),
                        "osservazioni": (
                            "Spesso può accadere che risulti evidente il movimento/aumento del "
                            "tono flessore negli arti del lato occipitale. Osservare entrambi i "
                            "lati del corpo (braccia e gambe)."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento di dita, braccia o gambe",
                            1: "Movimento delle dita o lieve movimento del braccio o gamba frontali",
                            2: "Movimento del braccio di 3-5 cm o movimento di torsione del corpo",
                            3: "Movimento del braccio di più di 5 cm e/o movimento della gamba, o movimento del corpo seguendo la rotazione della testa",
                            4: "Allungamento del braccio e/o gamba frontale, o flessione del braccio occipitale",
                        },
                    },
                    {
                        "id": "rtac_std_br_dx",
                        "label": "Standard — Braccio destro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard (supino). Stessa procedura. Osservare il braccio destro "
                            "durante la rotazione della testa."
                        ),
                        "osservazioni": (
                            "Spesso può accadere che risulti evidente il movimento/aumento del "
                            "tono flessore negli arti del lato occipitale. Osservare entrambi i "
                            "lati del corpo (braccia e gambe)."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento di dita, braccia o gambe",
                            1: "Movimento delle dita o lieve movimento del braccio o gamba frontali",
                            2: "Movimento del braccio di 3-5 cm o movimento di torsione del corpo",
                            3: "Movimento del braccio di più di 5 cm e/o movimento della gamba, o movimento del corpo seguendo la rotazione della testa",
                            4: "Allungamento del braccio e/o gamba frontale, o flessione del braccio occipitale",
                        },
                    },
                    {
                        "id": "rtac_std_gb_dx",
                        "label": "Standard — Gamba destra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard (supino). Stessa procedura. Osservare la gamba destra "
                            "durante la rotazione della testa."
                        ),
                        "osservazioni": (
                            "Spesso può accadere che risulti evidente il movimento/aumento del "
                            "tono flessore negli arti del lato occipitale. Osservare entrambi i "
                            "lati del corpo (braccia e gambe)."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento di dita, braccia o gambe",
                            1: "Movimento delle dita o lieve movimento del braccio o gamba frontali",
                            2: "Movimento del braccio di 3-5 cm o movimento di torsione del corpo",
                            3: "Movimento del braccio di più di 5 cm e/o movimento della gamba, o movimento del corpo seguendo la rotazione della testa",
                            4: "Allungamento del braccio e/o gamba frontale, o flessione del braccio occipitale",
                        },
                    },
                    # ─── Test di Ayres 1 (quadrupede) ───
                    {
                        "id": "rtac_ayres1_br_sx",
                        "label": "Test di Ayres (n.1) — Braccio sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Ayres 1 — dai 4-5 anni (Ayres AJ, 1972, 1980). "
                            "\"Mettiti sul pavimento in posizione quadrupede (come formando un tavolino).\" "
                            "Fare vedere la posizione se necessario. Spiegare al paziente di rimanere "
                            "il più fermo e rilassato possibile mentre noi gli giriamo la testa "
                            "verso un lato prima e poi verso l'altro. Fare una pausa dopo ogni "
                            "rotazione e nel raggiungere la linea media.\n\n"
                            "Nota: il RTAC può essere evidente anche in popolazione neurotipica "
                            "sotto i 7 anni; valutare l'intensità relativa. Sotto i 7 anni preferire "
                            "il test Standard supino. Un RTSC marcato può intralciare la posizione "
                            "quadrupede e condizionare il risultato."
                        ),
                        "osservazioni": (
                            "Il punteggio si riferisce al lato verso il quale viene girata la testa.\n"
                            "Osservare eventuali tracce dell'ATNR nella metà inferiore del corpo, "
                            "come la rotazione del bacino o il sollevamento del piede del lato occipitale."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia, spalle o bacino",
                            1: "Lieve flessione o movimento del braccio contro-laterale",
                            2: "Flessione evidente",
                            3: "Flessione di 45 gradi",
                            4: "Blocco totale del braccio contro-laterale",
                        },
                    },
                    {
                        "id": "rtac_ayres1_br_dx",
                        "label": "Test di Ayres (n.1) — Braccio destro",
                        "scoring": "0-4",
                        "istruzioni": "Test di Ayres 1 in posizione quadrupede. Osservare il braccio destro durante la rotazione della testa.",
                        "osservazioni": "Stesse osservazioni del braccio sinistro, lato opposto.",
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia, spalle o bacino",
                            1: "Lieve flessione o movimento del braccio contro-laterale",
                            2: "Flessione evidente",
                            3: "Flessione di 45 gradi",
                            4: "Blocco totale del braccio contro-laterale",
                        },
                    },
                    # ─── Test di Ayres 2 (quadrupede con braccia flesse) ───
                    {
                        "id": "rtac_ayres2_br_sx",
                        "label": "Test di Ayres (n.2) — Braccio sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Ayres 2 — solitamente per bambini dai 4-5 anni (Ayres AJ, "
                            "1972, 1980). Sotto i 7 anni il RTAC può essere evidente nella "
                            "popolazione normale, da considerare come indicatore.\n\n"
                            "\"Rimani in posizione quadrupede (come formando un tavolino), ma "
                            "fletti leggermente le braccia.\""
                        ),
                        "osservazioni": (
                            "Il punteggio si riferisce sempre al lato verso il quale viene "
                            "girata la testa.\n"
                            "Prestare attenzione perché se ci fosse un forte RTSC residuale, "
                            "questo aumenterebbe l'effetto della flessione del braccio in questo "
                            "test. Notare ogni movimento di compensazione del bacino in entrambi "
                            "i test di Ayres.\n"
                            "Un RT Simmetrico residuale può compromettere la capacità di "
                            "supportare la parte superiore del corpo in posizione quadrupede; "
                            "la presenza combinata di RTAC e RTSC può alterare i risultati."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia, spalle o bacino",
                            1: "Lieve flessione o movimento del braccio contro-laterale",
                            2: "Flessione evidente",
                            3: "Flessione di 45 gradi",
                            4: "Blocco totale del braccio contro-laterale",
                        },
                    },
                    {
                        "id": "rtac_ayres2_br_dx",
                        "label": "Test di Ayres (n.2) — Braccio destro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Ayres 2. Stessa procedura ma osservando il braccio destro "
                            "durante la rotazione della testa."
                        ),
                        "osservazioni": (
                            "Il punteggio si riferisce sempre al lato verso il quale viene "
                            "girata la testa. Prestare attenzione perché se ci fosse un forte "
                            "RTSC residuale, questo aumenterebbe l'effetto della flessione del "
                            "braccio in questo test. Notare ogni movimento di compensazione del "
                            "bacino in entrambi i test di Ayres."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia, spalle o bacino",
                            1: "Lieve flessione o movimento del braccio contro-laterale",
                            2: "Flessione evidente",
                            3: "Flessione di 45 gradi",
                            4: "Blocco totale del braccio contro-laterale",
                        },
                    },
                    # ─── Test di Hoff Schilder ───
                    {
                        "id": "rtac_schidler_br_sx",
                        "label": "Test di Schilder — Braccio sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Hoff Schilder — dai 7 anni (Critchley, 1970).\n\n"
                            "\"In piedi con i piedi insieme, braccia allungate davanti al corpo a "
                            "livello delle spalle e con i polsi rilassati. Chiudi gli occhi. "
                            "Girerò la tua testa verso ogni lato, ma devi lasciare le braccia "
                            "ferme dove sono.\"\n\n"
                            "Procedura: girare la testa lentamente verso un lato. Levare le mani "
                            "dalla testa e chiedere di mantenere la posizione con la testa girata "
                            "lateralmente. Pausa di 5-10 secondi. Lentamente ritornare alla linea "
                            "media. Pausa di 5-10 secondi. Ripetere verso l'altro lato. "
                            "Ripetere la sequenza 2-3 volte. Ripetere ancora ma girando la testa "
                            "velocemente (con attenzione)."
                        ),
                        "osservazioni": (
                            "• Osservare eventuali movimenti delle braccia nella direzione della "
                            "rotazione della testa.\n"
                            "• Notare se c'è qualche grado di insicurezza gravitazionale come "
                            "risultato della chiusura degli occhi o della rotazione della testa.\n"
                            "• C'è qualche modifica nell'equilibrio? Potrebbe essere il risultato "
                            "della stimolazione vestibolare o del RTAC nelle gambe che sposta il "
                            "centro d'equilibrio.\n"
                            "• L'incapacità per mantenere le braccia in parallelo con uno delle "
                            "braccia che si sposta verso l'esterno sarebbe risultato di una "
                            "disfunzione cerebellare sullo stesso lato; se entrambe le braccia "
                            "tendono a scendere in giù potrebbe esserci RTL."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento risultante della rotazione della testa",
                            1: "Leggera deviazione — 12-15°",
                            2: "Deviazione di 30°",
                            3: "Deviazione di 45°",
                            4: "Rotazione completa",
                        },
                    },
                    {
                        "id": "rtac_schidler_br_dx",
                        "label": "Test di Schilder — Braccio destro",
                        "scoring": "0-4",
                        "istruzioni": "Test di Schilder. Osservare il braccio destro durante la rotazione della testa.",
                        "osservazioni": "Stesse osservazioni del braccio sinistro, lato opposto.",
                        "scoring_specifico": {
                            0: "Nessun movimento risultante della rotazione della testa",
                            1: "Leggera deviazione — 12-15°",
                            2: "Deviazione di 30°",
                            3: "Deviazione di 45°",
                            4: "Rotazione completa",
                        },
                    },
                ],
            },
            {
                "id": "rtc_trasformato",
                "label": "Riflesso Tonico Trasformato del Collo (TTNR)",
                "prove": [
                    {
                        "id": "rtc_dx_sx",
                        "label": "Destra a sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "RIFLESSO TONICO TRASFORMATO DEL COLLO (RTTC / TTNR).\n\n"
                            "NB: importante ricordare che questo NON è un vero e proprio riflesso, "
                            "ma una \"posizione\" nella quale il bambino dovrebbe sentirsi comodo "
                            "una volta inibito il RTAC. Il termine RTTC è stato sviluppato da INPP.\n\n"
                            "Si colloca la persona in posizione prona, in recovery position. "
                            "Chi fa la valutazione girerà la testa verso il lato opposto e chiederà:\n"
                            "\"La posizione attuale della testa è più, meno o ugualmente comoda "
                            "rispetto a prima?\"\n\n"
                            "Se la risposta è MENO comoda, chiedere di:\n"
                            "\"Senza spostare la testa dalla posizione attuale, muovi gli arti in "
                            "modo che tu stia più comodo.\""
                        ),
                        "osservazioni": (
                            "In funzione di quanti arti raggiungono la posizione corretta "
                            "(speculare rispetto alla posizione iniziale), si assegna il punteggio."
                        ),
                        "scoring_specifico": {
                            0: "Posizione completamente a specchio (raggiunge tutti gli arti)",
                            1: "Numero di arti diversi rispetto alla posizione a specchio (1)",
                            2: "Numero di arti diversi rispetto alla posizione a specchio (2)",
                            3: "Numero di arti diversi rispetto alla posizione a specchio (3)",
                            4: "Resta nella posizione perché \"ugualmente comoda\"",
                        },
                    },
                    {
                        "id": "rtc_sx_dx",
                        "label": "Sinistra a destra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Stesso test ma partendo dal lato opposto. Posizione prona di "
                            "partenza con testa girata verso sinistra, valutazione del comfort "
                            "dopo rotazione della testa verso destra."
                        ),
                        "osservazioni": "Stesse osservazioni del lato dx-sx. Il punteggio si riferisce a quanti arti raggiungono la posizione corretta speculare.",
                        "scoring_specifico": {
                            0: "Posizione completamente a specchio (raggiunge tutti gli arti)",
                            1: "Numero di arti diversi rispetto alla posizione a specchio (1)",
                            2: "Numero di arti diversi rispetto alla posizione a specchio (2)",
                            3: "Numero di arti diversi rispetto alla posizione a specchio (3)",
                            4: "Resta nella posizione perché \"ugualmente comoda\"",
                        },
                    },
                ],
            },
            {
                "id": "rtsc",
                "label": "Riflesso Tonico Simmetrico del Collo (RTSC)",
                "prove": [
                    {
                        "id": "rtsc_piedi_sedere",
                        "label": "Coinvolgimento dei piedi o del sedere",
                        "scoring": "0-4",
                        "istruzioni": (
                            "RIFLESSO TONICO SIMMETRICO DEL COLLO (RTSC / STNR).\n\n"
                            "Test in posizione quadrupede — dai 5 anni (Holle, B. 1976).\n\n"
                            "\"Mantieni le braccia dritte e con il resto del corpo fermo, "
                            "lentamente muovi la testa in su come per guardare il soffitto, fai "
                            "una pausa (5 secondi), e poi, sempre lentamente abbassa la testa "
                            "come per guardarti fra le ginocchia.\""
                        ),
                        "osservazioni": (
                            "Osservare il sedere/piedi:\n"
                            "• Si alzano i piedi quando la testa va in giù?\n"
                            "• Movimento del bacino come compensazione del movimento della testa?\n"
                            "Capute ha indicato che la presenza durante l'infanzia in modo "
                            "significativo o per un tempo prolungato può essere un indicatore di "
                            "coinvolgimento estrapiramidale."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento di braccia, schiena o piedi in risposta al movimento della testa",
                            1: "Movimenti lievi delle braccia o del sedere",
                            2: "Evidente flessione delle braccia o movimento del bacino",
                            3: "Flessione delle braccia fino alla metà del percorso, o movimento del sedere",
                            4: "Cade per la flessione delle braccia o si siede sopra i piedi",
                        },
                    },
                    {
                        "id": "rtsc_braccia",
                        "label": "Coinvolgimento delle braccia",
                        "scoring": "0-4",
                        "istruzioni": "RTSC in posizione quadrupede. Osservare il movimento delle braccia mentre la testa si muove su/giù.",
                        "osservazioni": (
                            "Flessione delle braccia o abbassamento del bacino. Notare se si "
                            "inarca la schiena (compensazione del movimento della testa)."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia in risposta al movimento della testa",
                            1: "Movimenti lievi delle braccia",
                            2: "Evidente flessione delle braccia",
                            3: "Flessione delle braccia fino alla metà del percorso",
                            4: "Cade per la flessione delle braccia",
                        },
                    },
                    {
                        "id": "rtsc_carponi",
                        "label": "Evidenza durante il carponi",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Rivalutare con il carpone. Alcuni soggetti sono in grado di "
                            "compensare il riflesso in posizione statica, ma non ci riescono "
                            "quando iniziano a muoversi (carponi)."
                        ),
                        "osservazioni": (
                            "Guardare gli occhi: c'è convergenza o divergenza quando la testa va "
                            "su o giù? Osservare la fluidità del cammino carponi sotto carico "
                            "RTSC dinamico."
                        ),
                        "scoring_specifico": {
                            0: "Nessuna evidenza di RTSC durante il movimento carponi",
                            1: "Lieve evidenza, compensazione spontanea",
                            2: "Evidenza moderata durante il carpone",
                            3: "Forte alterazione del movimento carponi",
                            4: "Incapacità di mantenere la posizione carponi a causa del riflesso",
                        },
                    },
                ],
            },
            {
                "id": "galant",
                "label": "Riflesso Spinale di Galant",
                "prove": [
                    {
                        "id": "galant_sx",
                        "label": "Lato sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "RIFLESSO SPINALE DI GALANT.\n\n"
                            "Stimolare verso il basso lungo uno dei lati della spina (a 2 cm "
                            "dalla colonna) utilizzando un pennello.\n"
                            "Ripetere stimolando sull'altro lato.\n"
                            "Ripetere su entrambi i lati utilizzando la parte dura del pennello."
                        ),
                        "osservazioni": (
                            "Spesso il lato opposto del bacino si sposta in un movimento di "
                            "\"scansamento\". Questo deve essere valutato più come il risultato "
                            "di una condizione di ipersensibilità e non implica presenza del "
                            "riflesso."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento laterale del bacino (non confondere con una risposta di solletico)",
                            1: "Sensazione scomoda / Reazione emotiva",
                            2: "Lieve movimento muscolare o irrigidimento del bacino ipsilateralmente",
                            3: "Evidente spostamento del bacino ipsilateralmente",
                            4: "Il bacino si sposta di 45° o di più verso l'esterno",
                        },
                    },
                    {
                        "id": "galant_dx",
                        "label": "Lato destro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Stimolare verso il basso lungo il lato destro della spina (a 2 cm "
                            "dalla colonna) utilizzando un pennello. Ripetere usando la parte "
                            "dura del pennello."
                        ),
                        "osservazioni": (
                            "Spesso il lato opposto del bacino si sposta in un movimento di "
                            "\"scansamento\". Questo deve essere valutato più come il risultato "
                            "di una condizione di ipersensibilità e non implica presenza del "
                            "riflesso."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento laterale del bacino (non confondere con una risposta di solletico)",
                            1: "Sensazione scomoda / Reazione emotiva",
                            2: "Lieve movimento muscolare o irrigidimento del bacino ipsilateralmente",
                            3: "Evidente spostamento del bacino ipsilateralmente",
                            4: "Il bacino si sposta di 45° o di più verso l'esterno",
                        },
                    },
                ],
            },
            {
                "id": "rtl",
                "label": "Riflesso Tonico Labirintico del Collo (RTL)",
                "prove": [
                    {"id": "rtl_std", "label": "Test Standard", "scoring": "0-4"},
                    {"id": "rtl_piedi_aperti_flex", "label": "In piedi (occhi aperti) — Flessione", "scoring": "0-4"},
                    {"id": "rtl_piedi_aperti_ext", "label": "In piedi (occhi aperti) — Estensione", "scoring": "0-4"},
                    {"id": "rtl_piedi_chiusi_flex", "label": "In piedi (occhi chiusi) — Flessione", "scoring": "0-4"},
                    {"id": "rtl_piedi_chiusi_ext", "label": "In piedi (occhi chiusi) — Estensione", "scoring": "0-4"},
                    {"id": "rtl_ayres", "label": "Test di Ayres", "scoring": "0-4"},
                    {"id": "rtl_fiorentino", "label": "Test di Fiorentino", "scoring": "0-4"},
                ],
            },
            {
                "id": "moro",
                "label": "Riflesso di Moro",
                "prove": [
                    {"id": "moro_std", "label": "Test Standard", "scoring": "0-4"},
                    {"id": "moro_piede", "label": "Test in piede", "scoring": "0-4"},
                ],
            },
            {
                "id": "sostegno_oculare",
                "label": "Riflesso di Sostegno Cefalico Oculare",
                "prove": [
                    {"id": "sost_oc_sx", "label": "A sinistra", "scoring": "0-4"},
                    {"id": "sost_oc_dx", "label": "A destra", "scoring": "0-4"},
                    {"id": "sost_oc_indietro", "label": "All'indietro", "scoring": "0-4"},
                    {"id": "sost_oc_avanti", "label": "In avanti", "scoring": "0-4"},
                ],
            },
            {
                "id": "sostegno_labirintico",
                "label": "Riflesso di Sostegno Cefalico Labirintico",
                "prove": [
                    {"id": "sost_lb_sx", "label": "A sinistra", "scoring": "0-4"},
                    {"id": "sost_lb_dx", "label": "A destra", "scoring": "0-4"},
                    {"id": "sost_lb_indietro", "label": "All'indietro", "scoring": "0-4"},
                    {"id": "sost_lb_avanti", "label": "In avanti", "scoring": "0-4"},
                ],
            },
            {
                "id": "anfibio",
                "label": "Riflesso Anfibio",
                "prove": [
                    {"id": "anf_prono_sx", "label": "Prono — Lato sinistro", "scoring": "0-4"},
                    {"id": "anf_prono_dx", "label": "Prono — Lato destro", "scoring": "0-4"},
                    {"id": "anf_supino_sx", "label": "Supino — Lato sinistro", "scoring": "0-4"},
                    {"id": "anf_supino_dx", "label": "Supino — Lato destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "rotazione_seg",
                "label": "Riflesso di rotazione segmentaria",
                "prove": [
                    {"id": "rot_anche_sx", "label": "Dalle anche — Lato sinistro", "scoring": "0-4"},
                    {"id": "rot_anche_dx", "label": "Dalle anche — Lato destro", "scoring": "0-4"},
                    {"id": "rot_spalle_sx", "label": "Dalle spalle — Lato sinistro", "scoring": "0-4"},
                    {"id": "rot_spalle_dx", "label": "Dalle spalle — Lato destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "babinsky",
                "label": "Riflesso di Babinsky",
                "prove": [
                    {"id": "bab_sx", "label": "Piede sinistro", "scoring": "0-4"},
                    {"id": "bab_dx", "label": "Piede destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "addominale_landau",
                "label": "Riflessi Addominale e Landau",
                "prove": [
                    {"id": "addominale", "label": "Riflesso Addominale", "scoring": "0-4"},
                    {"id": "landau", "label": "Riflesso di Landau", "scoring": "0-4"},
                ],
            },
            {
                "id": "rooting",
                "label": "Riflesso di Ricerca / punti cardinali (Rooting)",
                "prove": [
                    {"id": "rooting_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "rooting_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "suzione",
                "label": "Riflessi di suzione",
                "prove": [
                    {"id": "suzione", "label": "Riflesso di suzione", "scoring": "0-4"},
                    {"id": "suzione_adulta", "label": "Riflesso di suzione adulta", "scoring": "scelta",
                     "opzioni": ["assente", "debole", "presente"]},
                ],
            },
            {
                "id": "prensile_mano",
                "label": "Riflesso Prensile (mano)",
                "prove": [
                    {"id": "prens_mano_sx", "label": "Mano sinistra", "scoring": "0-4"},
                    {"id": "prens_mano_dx", "label": "Mano destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "prensile_piede",
                "label": "Riflesso Prensile (piede)",
                "prove": [
                    {"id": "prens_piede_sx", "label": "Piede sinistro", "scoring": "0-4"},
                    {"id": "prens_piede_dx", "label": "Piede destro", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 8 — LATERALITÀ (preferenza laterale, no scoring numerico)
    # =========================================================================
    {
        "id": "lateralita",
        "label": "Lateralità",
        "icon": "↔️",
        "no_total": True,
        "gruppi": [
            {
                "id": "lat_piede",
                "label": "Lateralità di piede",
                "prove": [
                    {"id": "lat_piede_palla", "label": "Calciare la palla", "scoring": "lateralita"},
                    {"id": "lat_piede_calcio", "label": "Calcio sul pavimento", "scoring": "lateralita"},
                    {"id": "lat_piede_sedia", "label": "Salire sulla sedia", "scoring": "lateralita"},
                    {"id": "lat_piede_saltell", "label": "Saltellare su una gamba", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_mano",
                "label": "Lateralità di mano",
                "prove": [
                    {"id": "lat_mano_palla", "label": "Prendere una palla", "scoring": "lateralita"},
                    {"id": "lat_mano_applauso", "label": "Applauso", "scoring": "lateralita"},
                    {"id": "lat_mano_scrittura", "label": "Scrittura", "scoring": "lateralita"},
                    {"id": "lat_mano_telescopio", "label": "Telescopio", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_occhio_lontano",
                "label": "Lateralità di occhio (da lontano)",
                "prove": [
                    {"id": "lat_occ_lont_telescopio", "label": "Telescopio", "scoring": "lateralita"},
                    {"id": "lat_occ_lont_anello", "label": "Anello", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_occhio_vicino",
                "label": "Lateralità di occhio (da vicino)",
                "prove": [
                    {"id": "lat_occ_vic_buco", "label": "Buco nella carta", "scoring": "lateralita"},
                    {"id": "lat_occ_vic_anello", "label": "Anello", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_orecchio",
                "label": "Lateralità di orecchio",
                "prove": [
                    {"id": "lat_or_conchiglia", "label": "Conchiglia", "scoring": "lateralita"},
                    {"id": "lat_or_chiamata", "label": "Chiamata da dietro", "scoring": "lateralita"},
                    {"id": "lat_or_ascolto", "label": "Ascolto sotto il tavolo", "scoring": "lateralita"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 9 — TEST OCULO-MOTORI
    # =========================================================================
    {
        "id": "oculomotori",
        "label": "Test oculo-motori",
        "icon": "👁",
        "gruppi": [
            {
                "id": "oculo_base",
                "label": "Funzionalità oculo-motoria di base",
                "prove": [
                    {"id": "oc_fissazione", "label": "Difficoltà di fissazione", "scoring": "0-4"},
                    {"id": "oc_inseguimento", "label": "Difficoltà di inseguimento (tracking orizzontale)", "scoring": "0-4"},
                    {"id": "oc_occhio_mano", "label": "Inseguimento occhio-mano", "scoring": "0-4"},
                    {"id": "oc_conv_latente", "label": "Convergenza latente", "scoring": "0-4"},
                    {"id": "oc_div_latente", "label": "Divergenza latente", "scoring": "0-4"},
                ],
            },
            {
                "id": "oculo_lateralizzati",
                "label": "Test bilaterali",
                "prove": [
                    {"id": "oc_conv_sx", "label": "Convergenza — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_conv_dx", "label": "Convergenza — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_chius_sx", "label": "Chiusura indipendente — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_chius_dx", "label": "Chiusura indipendente — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_yoking_sx", "label": "Yoking — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_yoking_dx", "label": "Yoking — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_perif_sx", "label": "Visione periferica amplificata — Sinistra", "scoring": "0-4"},
                    {"id": "oc_perif_dx", "label": "Visione periferica amplificata — Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "oculo_accomodazione",
                "label": "Accomodazione",
                "prove": [
                    {"id": "oc_accomod", "label": "Ristabilimento della visione binoculare", "scoring": "0-4"},
                ],
            },
            {
                "id": "pupillare",
                "label": "Riflesso pupillare (annotazione testuale)",
                "prove": [
                    {"id": "pup_prima_sx", "label": "Prima stimolazione — Sx", "scoring": "testo"},
                    {"id": "pup_prima_dx", "label": "Prima stimolazione — Dx", "scoring": "testo"},
                    {"id": "pup_seconda_sx", "label": "Seconda stimolazione — Sx", "scoring": "testo"},
                    {"id": "pup_seconda_dx", "label": "Seconda stimolazione — Dx", "scoring": "testo"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 10 — TEST VISUO-PERCETTIVI
    # =========================================================================
    {
        "id": "visuo_percettivi",
        "label": "Test visuo-percettivi",
        "icon": "🎨",
        "gruppi": [
            {
                "id": "vp_principali",
                "label": "Test visuo-percettivi",
                "prove": [
                    {"id": "vp_stimulous_bound", "label": "Indicazioni di Stimulous bound", "scoring": "0-4"},
                    {"id": "vp_discriminazione", "label": "Problemi di discriminazione visiva", "scoring": "0-4"},
                    {"id": "vp_integrazione", "label": "Difficoltà di integrazione viso-motoria", "scoring": "0-4"},
                    {"id": "vp_spaziali", "label": "Problemi spaziali", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 11 — GOODENOUGH (Indice di Aston, disegno della figura umana)
    # =========================================================================
    {
        "id": "goodenough",
        "label": "Test di Goodenough (Indice di Aston)",
        "icon": "🧒",
        "no_total": True,
        "gruppi": [
            {
                "id": "good_score",
                "label": "Punteggio Goodenough",
                "prove": [
                    {"id": "good_punteggio", "label": "Punteggio totale (somma dei criteri)",
                     "scoring": "numerico"},
                    {"id": "good_eta_mentale", "label": "Età mentale corrispondente (anni;mesi)",
                     "scoring": "testo"},
                    {"id": "good_note", "label": "Note osservative sul disegno",
                     "scoring": "testo"},
                ],
            },
        ],
    },
]

# -----------------------------------------------------------------------------
# UTILITY: lookup veloci e calcolo punteggi
# -----------------------------------------------------------------------------

def itera_prove(scoring_filter: str | None = None):
    """
    Generatore: per ogni prova del protocollo, restituisce
    (sezione_id, gruppo_id, prova_dict).
    Se scoring_filter è dato, filtra solo le prove con quel tipo di scoring.
    """
    for sezione in PROTOCOLLO_INPP:
        for gruppo in sezione["gruppi"]:
            for prova in gruppo["prove"]:
                if scoring_filter is None or prova.get("scoring") == scoring_filter:
                    yield sezione["id"], gruppo["id"], prova


def calcola_punteggio_sezione(sezione_id: str, valori: dict) -> tuple[int, int]:
    """
    Calcola (punteggio_ottenuto, punteggio_massimo) per una sezione,
    considerando solo le prove con scoring '0-4'.

    Restituisce (0, 0) se la sezione non esiste o non ha prove 0-4.
    """
    sezione = next((s for s in PROTOCOLLO_INPP if s["id"] == sezione_id), None)
    if sezione is None or sezione.get("no_total"):
        return 0, 0

    ottenuto = 0
    massimo = 0
    for gruppo in sezione["gruppi"]:
        for prova in gruppo["prove"]:
            if prova.get("scoring") == "0-4":
                massimo += 4
                v = valori.get(prova["id"])
                if isinstance(v, (int, float)):
                    ottenuto += int(v)
    return ottenuto, massimo


def riepilogo_punteggi(valori: dict) -> dict[str, dict]:
    """
    Costruisce il riepilogo finale: per ogni sezione, punteggio e percentuale.

    Ritorna: {sezione_id: {"label": str, "ottenuto": int, "massimo": int, "perc": float}}
    """
    out: dict[str, dict] = {}
    for sezione in PROTOCOLLO_INPP:
        if sezione.get("no_total"):
            continue
        ott, mx = calcola_punteggio_sezione(sezione["id"], valori)
        if mx > 0:
            out[sezione["id"]] = {
                "label": sezione["label"],
                "ottenuto": ott,
                "massimo": mx,
                "perc": round(100.0 * ott / mx, 1),
            }
    return out


def conta_prove_totali() -> int:
    """Numero totale di prove nel protocollo (utile per debug/info)."""
    return sum(1 for _ in itera_prove())
