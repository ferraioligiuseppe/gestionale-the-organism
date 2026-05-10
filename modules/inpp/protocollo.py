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
                "label": "Dita (Test delle opposizioni pollice-resto delle dita)",
                "prove": [
                    {
                        "id": "dita_sx",
                        "label": "Mano sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test delle opposizioni pollice-resto delle dita (Dai 5-6 anni — "
                            "Holt 1991, 1993; dai 5-7 — Kohen-Raz).\n\n"
                            "\"In piede con i piedi insieme, piegare il braccio a livello del "
                            "gomito girando il palmo verso il viso e fare un cerchio con pollice "
                            "e indice a livello degli occhi. Ripetere 5 volte aprendo e "
                            "chiudendo il cerchio con pollice e indice e poi continuare nello "
                            "stesso modo con ogni altro dito della mano facendo un cerchio con "
                            "il pollice. Poi ripetere con l'altra mano.\" (Dimostrare).\n\n"
                            "Il cervelletto è coinvolto anche nel controllo e la precisione dei "
                            "movimenti fini."
                        ),
                        "osservazioni": (
                            "• Ci sono problemi con l'accuratezza dei movimenti di uno o più dita?\n"
                            "  In caso affermativo, quali? Si possono numerare per annotare quale "
                            "dito ha problemi in ogni mano.\n"
                            "• Ci sono movimenti \"a specchio\" nell'altra mano?\n"
                            "• Ci sono movimenti con la bocca?\n\n"
                            "Il movimento delle dita potrebbe essere disturbato da un riflesso "
                            "prensile ancora presente ma anche dalla risposta di Babkin o dei "
                            "riflessi orali. Spesso c'è una associazione con il linguaggio — in "
                            "particolare con i problemi di pronuncia — e con i movimenti fini "
                            "necessari per la scrittura."
                        ),
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve grado di difficoltà per effettuare i movimenti delle dita in modo fluido e senza coinvolgimento di altri movimenti",
                            2: "Difficoltà moderata",
                            3: "Difficoltà marcata",
                            4: "Incapace di svolgere movimenti indipendenti delle dita",
                        },
                    },
                    {
                        "id": "dita_dx",
                        "label": "Mano destra",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test sull'altra mano.",
                        "osservazioni": "Stesse osservazioni della mano sinistra.",
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve grado di difficoltà",
                            2: "Difficoltà moderata",
                            3: "Difficoltà marcata",
                            4: "Incapace di svolgere movimenti indipendenti delle dita",
                        },
                    },
                ],
            },
            {
                "id": "mani",
                "label": "Mani (dai 7-8 anni — Accardo PJ)",
                "prove": [
                    {
                        "id": "mani_sx",
                        "label": "Sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "\"In piede con i piedi o talloni insieme. Colloca le mani davanti "
                            "a te, con il palmo di una di loro guardando verso il soffitto, "
                            "l'altra guardando verso il pavimento. Gira entrambe le mani in "
                            "modo che guardino verso il lato opposto. Ripeti il movimento più "
                            "volte.\""
                        ),
                        "osservazioni": (
                            "• Riesce a fare movimenti indipendenti (e opposti) con ognuna "
                            "delle mani?\n"
                            "• Appaiono movimenti speculari nell'altra mano o indicatori di "
                            "stress (viso, bocca, equilibrio…)?"
                        ),
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve grado di difficoltà nel movimento alternato",
                            2: "Difficoltà moderata o lievi movimenti speculari",
                            3: "Difficoltà marcata o movimenti speculari evidenti",
                            4: "Incapace di svolgere movimenti indipendenti delle mani",
                        },
                    },
                    {
                        "id": "mani_dx",
                        "label": "Destra",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test, specificare se la difficoltà è maggiore con la mano destra o sinistra.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve grado di difficoltà",
                            2: "Difficoltà moderata o lievi movimenti speculari",
                            3: "Difficoltà marcata o movimenti speculari evidenti",
                            4: "Incapace di svolgere movimenti indipendenti delle mani",
                        },
                    },
                ],
            },
            {
                "id": "piedi",
                "label": "Piedi",
                "prove": [
                    {
                        "id": "piedi_sx",
                        "label": "Sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "\"Seduto in una sedia. Appoggiare un piede sul pavimento. "
                            "Sollevare leggermente l'altro piede. Fare un movimento alternato "
                            "alzando ed abbassando il piede a livello della caviglia.\" "
                            "(Dimostrare). Ripetere con l'altro piede.\n\n"
                            "Sollevare entrambi i piedi del pavimento e ripetere il movimento "
                            "in modo alternato con entrambi i piedi. (Dimostrare)."
                        ),
                        "osservazioni": (
                            "• È in grado di fare il movimento di ogni piede separatamente?\n"
                            "• Appaiono movimenti speculari?\n"
                            "• È il movimento uguale in entrambi i piedi?\n"
                            "• È possibile per il soggetto fare movimenti opposti?"
                        ),
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve difficoltà nel movimento alternato",
                            2: "Difficoltà moderata o lievi movimenti speculari",
                            3: "Difficoltà marcata o movimenti speculari evidenti",
                            4: "Incapace di svolgere movimenti indipendenti dei piedi",
                        },
                    },
                    {
                        "id": "piedi_dx",
                        "label": "Destro",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test, specificare se la difficoltà è maggiore con il piede destro o sinistro.",
                        "osservazioni": "Stesse osservazioni del piede sinistro.",
                        "scoring_specifico": {
                            0: "Nulla da segnalare",
                            1: "Lieve difficoltà nel movimento alternato",
                            2: "Difficoltà moderata o lievi movimenti speculari",
                            3: "Difficoltà marcata o movimenti speculari evidenti",
                            4: "Incapace di svolgere movimenti indipendenti dei piedi",
                        },
                    },
                ],
            },
            {
                "id": "orale",
                "label": "Disdiadococinesia orale (registrare ripetizioni e secondi)",
                "prove": [
                    # Il manuale 2019-2020 non descrive questa sezione nelle pagine
                    # teoriche; struttura presa dal Formulario INPPA01IT rev. 01/22.
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
                "label": "Tests cognitivo-spaziali (sì/no)",
                "prove": [
                    {
                        "id": "orient_dx_sx",
                        "label": "Problemi di discriminazione destra/sinistra",
                        "scoring": "si_no",
                        "istruzioni": (
                            "Problemi di discriminazione Destra/Sinistra (dai 7 anni).\n\n"
                            "\"In piedi nel centro della stanza, piedi insieme. Girati di un "
                            "quarto di giro verso destra o sinistra quando io dirò la parola "
                            "'destra' o 'sinistra'.\"\n\n"
                            "L'istruttore indicherà \"sinistra\" \"destra\" in sequenza random "
                            "diverse volte (10).\n\n"
                            "Se questo test viene superato, chiedere di indicare il proprio "
                            "orecchio destro/sinistro, piede, occhio, ecc (consapevolezza "
                            "soggettiva). Se supera anche questo passaggio, chiedere di "
                            "indicare l'orecchio destro/sinistro dell'esaminatore, poi mano, "
                            "piede, ecc."
                        ),
                        "osservazioni": (
                            "Questo test va punteggiato come \"giusto\" o \"sbagliato\". "
                            "Segnalare a che livello di complessità sono iniziate le difficoltà "
                            "(consapevolezza oggettiva o soggettiva di destra o sinistra, ad "
                            "esempio)."
                        ),
                    },
                    {
                        "id": "orient_orientamento",
                        "label": "Problemi di orientamento",
                        "scoring": "si_no",
                        "istruzioni": (
                            "Problemi di Orientamento (test della bussola, dai 7 anni).\n\n"
                            "In piedi nel centro della stanza, piedi insieme.\n\n"
                            "L'esaminatore indicherà la posizione immaginaria dei 4 punti "
                            "cardinali nella stanza (nord, sud, est, ovest). Verrà chiesto di "
                            "girarsi verso ognuno di quei 4 punti ogni volta che li senta dalla "
                            "voce dell'esaminatore. Essi dovranno essere nominati in ordine "
                            "sparso in modo che non possa essere anticipata la direzione."
                        ),
                        "osservazioni": "Questo test va punteggiato come \"giusto\" o \"sbagliato\".",
                    },
                    {
                        "id": "orient_spaziali",
                        "label": "Problemi spaziali",
                        "scoring": "si_no",
                        "istruzioni": (
                            "Problemi Spaziali (Test dell'orologio).\n\n"
                            "Non adatto per bambini sotto gli 8 anni. Controllare sempre che "
                            "sia in grado di leggere l'orologio analogico prima di provare il test.\n\n"
                            "L'esaminatore farà vedere in che modo vorrà che il bambino faccia "
                            "finta di essere un orologio utilizzando le mani per indicare "
                            "l'ora.\n\n"
                            "\"Stai in piedi con i piedi insieme e guardando verso di me.\"\n\n"
                            "L'esaminatore allora proporrà diverse \"ore\" che il bambino dovrà "
                            "indicare usando le sue mani al posto delle lancette, iniziando da "
                            "quelle più semplici (dodici in punto) e rendendo il compito sempre "
                            "più complesso. (6 volte)."
                        ),
                        "osservazioni": (
                            "Il test va registrato come \"giusto\" o \"sbagliato\". L'esaminatore "
                            "dovrebbe indicare a che livello di complessità sono iniziati gli "
                            "errori nel caso a inizio le risposte erano adeguate."
                        ),
                    },
                ],
            },
            {
                "id": "gold",
                "label": "Test di Gold (toccare e indicare)",
                "prove": [
                    # Il manuale 2019-2020 non descrive il Test di Gold nelle pagine
                    # teoriche; struttura presa dal Formulario INPPA01IT rev. 01/22.
                    {"id": "gold_dx_su_sx", "label": "Destra su sinistra", "scoring": "0-4"},
                    {"id": "gold_sx_su_dx", "label": "Sinistra su destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "specchio",
                "label": "Test dei movimenti a specchio",
                "prove": [
                    # Idem: non descritto nelle pagine teoriche del manuale.
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
                    {
                        "id": "rtl_std",
                        "label": "Test Standard",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard in posizione supina. Collocare il soggetto nella "
                            "posizione del test e spiegare:\n\n"
                            "\"Fra qualche istante abbasserò la tua testa di qualche centimetro "
                            "senza mai lasciarla cadere o colpire il pavimento; per favore rimani "
                            "il più rilassato possibile.\"\n\n"
                            "Lentamente estendere il collo abbassando la testa finché sarà "
                            "soltanto appena oltre il livello della spina, e mantenere questa "
                            "posizione durante 5-10 secondi."
                        ),
                        "osservazioni": (
                            "Osservare le gambe e la parte inferiore del corpo come risultato "
                            "dell'estensione della testa."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento (o aumento del tono muscolare) nella parte inferiore del corpo come risultato dell'estensione della testa",
                            1: "Leggero movimento delle gambe quando si abbassa la testa",
                            2: "Movimento evidente delle gambe",
                            3: "Estensione parziale delle gambe",
                            4: "Completa estensione delle gambe",
                        },
                    },
                    {
                        "id": "rtl_piedi_aperti_flex",
                        "label": "In piedi (occhi aperti) — Flessione",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test in piedi per il RTL (dai 6 anni — Blythe P).\n\n"
                            "\"Mantenendo il resto del corpo fermo, alza lentamente la testa come "
                            "per guardare il soffitto. Fai una pausa (5-10 secondi). Adesso, "
                            "lentamente abbassa la testa come per guardare in giù. Fai una pausa\" "
                            "(5-10 secondi).\n\n"
                            "Ripetere 2-3 volte. Prima fare il test con gli occhi aperti."
                        ),
                        "osservazioni": (
                            "Segnalare qualsiasi cambiamento del tono muscolare in particolare "
                            "della sezione inferiore del corpo (gambe) come effetto della "
                            "estensione o flessione della testa. Annotare specificamente il "
                            "punteggio per estensione o flessione."
                        ),
                        "scoring_specifico": {
                            0: "Nessuna reazione del corpo come risposta alla flessione, estensione della testa o allo spostamento attraverso il piano frontale",
                            1: "Lieve dondolio o cambiamento nel tono muscolare della parte posteriore delle gambe",
                            2: "Evidente dondolio o cambiamento del tono muscolare delle gambe per compensare l'equilibrio",
                            3: "Vicino a perdere l'equilibrio, aggiustamento posturale a livello del bacino e/o cambiamento nel tono muscolare. Notare se c'è prensione con le dita dei piedi",
                            4: "Perdita dell'equilibrio come conseguenza del movimento della testa",
                        },
                    },
                    {
                        "id": "rtl_piedi_aperti_ext",
                        "label": "In piedi (occhi aperti) — Estensione",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test, valutare la fase di estensione (testa alzata verso il soffitto).",
                        "osservazioni": "Stesse osservazioni del test in flessione.",
                        "scoring_specifico": {
                            0: "Nessuna reazione del corpo come risposta alla flessione, estensione della testa o allo spostamento attraverso il piano frontale",
                            1: "Lieve dondolio o cambiamento nel tono muscolare della parte posteriore delle gambe",
                            2: "Evidente dondolio o cambiamento del tono muscolare delle gambe per compensare l'equilibrio",
                            3: "Vicino a perdere l'equilibrio, aggiustamento posturale a livello del bacino e/o cambiamento nel tono muscolare",
                            4: "Perdita dell'equilibrio come conseguenza del movimento della testa",
                        },
                    },
                    {
                        "id": "rtl_piedi_chiusi_flex",
                        "label": "In piedi (occhi chiusi) — Flessione",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Ripetere il test in piedi con gli occhi chiusi. Osservare se "
                            "appaiono i riflessi come compensazione per un insufficiente "
                            "aggiustamento vestibolare."
                        ),
                        "osservazioni": "Stesse osservazioni del test a occhi aperti.",
                        "scoring_specifico": {
                            0: "Nessuna reazione del corpo",
                            1: "Lieve dondolio o cambiamento nel tono muscolare delle gambe",
                            2: "Evidente dondolio o cambiamento del tono muscolare delle gambe",
                            3: "Vicino a perdere l'equilibrio, aggiustamento posturale del bacino",
                            4: "Perdita dell'equilibrio",
                        },
                    },
                    {
                        "id": "rtl_piedi_chiusi_ext",
                        "label": "In piedi (occhi chiusi) — Estensione",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test a occhi chiusi, valutare la fase di estensione.",
                        "osservazioni": "Stesse osservazioni del test precedente.",
                        "scoring_specifico": {
                            0: "Nessuna reazione del corpo",
                            1: "Lieve dondolio o cambiamento nel tono muscolare delle gambe",
                            2: "Evidente dondolio o cambiamento del tono muscolare delle gambe",
                            3: "Vicino a perdere l'equilibrio, aggiustamento posturale del bacino",
                            4: "Perdita dell'equilibrio",
                        },
                    },
                    {
                        "id": "rtl_ayres",
                        "label": "Test di Ayres",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Ayres per il RTL in flessione (opzionale).\n\n"
                            "Utilizzando uno sgabello basso, chiedere al soggetto di distendersi "
                            "prono con l'addome supportato dallo stesso sgabello, e sollevare la "
                            "testa mentre mantiene braccia e gambe in estensione."
                        ),
                        "osservazioni": (
                            "Riescono a mantenere l'estensione degli arti durante alcuni secondi "
                            "oppure qualche parte del corpo inizia a flettersi? Se il RTL in "
                            "flessione è molto presente, il soggetto farà molta fatica a "
                            "mantenere il tono estensore contro la forza della gravità, e testa, "
                            "braccia e/o gambe inizieranno a flettersi.\n\n"
                            "Questo test si punteggia soltanto 0 o 4."
                        ),
                        "scoring_specifico": {
                            0: "Mantiene l'estensione degli arti — RTL in flessione assente",
                            4: "Testa, braccia e/o gambe iniziano a flettersi — RTL in flessione presente",
                        },
                    },
                    {
                        "id": "rtl_fiorentino",
                        "label": "Test di Fiorentino",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test di Fiorentino per il RTL (in flessione).\n\n"
                            "\"Solleva la testa come per guardarti i piedi.\"\n\n"
                            "L'esaminatore poggia un braccio sotto le ginocchia del soggetto in "
                            "modo da poter percepire se c'è qualche cambiamento (aumento della "
                            "flessione) nelle ginocchia."
                        ),
                        "osservazioni": (
                            "Notare se si piegano le ginocchia dopo la flessione della testa, o "
                            "rigidità dopo l'estensione. Osservare se ci sono cambiamenti di tono "
                            "muscolare nella parte posteriore della testa quando si flettono o "
                            "estendono le ginocchia."
                        ),
                        "scoring_specifico": {
                            0: "Nessun cambiamento nel tono muscolare",
                            1: "Graduale aumento della flessione delle ginocchia (lieve)",
                            2: "Graduale aumento della flessione delle ginocchia (moderato)",
                            3: "Graduale aumento della flessione delle ginocchia (marcato)",
                            4: "Flessione completa delle ginocchia",
                        },
                    },
                ],
            },
            {
                "id": "moro",
                "label": "Riflesso di Moro",
                "prove": [
                    {
                        "id": "moro_std",
                        "label": "Test Standard",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test Standard per il riflesso di Moro (adattamento di Goddard "
                            "Blythe per popolazione adulta).\n\n"
                            "\"Fra qualche istante, lascerò cadere leggermente la tua testa "
                            "all'indietro. Non ti preoccupare perché ti prometto che non "
                            "picchierai con il pavimento ne ti farai male. Voglio che tu "
                            "mantenga il resto del corpo il più fermo possibile nella posizione "
                            "attuale.\"\n\n"
                            "La valutazione è come per il test standard del RTL ma con le "
                            "braccia sollevate e flesse. La testa viene lasciata andare "
                            "velocemente e in modo inatteso in questo test."
                        ),
                        "osservazioni": (
                            "Riescono a mantenere la posizione delle braccia quando la testa va "
                            "indietro o c'è abduzione degli arti superiori?\n\n"
                            "Se il soggetto è incapace di rilassarsi e \"lasciare andare\" la "
                            "testa all'indietro, questo potrebbe considerarsi un indicatore che "
                            "il riflesso di Moro è presente."
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle braccia, nessun indicatore di stress o disagio",
                            1: "Lieve movimento delle braccia verso l'esterno o blocco momentaneo",
                            2: "Evidente movimento delle braccia. Si sente \"scomodo\" dopo il test",
                            3: "Abduzione parziale e sensazione di fastidio per il test",
                            4: "Abduzione delle braccia e/o evidente stress causato dal test",
                        },
                    },
                    {
                        "id": "moro_piede",
                        "label": "Test in piede",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Test in piedi per il Riflesso di Moro (Bennett, R., Clarke, S. & "
                            "Rowston, J.).\n\n"
                            "Nota: questo test in piedi non è un test genericamente accettato "
                            "(dal punto di vista medico). Medicamente il riflesso di Moro viene "
                            "valutato in posizione supina, solitamente da neonato. Il test in "
                            "piedi è stato elaborato da terapisti formati con INPP quando è "
                            "diventato evidente che il test standard spesso non era sufficiente "
                            "per elicitare un riflesso di Moro attivo in individui adulti.\n\n"
                            "In bambini più grandi e adulti che presentano problemi posturali, "
                            "il riflesso di Moro potrebbe risultare evidente soltanto nel test "
                            "in piedi, in una condizione di maggiore stress posturale.\n\n"
                            "\"Collocarsi in posizione per il test. Quando ti farò il segnale, "
                            "voglio che ti lasci cadere all'indietro come un tronco in modo che "
                            "io possa prenderti con le mie braccia; ti assicuro che non ti farò "
                            "cadere.\""
                        ),
                        "osservazioni": (
                            "In bambini più grandi e adulti, la ritenzione del riflesso di Moro "
                            "potrebbe essere secondaria a difficoltà posturali sottostanti, e "
                            "quando l'equilibrio e la postura migliorano, il riflesso di Moro "
                            "diminuisce."
                        ),
                        "scoring_specifico": {
                            0: "Nessuna reazione, le braccia rimangono nella posizione del test",
                            1: "Minima abduzione delle braccia",
                            2: "Evidente apertura parziale delle braccia, cambiamento nel ritmo respiratorio",
                            3: "Le braccia si aprono un 75%, e/o si sente \"scosso\" dal test",
                            4: "Completa apertura delle braccia e/o forte stress provocato dal test",
                        },
                    },
                ],
            },
            {
                "id": "sostegno_oculare",
                "label": "Riflesso di Sostegno Cefalico Oculare (Raddrizzamento Cervicale)",
                "prove": [
                    {
                        "id": "sost_oc_sx",
                        "label": "A sinistra",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": (
                            "Posizionare il soggetto (seduto con le gambe allungate davanti) ad "
                            "alcuni passi di distanza di un oggetto collocato all'altezza degli "
                            "occhi. L'esaminatore poggia i palmi delle mani sugli omoplati e "
                            "suggerisce:\n\n"
                            "\"Guarda l'oggetto (collocato in posizione centrale e al livello "
                            "degli occhi) davanti a te. Fra qualche istante ti sposterò da un "
                            "lato all'altro e anche in avanti e indietro. Voglio che per favore "
                            "tu guardi l'oggetto durante tutto il tempo.\"\n\n"
                            "Lentamente inclinare il corpo in 3 tappe verso uno dei lati, "
                            "procedendo in spostamenti di 10-15 gradi. Non andare oltre i 45 "
                            "gradi. Fare una pausa di 2 secondi dopo ogni movimento. Ritornare "
                            "alla posizione centrale sempre in 3 tappe e facendo pause di 2 "
                            "secondi. Ripetere verso il lato opposto. Ripetere l'intera "
                            "procedura avanti e indietro."
                        ),
                        "osservazioni": (
                            "La testa dovrebbe correggere automaticamente la posizione "
                            "mantenendosi sulla linea mediana a prescindere dell'alterazione "
                            "della posizione del corpo, ovvero la testa si sposta verso il lato "
                            "opposto del corpo per mantenersi nella posizione centrale."
                        ),
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo (raddrizzamento cervicale presente)",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo o eccessiva compensazione nel recupero della linea mediana",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_oc_dx",
                        "label": "A destra",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test, inclinazione verso destra. Stessa procedura in 3 tappe.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo o eccessiva compensazione",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_oc_indietro",
                        "label": "All'indietro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test, inclinazione del corpo all'indietro in 3 tappe.",
                        "osservazioni": "Stesse osservazioni laterali, applicate alla direzione antero-posteriore.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_oc_avanti",
                        "label": "In avanti",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test, inclinazione del corpo in avanti in 3 tappe.",
                        "osservazioni": "Stesse osservazioni precedenti.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                ],
            },
            {
                "id": "sostegno_labirintico",
                "label": "Riflesso di Sostegno Cefalico Labirintico (Raddrizzamento Cervicale)",
                "prove": [
                    {
                        "id": "sost_lb_sx",
                        "label": "A sinistra",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": (
                            "\"Adesso ripeteremmo il test precedente. Questa volta voglio che tu "
                            "ricordi dove sta l'oggetto, chiuda gli occhi ed immagini che stai "
                            "sempre guardandolo.\"\n\n"
                            "Stessa procedura del test oculare ma con occhi chiusi. Inclinazione "
                            "verso sinistra in 3 tappe."
                        ),
                        "osservazioni": (
                            "Senza il supporto visivo, il sistema vestibolare-labirintico è "
                            "l'unico riferimento. Il raddrizzamento cervicale dovrebbe "
                            "comunque mantenere la testa allineata."
                        ),
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo o eccessiva compensazione",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_lb_dx",
                        "label": "A destra",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test ad occhi chiusi, inclinazione verso destra.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_lb_indietro",
                        "label": "All'indietro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test ad occhi chiusi, inclinazione del corpo all'indietro.",
                        "osservazioni": "Stesse osservazioni precedenti.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                    {
                        "id": "sost_lb_avanti",
                        "label": "In avanti",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test ad occhi chiusi, inclinazione del corpo in avanti.",
                        "osservazioni": "Stesse osservazioni precedenti.",
                        "scoring_specifico": {
                            0: "La testa si muove nella stessa proporzione e opposta direzione rispetto allo spostamento del corpo",
                            1: "Leggero spostamento della testa nella stessa direzione del corpo",
                            2: "La testa rimane in linea con il corpo, o \"sovracompensa\"",
                            3: "La testa supera lievemente al di là della linea del corpo",
                            4: "La testa cade al di là della linea del corpo come una \"bambola di pezza\"",
                        },
                    },
                ],
            },
            {
                "id": "anfibio",
                "label": "Riflesso Anfibio",
                "prove": [
                    {
                        "id": "anf_prono_sx",
                        "label": "Prono — Lato sinistro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": (
                            "Valutare in posizione prona e supina. Lentamente sollevare dalla "
                            "parte inferiore uno dei lati del bacino. La gamba dovrebbe flettersi "
                            "a livello del ginocchio quando si alza leggermente il bacino dello "
                            "stesso lato. Ripetere sull'altro lato."
                        ),
                        "osservazioni": (
                            "Può risultare difficile differenziare un punteggio di 2 o 3 nella "
                            "valutazione di questo riflesso. Trattandosi di un riflesso "
                            "POSTURALE: 0 vuole dire che il riflesso è presente (gamba si flette "
                            "correttamente), 4 che è assente (gamba rigida)."
                        ),
                        "scoring_specifico": {
                            0: "Flessione della gamba a livello del ginocchio nel lato stimolato (riflesso presente)",
                            1: "La gamba non si flette",
                            2: "Rotola come un tronco",
                            3: "Rotola come un tronco (più marcato)",
                            4: "La gamba si stende rigida (riflesso assente)",
                        },
                    },
                    {
                        "id": "anf_prono_dx",
                        "label": "Prono — Lato destro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test in posizione prona, sollevamento del bacino dal lato destro.",
                        "osservazioni": "Stesse osservazioni del lato sinistro. Riflesso posturale.",
                        "scoring_specifico": {
                            0: "Flessione della gamba a livello del ginocchio nel lato stimolato (riflesso presente)",
                            1: "La gamba non si flette",
                            2: "Rotola come un tronco",
                            3: "Rotola come un tronco (più marcato)",
                            4: "La gamba si stende rigida (riflesso assente)",
                        },
                    },
                    {
                        "id": "anf_supino_sx",
                        "label": "Supino — Lato sinistro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test in posizione supina. Sollevamento del bacino dal lato sinistro.",
                        "osservazioni": "Stesse osservazioni del test in posizione prona.",
                        "scoring_specifico": {
                            0: "Flessione della gamba a livello del ginocchio nel lato stimolato (riflesso presente)",
                            1: "La gamba non si flette",
                            2: "Rotola come un tronco",
                            3: "Rotola come un tronco (più marcato)",
                            4: "La gamba si stende rigida (riflesso assente)",
                        },
                    },
                    {
                        "id": "anf_supino_dx",
                        "label": "Supino — Lato destro",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": "Stesso test in posizione supina, sollevamento del bacino dal lato destro.",
                        "osservazioni": "Stesse osservazioni precedenti.",
                        "scoring_specifico": {
                            0: "Flessione della gamba a livello del ginocchio nel lato stimolato (riflesso presente)",
                            1: "La gamba non si flette",
                            2: "Rotola come un tronco",
                            3: "Rotola come un tronco (più marcato)",
                            4: "La gamba si stende rigida (riflesso assente)",
                        },
                    },
                ],
            },
            {
                "id": "rotazione_seg",
                "label": "Riflessi di Rotazione Segmentaria",
                "prove": [
                    {
                        "id": "rot_anche_sx",
                        "label": "Dalle anche — Lato sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Dal Bacino. Lentamente flettere una gamba a livello del ginocchio "
                            "e spostarla attraverso il corpo in angolo retto. Fermarsi nel caso "
                            "ci sia una risposta di dolore o resistenza.\n\n"
                            "Il movimento di rotazione della parte inferiore del corpo dovrebbe "
                            "attivare un movimento della parte superiore del corpo che risulta "
                            "nella rotazione completa del tronco."
                        ),
                        "osservazioni": "Osservare la sequenzialità della rotazione e l'attivazione della parte superiore del corpo come risposta al movimento del bacino.",
                        "scoring_specifico": {
                            0: "Il corpo rotola in un movimento segmentato e sequenziale",
                            1: "Si alza la spalla ma non c'è la completa rotazione di tutta la parte superiore del corpo",
                            2: "Reazione inadeguata della parte superiore del corpo",
                            3: "Rotola come un tronco",
                            4: "Nessuna attivazione della parte superiore del corpo",
                        },
                    },
                    {
                        "id": "rot_anche_dx",
                        "label": "Dalle anche — Lato destro",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test, gamba destra spostata attraverso il corpo.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "Il corpo rotola in un movimento segmentato e sequenziale",
                            1: "Si alza la spalla ma non c'è la completa rotazione di tutta la parte superiore del corpo",
                            2: "Reazione inadeguata della parte superiore del corpo",
                            3: "Rotola come un tronco",
                            4: "Nessuna attivazione della parte superiore del corpo",
                        },
                    },
                    {
                        "id": "rot_spalle_sx",
                        "label": "Dalle spalle — Lato sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Dalle Spalle. In posizione supina, con le braccia lungo il corpo e "
                            "le gambe distese, chiedere al soggetto di flettere il braccio del "
                            "lato opposto all'esaminatore. Lentamente sollevare da sotto la "
                            "spalla del braccio flesso e portare il corpo fino alla linea "
                            "mediana. Tutto ciò dovrebbe far iniziare un movimento del bacino e "
                            "la flessione del ginocchio dello stesso lato per iniziare il "
                            "movimento di rotazione."
                        ),
                        "osservazioni": "Osservare la sequenzialità della rotazione dall'alto verso il basso.",
                        "scoring_specifico": {
                            0: "Il corpo inizia la rotazione (parte inferiore si attiva e segue)",
                            1: "Attivazione della parte inferiore del corpo ma rotola solo parzialmente",
                            2: "Attivazione della parte inferiore del corpo ma non inizia il movimento",
                            3: "Rotola come un tronco",
                            4: "Nessuna risposta nella parte inferiore del corpo",
                        },
                    },
                    {
                        "id": "rot_spalle_dx",
                        "label": "Dalle spalle — Lato destro",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test, sollevamento dalla spalla del lato destro.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "Il corpo inizia la rotazione",
                            1: "Attivazione della parte inferiore del corpo ma rotola solo parzialmente",
                            2: "Attivazione della parte inferiore del corpo ma non inizia il movimento",
                            3: "Rotola come un tronco",
                            4: "Nessuna risposta nella parte inferiore del corpo",
                        },
                    },
                ],
            },
            {
                "id": "babinsky",
                "label": "Riflesso di Babinsky",
                "prove": [
                    {
                        "id": "bab_sx",
                        "label": "Piede sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Stimolare la pianta del piede sinistro lungo il bordo laterale "
                            "dalla calcagno verso le dita.\n\n"
                            "Raramente questo test può elicitare la risposta di chiusura "
                            "primitiva (withdrawal) o flessione durante la valutazione (la "
                            "gamba opposta si flette in corrispondenza alla stimolazione del "
                            "piede — prima fase del riflesso di estensione crociata)."
                        ),
                        "osservazioni": (
                            "La risposta infantile (primitiva) al test del Babinski sarebbe "
                            "l'estensione dell'alluce e l'apertura del resto delle dita. La sua "
                            "presenza è sempre stata considerata un segno di disfunzione "
                            "cerebrale per il suo collegamento con i neuroni motori del tratto "
                            "piramidale superiore. Riappare nella Sclerosi Multipla, è molto "
                            "frequente fra i cerebrolesi ed è molto spesso presente nella "
                            "popolazione con Disturbi specifici dell'apprendimento. Non dovrebbe "
                            "essere evidente sopra l'anno di età \"quando si è raggiunto "
                            "l'equilibrio del sistema vestibolare (Wilkinson)\".\n\n"
                            "Bisogna essere consapevoli che la risposta primitiva del riflesso "
                            "di Babinsky può ri-emergere in condizioni di ipoglicemia — questo "
                            "può essere un fattore da considerare nei diabetici o soggetti con "
                            "disturbi dell'alimentazione."
                        ),
                        "scoring_specifico": {
                            0: "Flessione molto lieve delle dita del piede (alluce) verso lo stimolo",
                            1: "Nessuna risposta, riflesso adulto non presente",
                            2: "Lieve apertura delle dita",
                            3: "Evidente apertura delle dita",
                            4: "Apertura delle dita ed estensione dell'alluce",
                        },
                    },
                    {
                        "id": "bab_dx",
                        "label": "Piede destro",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test sul piede destro.",
                        "osservazioni": "Stesse osservazioni del piede sinistro.",
                        "scoring_specifico": {
                            0: "Flessione molto lieve delle dita del piede (alluce) verso lo stimolo",
                            1: "Nessuna risposta, riflesso adulto non presente",
                            2: "Lieve apertura delle dita",
                            3: "Evidente apertura delle dita",
                            4: "Apertura delle dita ed estensione dell'alluce",
                        },
                    },
                ],
            },
            {
                "id": "addominale_landau",
                "label": "Riflessi Addominale e Landau",
                "prove": [
                    {
                        "id": "addominale",
                        "label": "Riflesso Addominale",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Questo test non viene utilizzato routinariamente, giacché la sua "
                            "accuratezza è limitata da molti fattori diversi: interventi "
                            "chirurgici pregressi in zona addominale, gravidanze, sovrappeso o "
                            "ipersensibilità. Può tornare utile nel caso di un riflesso di "
                            "Babinsky primitivo completamente presente ed esiste il sospetto di "
                            "un problema a livello del tratto cortico-spinale.\n\n"
                            "Implica la contrazione dei muscoli della parete addominale come "
                            "risposta alla stimolazione dei quadranti intorno all'ombelico. "
                            "L'ASSENZA di questo riflesso si associa con lesioni nel tratto "
                            "cortico-spinale, ma può essere anche il risultato di lesioni nei "
                            "nervi periferici o dei centri rilessi della zona toracica del "
                            "midollo spinale o di Sclerosi Multipla. Il punteggio dipende dai "
                            "quadranti in cui non c'è risposta.\n\n"
                            "Utilizzando un pennello morbido e stretto, stimolare con dei "
                            "movimenti lievi ma vivaci a circa 2 cm di distanza dell'ombelico:\n"
                            "i. movimenti verticali ai lati\n"
                            "ii. movimenti orizzontali sopra e sotto l'ombelico\n"
                            "iii. movimenti in diagonale negli angoli determinati dai movimenti "
                            "precedenti."
                        ),
                        "osservazioni": "Il punteggio dipende dal numero di quadranti in cui non si osserva risposta.",
                        "scoring_specifico": {
                            0: "Risposta adeguata in tutti i 4 quadranti",
                            1: "Risposta in 3 quadranti",
                            2: "Risposta in 2 quadranti",
                            3: "Risposta in 1 quadrante",
                            4: "Nessuna risposta",
                        },
                    },
                    {
                        "id": "landau",
                        "label": "Riflesso di Landau",
                        "scoring": "0-4",
                        "posturale": True,
                        "istruzioni": (
                            "Chiedere al soggetto di distendersi sul pavimento in posizione "
                            "prona con le braccia ad angolo retto rispetto al corpo.\n\n"
                            "\"Solleva la parte superiore del corpo ma mantieni piedi e gambe "
                            "sul pavimento. Mantieni la posizione per 5 secondi se ti riesce.\""
                        ),
                        "osservazioni": (
                            "Si sollevano i piedi del pavimento mentre rimane nella posizione "
                            "di estensione, nell'alzarsi o scendere?"
                        ),
                        "scoring_specifico": {
                            0: "Nessun spostamento dei piedi (riflesso integrato correttamente)",
                            1: "Lieve, momentaneo sollevamento dei piedi",
                            2: "Netto spostamento rispetto al pavimento di 2-3 cm",
                            3: "Movimento di circa 3-5 cm",
                            4: "Risposta di Landau completa",
                        },
                    },
                ],
            },
            {
                "id": "rooting",
                "label": "Riflesso di Ricerca / punti cardinali (Rooting)",
                "prove": [
                    {
                        "id": "rooting_sx",
                        "label": "Sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Utilizzando un pennello morbido, stimolare delicatamente intorno "
                            "alle labbra verso il basso nei quattro angoli della bocca."
                        ),
                        "osservazioni": (
                            "Si osserva qualche movimento della bocca come risposta allo "
                            "stimolo, rictus o rimane una sensazione spiacevole alla fine del "
                            "test?"
                        ),
                        "scoring_specifico": {
                            0: "Nessun movimento delle labbra, bocca o guance in risposta allo stimolo",
                            1: "Lieve movimento della bocca sul lato dove si stimola",
                            2: "Movimento controllato o ritardato (\"sensazione disturbata dopo\")",
                            3: "Movimento evidente",
                            4: "Completa reazione di ricerca verso lo stimolo",
                        },
                    },
                    {
                        "id": "rooting_dx",
                        "label": "Destra",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test sul lato destro della bocca.",
                        "osservazioni": "Stesse osservazioni del lato sinistro.",
                        "scoring_specifico": {
                            0: "Nessun movimento delle labbra, bocca o guance in risposta allo stimolo",
                            1: "Lieve movimento della bocca sul lato dove si stimola",
                            2: "Movimento controllato o ritardato",
                            3: "Movimento evidente",
                            4: "Completa reazione di ricerca verso lo stimolo",
                        },
                    },
                ],
            },
            {
                "id": "suzione",
                "label": "Riflessi di suzione",
                "prove": [
                    {
                        "id": "suzione",
                        "label": "Riflesso di suzione",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Stimolare delicatamente la piega naso-labiale centralmente appena "
                            "sopra il labbro superiore con un dito. Quando si tocca la parte "
                            "superiore del labbro, si spostano essi in avanti come per iniziare "
                            "la suzione?"
                        ),
                        "osservazioni": (
                            "Il manuale specifica solo i livelli 0, 2 e 4. I livelli 1 e 3 "
                            "rappresentano gradi intermedi di reazione."
                        ),
                        "scoring_specifico": {
                            0: "Nessuna reazione",
                            1: "(grado intermedio)",
                            2: "Lieve reazione",
                            3: "(grado intermedio)",
                            4: "Sposta le labbra in avanti, apertura della bocca",
                        },
                    },
                    {
                        "id": "suzione_adulta",
                        "label": "Riflesso di suzione adulta",
                        "scoring": "scelta",
                        "opzioni": ["assente", "debole", "presente"],
                        "istruzioni": "Chiedere se è in grado di lanciare un bacio all'aria. Provare.",
                        "osservazioni": (
                            "Il manuale assegna direttamente: 0 = sì (riflesso adulto presente), "
                            "2 = movimento debole delle labbra, 4 = riflesso di suzione adulta non "
                            "presente. Per coerenza con il modulo si usa il campo descrittivo "
                            "(assente / debole / presente)."
                        ),
                    },
                ],
            },
            {
                "id": "prensile_mano",
                "label": "Riflesso Prensile (Palmare)",
                "prove": [
                    {
                        "id": "prens_mano_sx",
                        "label": "Mano sinistra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Utilizzando un pennello morbido, stimolare longitudinalmente e "
                            "delicatamente il palmo di ognuna delle mani."
                        ),
                        "osservazioni": "Notare anche eventuali sensazioni di disagio dopo il test.",
                        "scoring_specifico": {
                            0: "Nessuna risposta",
                            1: "Leggero e breve movimento del pollice verso l'interno o lieve flessione delle dita",
                            2: "Movimento del pollice verso il palmo della mano",
                            3: "Movimento evidente del pollice e delle dita",
                            4: "Chiusura del pollice e delle dita \"a pugno\"",
                        },
                    },
                    {
                        "id": "prens_mano_dx",
                        "label": "Mano destra",
                        "scoring": "0-4",
                        "istruzioni": "Stesso test sul palmo della mano destra.",
                        "osservazioni": "Stesse osservazioni della mano sinistra.",
                        "scoring_specifico": {
                            0: "Nessuna risposta",
                            1: "Leggero e breve movimento del pollice verso l'interno o lieve flessione delle dita",
                            2: "Movimento del pollice verso il palmo della mano",
                            3: "Movimento evidente del pollice e delle dita",
                            4: "Chiusura del pollice e delle dita \"a pugno\"",
                        },
                    },
                ],
            },
            {
                "id": "prensile_piede",
                "label": "Riflesso Prensile Plantare (\"Book test\")",
                "prove": [
                    {
                        "id": "prens_piede_sx",
                        "label": "Piede sinistro",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Book test. Collocare un grosso libro davanti ai piedi.\n\n"
                            "Chiedere al soggetto di appoggiare gli avampiedi sul bordo del "
                            "libro. La pressione del peso sulla parte superficiale della parte "
                            "superiore del piede eliciterà la risposta del riflesso prensile "
                            "plantare nel caso sia presente.\n\n"
                            "\"Quando sarai pronto, voglio che tu ti appoggi sulle dita dei "
                            "piedi e ti mantenga in quella posizione per 5 secondi se ti riesce. "
                            "(Appoggiati sulle mie spalle se senti che stai per cadere).\""
                        ),
                        "osservazioni": "Osservare il piede sinistro durante il test.",
                        "scoring_specifico": {
                            0: "Nessuna evidenza di movimento di \"prensione\" con le dita",
                            1: "Flessione momentanea delle dita di uno o entrambi i piedi",
                            2: "Flessione più prolungata delle dita dei piedi o instabilità",
                            3: "Flessione ulteriormente prolungata come sopra",
                            4: "Le dita si flettono durante l'intero test",
                        },
                    },
                    {
                        "id": "prens_piede_dx",
                        "label": "Piede destro",
                        "scoring": "0-4",
                        "istruzioni": "Stesso book test, osservare il piede destro.",
                        "osservazioni": "Stesse osservazioni del piede sinistro.",
                        "scoring_specifico": {
                            0: "Nessuna evidenza di movimento di \"prensione\" con le dita",
                            1: "Flessione momentanea delle dita",
                            2: "Flessione più prolungata delle dita dei piedi o instabilità",
                            3: "Flessione ulteriormente prolungata",
                            4: "Le dita si flettono durante l'intero test",
                        },
                    },
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
