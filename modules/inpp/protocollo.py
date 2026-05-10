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

# Legenda generica — usata quando una prova non ha scoring_specifico
# (Formulario rev. 01/22, pag. 2)
SCORING_LABELS: dict[int, str] = {
    0: "Nessuna anomalia",
    1: "Minima presenza residua / Minima difficoltà",
    2: "Riflesso primitivo residuo / Difficoltà a completare",
    3: "Riflesso primitivo presente in gran parte / Marcata difficoltà",
    4: "Riflesso primitivo completamente ritenuto / Incapacità",
}

# Legenda alternativa percentuale (manuale corso INPP 2019-2020)
# Mostrata come sottotitolo informativo
SCORING_LABELS_PERCENTUALE: dict[int, str] = {
    0: "0% — Nessuna anomalia",
    1: "25% — Disfunzione lieve",
    2: "50% — Disfunzione moderata",
    3: "75% — Disfunzione marcata",
    4: "100% — Disfunzione completa",
}

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
                "id": "upst",
                "label": "Test su un solo piede (UPST — Unipedal Stance Test)",
                "prove": [
                    {
                        "id": "upst",
                        "label": "Test su un solo piede (UPST), dai 6 anni",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Chiedere al bambino di collocarsi in piedi su un solo piede e dire: "
                            "\"Cerca di mantenere questa posizione tutto il tempo che ti riesca\". "
                            "Contabilizzare in secondi il tempo che il bambino riesce a mantenere "
                            "la posizione prima di perdere l'equilibrio o di appoggiare l'altro "
                            "piede. Ripetere la procedura con l'altro piede.\n\n"
                            "Utilizzare un cronometro. Il tempo inizia quando il soggetto solleva "
                            "il piede dal pavimento e finisce quando perde l'equilibrio, appoggia "
                            "l'altro piede sul pavimento o sposta il piede di appoggio.\n\n"
                            "Dati normativi:\n"
                            "• 6 anni: 20 secondi con il piede destro o sinistro\n"
                            "• 8+ anni: 30 secondi con piede destro o sinistro"
                        ),
                        "osservazioni": (
                            "• L'incapacità di mantenersi in equilibrio su un solo piede per il "
                            "tempo appropriato all'età può essere un indicatore di difficoltà "
                            "vestibolari o di immaturità posturale.\n"
                            "• Osservare ogni movimento compensatorio significativo delle braccia, "
                            "dell'altra gamba, della bocca o delle mani durante l'esecuzione."
                        ),
                        "scoring_specifico": {
                            0: "N.A. — Tempo nella norma per l'età",
                            1: "Due secondi meno della norma per l'età",
                            2: "Quattro secondi meno della norma per l'età",
                            3: "Sei secondi meno della norma per l'età",
                            4: "Otto secondi meno della norma per l'età",
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
                "label": "Saltare su una gamba (dai 4 anni)",
                "prove": [
                    {
                        "id": "saltellare_dx",
                        "label": "Gamba destra",
                        "scoring": "0-4",
                        "istruzioni": (
                            "Salta su una sola gamba spostandoti in avanti lungo tutta la stanza "
                            "finché ti chiederò di fermarti."
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
                    {
                        "id": "saltellare_sx",
                        "label": "Gamba sinistra",
                        "scoring": "0-4",
                        "istruzioni": "Ripetere lo stesso compito sull'altra gamba.",
                        "osservazioni": (
                            "Stesse osservazioni del salto su gamba destra. Annotare differenze "
                            "significative tra i due lati."
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
    # (radio button: presente / atipico / assente, come da scelta utente)
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
                    {"id": "striscio_omologo", "label": "Omologo", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "striscio_omolaterale", "label": "Omolaterale", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "striscio_incrociato", "label": "Incrociato", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                ],
            },
            {
                "id": "carponi",
                "label": "Carponi",
                "prove": [
                    {"id": "carponi_omologo", "label": "Omologo", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "carponi_omolaterale", "label": "Omolaterale", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "carponi_incrociato", "label": "Incrociato", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                ],
            },
            {
                "id": "schemi_note",
                "label": "Note osservative",
                "prove": [
                    {"id": "schemi_note", "label": "Note", "scoring": "testo"},
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
                    {"id": "tallone_sx_su_dx", "label": "Sx su Dx", "scoring": "0-4"},
                    {"id": "tallone_dx_su_sx", "label": "Dx su Sx", "scoring": "0-4"},
                ],
            },
            {
                "id": "approssimazione",
                "label": "Approssimazione digitale (linea mediana)",
                "prove": [
                    {"id": "appr_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "appr_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
                ],
            },
            {
                "id": "dito_naso",
                "label": "Dito-naso",
                "prove": [
                    {"id": "dn_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "dn_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
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
                    {"id": "rtac_std_br_sx", "label": "Standard — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_std_gb_sx", "label": "Standard — Gamba sinistra", "scoring": "0-4"},
                    {"id": "rtac_std_br_dx", "label": "Standard — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_std_gb_dx", "label": "Standard — Gamba destra", "scoring": "0-4"},
                    {"id": "rtac_ayres1_br_sx", "label": "Test di Ayres (n.1) — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_ayres1_br_dx", "label": "Test di Ayres (n.1) — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_ayres2_br_sx", "label": "Test di Ayres (n.2) — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_ayres2_br_dx", "label": "Test di Ayres (n.2) — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_schidler_br_sx", "label": "Test di Schidler — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_schidler_br_dx", "label": "Test di Schidler — Braccio destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "rtc_trasformato",
                "label": "Riflesso Tonico Trasformato del Collo",
                "prove": [
                    {"id": "rtc_dx_sx", "label": "Destra a sinistra", "scoring": "0-4"},
                    {"id": "rtc_sx_dx", "label": "Sinistra a destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "rtsc",
                "label": "Riflesso Tonico Simmetrico del Collo (RTSC)",
                "prove": [
                    {"id": "rtsc_piedi_sedere", "label": "Coinvolgimento dei piedi o del sedere", "scoring": "0-4"},
                    {"id": "rtsc_braccia", "label": "Coinvolgimento delle braccia", "scoring": "0-4"},
                    {"id": "rtsc_carponi", "label": "Evidenza durante il carponi", "scoring": "0-4"},
                ],
            },
            {
                "id": "galant",
                "label": "Riflesso Spinale di Galant",
                "prove": [
                    {"id": "galant_sx", "label": "Lato sinistro", "scoring": "0-4"},
                    {"id": "galant_dx", "label": "Lato destro", "scoring": "0-4"},
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
