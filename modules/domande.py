# modules/pnev/domande.py
# Questionario di Screening Neurosviluppo
# Fonte: INPP International Ltd. 2020 (adattato per The Organism)
# Versioni: BAMBINI (genitore compila) e ADULTI (autocompilato)

# ── SEZIONI COMUNI ────────────────────────────────────────────────────────────

SEZIONE_STORIA_PRENATALE = {
    "id": "prenatale",
    "titolo": "Storia della Gravidanza e della Nascita",
    "descrizione": "Informazioni sullo sviluppo prima e durante la nascita.",
    "domande": [
        {"id": "p01", "testo": "C'è qualche caso di difficoltà simili fra i genitori o le loro famiglie?", "tipo": "si_no_testo"},
        {"id": "p02", "testo": "È stato concepito/a con fecondazione assistita (FIVET)?", "tipo": "si_no"},
        {"id": "p03", "testo": "Durante la gravidanza c'è stato qualche problema medico? (pressione alta, nausea eccessiva, rischio aborto, infezioni virali, stress emotivo importante)", "tipo": "si_no_testo"},
        {"id": "p03a", "testo": "La madre ha fumato durante la gravidanza?", "tipo": "si_no"},
        {"id": "p03b", "testo": "La madre ha bevuto alcool durante la gravidanza?", "tipo": "si_no"},
        {"id": "p03c", "testo": "La madre ha sofferto di un'importante infezione virale durante le prime 13 settimane?", "tipo": "si_no"},
        {"id": "p03d", "testo": "La madre ha sofferto di stress emotivo importante?", "tipo": "si_no"},
        {"id": "p04", "testo": "È stata una gravidanza pre-termine o post-termine?", "tipo": "si_no_testo", "placeholder": "Specificare di quante settimane"},
        {"id": "p05", "testo": "La nascita è stata particolarmente difficoltosa o anomala? (parto indotto, forcipe, ventosa, cesareo...)", "tipo": "si_no_testo"},
        {"id": "p06", "testo": "Il bambino era particolarmente piccolo per l'età gestazionale?", "tipo": "si_no_testo", "placeholder": "Indicare il peso se ricordato"},
        {"id": "p07", "testo": "C'era qualcosa di inusuale alla nascita? (problemi craniali, colorito bluastro, itterizia, crosta lattea, terapia intensiva)", "tipo": "si_no_testo", "placeholder": "Indicare il punteggio Apgar se ricordato"},
    ],
}

SEZIONE_PRIMA_INFANZIA = {
    "id": "prima_infanzia",
    "titolo": "Primi Anni di Vita",
    "descrizione": "Sviluppo nei primi 18 mesi.",
    "domande": [
        {"id": "i01", "testo": "Durante le prime 13 settimane di vita ha avuto difficoltà di suzione, per alimentarsi o di rigurgito?", "tipo": "si_no_testo", "placeholder": "È stato allattato al seno? Per quanto tempo?"},
        {"id": "i02", "testo": "Durante i primi 6 mesi, è stato un bambino particolarmente tranquillo, anche troppo?", "tipo": "si_no"},
        {"id": "i03", "testo": "Fra i 6 e i 18 mesi, era particolarmente agitato, richiedeva continue attenzioni, dormiva poco e piangeva?", "tipo": "si_no"},
        {"id": "i04", "testo": "Quando era abbastanza grande da mantenersi seduto, si dondolava così forte da muovere il lettino o il passeggino?", "tipo": "si_no"},
        {"id": "i05", "testo": "Si colpiva la testa con oggetti solidi?", "tipo": "si_no"},
        {"id": "i06", "testo": "Ha imparato a camminare troppo presto (prima dei 10 mesi) oppure in ritardo (dopo i 16 mesi)?", "tipo": "si_no"},
        {"id": "i07", "testo": "Ha omesso la fase dello striscio sulla pancia?", "tipo": "si_no"},
        {"id": "i08", "testo": "Ha omesso la fase del gattonamento, oppure saltellava sul sedere o rotolava e poi in un giorno si mise in piedi?", "tipo": "si_no_testo"},
        {"id": "i09", "testo": "Ha imparato a parlare in ritardo? (frasi di 3 parole dopo i 2 anni)", "tipo": "si_no"},
        {"id": "i10", "testo": "Nei primi 18 mesi di vita, ha avuto malattie con febbre molto alta e/o convulsioni?", "tipo": "si_no_testo"},
        {"id": "i11", "testo": "C'è stato qualche segno di eczema o asma?", "tipo": "si_no"},
        {"id": "i12", "testo": "C'è stata qualche reazione ad un vaccino?", "tipo": "si_no"},
    ],
}

SEZIONE_SVILUPPO_MOTORIO = {
    "id": "sviluppo_motorio",
    "titolo": "Sviluppo Motorio e Autonomia",
    "descrizione": "Tappe motorie e autonomia personale.",
    "domande": [
        {"id": "m01", "testo": "Ha avuto difficoltà ad imparare a vestirsi da solo/a?", "tipo": "si_no"},
        {"id": "m02", "testo": "Ha continuato a succhiarsi il pollice fino ai 5 anni o anche oltre?", "tipo": "si_no_testo", "placeholder": "Destro o sinistro?"},
        {"id": "m03", "testo": "Ha continuato a bagnare il letto (anche solo ogni tanto) sopra i 5 anni?", "tipo": "si_no"},
        {"id": "m04", "testo": "Soffre di 'mal d'auto' o chinetosi?", "tipo": "si_no"},
        {"id": "m05", "testo": "Ha avuto difficoltà ad imparare ad andare in bicicletta con solo due ruote?", "tipo": "si_no"},
        {"id": "m06", "testo": "Ha avuto difficoltà ad imparare a prendere una palla al volo?", "tipo": "si_no"},
    ],
}

SEZIONE_SCUOLA = {
    "id": "scuola",
    "titolo": "Apprendimento Scolastico",
    "descrizione": "Difficoltà nella scuola primaria e oltre.",
    "domande": [
        {"id": "s01", "testo": "Nei primi due anni di scuola, ha avuto problemi a imparare a leggere?", "tipo": "si_no"},
        {"id": "s02", "testo": "Nei primi due anni di scuola, ha avuto difficoltà a imparare a scrivere?", "tipo": "si_no"},
        {"id": "s03", "testo": "Ha avuto particolari difficoltà a scrivere in corsivo?", "tipo": "si_no"},
        {"id": "s04", "testo": "Ha fatto più fatica a imparare a leggere l'ora da un orologio analogico che da quelli digitali?", "tipo": "si_no"},
        {"id": "s05", "testo": "È stato un bambino con continue malattie alle alte vie respiratorie (otite a ripetizione, bronchite, sinusite)?", "tipo": "si_no"},
        {"id": "s06", "testo": "Fa fatica a stare fermo seduto, come se avesse 'formiche nei pantaloni', ed è continuamente ripreso dagli insegnanti?", "tipo": "si_no"},
        {"id": "s07", "testo": "Fa molti errori quando copia un testo da un libro?", "tipo": "si_no"},
        {"id": "s08", "testo": "Quando scrive un compito, ogni tanto 'gira' le lettere oppure salta qualche lettera o parola?", "tipo": "si_no"},
        {"id": "s09", "testo": "Se c'è un rumore o movimento inaspettato, si spaventa in modo esagerato?", "tipo": "si_no"},
    ],
}

SEZIONE_NUTRIZIONE = {
    "id": "nutrizione",
    "titolo": "Nutrizione e Salute Generale",
    "descrizione": "Problemi gastrointestinali, cutanei e respiratori.",
    "domande": [
        {"id": "n01", "testo": "Problemi gastro-intestinali frequenti (colica, dolori addominali, aerofagia, stitichezza, diarrea)?", "tipo": "si_no_testo"},
        {"id": "n02", "testo": "Problemi di pelle (eczema, zone secche, 'pelle di gallina' sulle braccia o cosce, dermatite)?", "tipo": "si_no_testo"},
        {"id": "n03", "testo": "Problemi di Orecchio, Naso e Gola (ulcere, respirazione difficoltosa, tonsilliti, sinusite, muco persistente, russamento, respirazione con la bocca, febbre da fieno)?", "tipo": "si_no_testo"},
        {"id": "n04", "testo": "Soffre di asma? (specificare se indotto da esercizio, infezioni, polvere, muffa, animali, alimenti)", "tipo": "si_no_testo"},
        {"id": "n05", "testo": "Ha una sete particolarmente esagerata?", "tipo": "si_no"},
        {"id": "n06", "testo": "I sintomi peggiorano se passa più di 2-3 ore senza mangiare?", "tipo": "si_no"},
        {"id": "n07", "testo": "C'è qualche alimento in particolare che altera il comportamento?", "tipo": "si_no_testo"},
    ],
}

SEZIONE_UDITO = {
    "id": "udito",
    "titolo": "Ascolto e Udito",
    "descrizione": "Difficoltà legate all'elaborazione uditiva.",
    "domande": [
        {"id": "u01", "testo": "C'è stato un ritardo nello sviluppo motorio?", "tipo": "si_no"},
        {"id": "u02", "testo": "C'è stato un ritardo nello sviluppo del linguaggio?", "tipo": "si_no"},
        {"id": "u03", "testo": "Ha sofferto di otiti a ripetizione?", "tipo": "si_no"},
        {"id": "u04", "testo": "Ci sono stati sospetti di difficoltà uditive per le quali siano state fatte ricerche specifiche?", "tipo": "si_no"},
        {"id": "u05", "testo": "Brevi tempi di attenzione e distraibilità?", "tipo": "si_no"},
        {"id": "u06", "testo": "Ipersensibile ai suoni?", "tipo": "si_no"},
        {"id": "u07", "testo": "Mal intende le domande, ha bisogno spesso di ripetizioni?", "tipo": "si_no"},
        {"id": "u08", "testo": "Incapace di seguire ordini in sequenza?", "tipo": "si_no"},
        {"id": "u09", "testo": "Stanchezza alla fine della giornata o, al contrario, iperattività?", "tipo": "si_no"},
        {"id": "u10", "testo": "Voce piatta/monotona, scarso vocabolario, povera costruzione delle frasi?", "tipo": "si_no"},
        {"id": "u11", "testo": "Incapacità a cantare intonato, confusione o inversione di lettere?", "tipo": "si_no"},
        {"id": "u12", "testo": "Difficoltà a fare amicizia, tendenza a rinchiudersi, scarsa motivazione, irritabilità, timidezza?", "tipo": "si_no"},
    ],
}

# ── SEZIONE SOLO ADULTI ───────────────────────────────────────────────────────

SEZIONE_ETA_ADULTA = {
    "id": "eta_adulta",
    "titolo": "Sintomi in Età Adulta",
    "descrizione": "Sintomi e difficoltà attuali.",
    "domande": [
        {"id": "a01", "testo": "Se c'è un rumore o movimento inaspettato, si spaventa in modo esagerato?", "tipo": "si_no"},
        {"id": "a02", "testo": "Ha paura degli spazi aperti, attacchi di panico, ansia esagerata?", "tipo": "si_no_testo", "placeholder": "A che età hanno cominciato? Descrivere i sintomi"},
        {"id": "a03", "testo": "Questi sintomi peggiorano in qualche luogo o momento specifico?", "tipo": "si_no_testo"},
        {"id": "a04", "testo": "Le capita di percepire il movimento di oggetti che in realtà sono fermi (alberi, palazzi)?", "tipo": "si_no"},
        {"id": "a05", "testo": "Le capita di vedere sfuocato o percepire altre alterazioni visive?", "tipo": "si_no"},
        {"id": "a06", "testo": "Ha nausea frequentemente?", "tipo": "si_no"},
        {"id": "a07", "testo": "Ha spesso nausea mentre è coricato/a sul letto?", "tipo": "si_no"},
        {"id": "a08", "testo": "Considera di avere uno scarso senso dell'equilibrio?", "tipo": "si_no"},
        {"id": "a09", "testo": "Pensa di essere molto scoordinato/a ogni tanto?", "tipo": "si_no"},
        {"id": "a10", "testo": "Soffre o ha sofferto di emicrania?", "tipo": "frequenza", "opzioni": ["Mai", "Talvolta", "Spesso"]},
        {"id": "a11", "testo": "È molto sensibile alle luci brillanti (discoteche, flash, sole diretto)?", "tipo": "si_no"},
        {"id": "a12", "testo": "Si considera particolarmente sensibile ai suoni rispetto alle persone che conosce?", "tipo": "si_no"},
        {"id": "a13", "testo": "Fa fatica con destra e sinistra quando deve dare indicazioni stradali?", "tipo": "si_no"},
        {"id": "a14", "testo": "Quando scrive qualcosa di lungo/complesso, inizia a fare errori (cambia ordine di lettere o parole, errori ortografici inusuali)?", "tipo": "si_no"},
        {"id": "a15", "testo": "Le capita, quando è molto stanco/a, di sapere cosa vuole dire ma non riuscire a parlare correttamente?", "tipo": "si_no"},
        {"id": "a16", "testo": "Le capita, quando è molto stanco/a, di diventare goffo/a e scoordinato/a, di colpirsi con oggetti?", "tipo": "si_no"},
    ],
}

# ── STRUTTURA QUESTIONARI ─────────────────────────────────────────────────────

QUESTIONARIO_BAMBINI = {
    "versione": "bambini",
    "titolo": "Questionario di Screening Neurosviluppo — Bambini",
    "sottotitolo": "Compilato dal genitore o tutore",
    "eta_min": 4,
    "eta_max": 17,
    "sezioni": [
        SEZIONE_STORIA_PRENATALE,
        SEZIONE_PRIMA_INFANZIA,
        SEZIONE_SVILUPPO_MOTORIO,
        SEZIONE_SCUOLA,
        SEZIONE_NUTRIZIONE,
        SEZIONE_UDITO,
    ],
    "note_finali": True,
}

QUESTIONARIO_ADULTI = {
    "versione": "adulti",
    "titolo": "Questionario di Screening Neurosviluppo — Adulti",
    "sottotitolo": "Autocompilato",
    "eta_min": 18,
    "eta_max": 99,
    "sezioni": [
        SEZIONE_STORIA_PRENATALE,
        SEZIONE_PRIMA_INFANZIA,
        SEZIONE_SVILUPPO_MOTORIO,
        SEZIONE_SCUOLA,
        SEZIONE_ETA_ADULTA,
    ],
    "note_finali": True,
}
