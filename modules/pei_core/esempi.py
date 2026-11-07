"""
pei_core.esempi — caso didattico INVENTATO, completo e anonimo.

Uso: esercitazioni del corso «Progettazione PDF e PEI» e tirocinio.
Profilo Dinamico Funzionale + PEI (secondaria di II grado, classe 3ª, quindi
con PCTO), redatto all'inizio dell'anno: revisioni, verifica finale e
sezioni 11-12 restano vuote, come in un PEI approvato entro il 31 ottobre.
Nessun riferimento a persone reali.
"""

AVVERTENZA = ("Caso didattico inventato a scopo di esercitazione. "
              "Ogni riferimento a persone o istituti reali è casuale.")

ANNO = "2026/2027"

ESEMPIO_PDF = {
    "soggetto": "Studente L.R. (caso didattico)",
    "scuola": "Liceo scientifico, opzione scienze applicate — classe 3ª",
    "anno_scolastico": ANNO,
    "data_redazione": "2026-10-12",
    "df_riferimento": "Diagnosi Funzionale UONPIA del 03/2024: disturbo dello spettro autistico, "
                      "livello 1 di supporto, senza disabilità intellettiva",
    "redattori": "GLO: docenti del consiglio di classe, docente di sostegno, genitori, "
                 "referente UONPIA, assistente alla comunicazione",

    "cognitivo_attuale": "Funzionamento intellettivo nella norma, con profilo disomogeneo: punti di forza "
                         "nel ragionamento logico-astratto e nella memoria visiva; più fragili velocità di "
                         "elaborazione e flessibilità cognitiva nei compiti aperti.",
    "cognitivo_breve": "Usare in autonomia una scaletta per affrontare un compito aperto (es. problema "
                       "di realtà) in almeno 3 materie.",
    "cognitivo_medio": "Passare con flessibilità da una strategia all'altra quando la prima non funziona, "
                       "senza bisogno della mediazione dell'adulto.",

    "affettivo_relazionale_attuale": "Cerca il rapporto con due compagni con cui condivide interessi "
                                     "(robotica, astronomia). Nel gruppo classe tende a isolarsi; vive con "
                                     "ansia i cambi di programma e le situazioni nuove.",
    "affettivo_relazionale_breve": "Partecipare a un lavoro di gruppo strutturato con un ruolo "
                                   "definito, una volta alla settimana.",
    "affettivo_relazionale_medio": "Riconoscere e nominare l'ansia anticipatoria e usare una strategia "
                                   "concordata (pausa, richiesta d'aiuto) prima che diventi blocco.",

    "comunicazionale_attuale": "Comunica volentieri sui propri interessi, con difficoltà nei turni di "
                               "conversazione, nella lettura dei segnali non verbali e nelle richieste "
                               "implicite. Preferisce la comunicazione scritta.",
    "comunicazionale_breve": "Chiedere chiarimenti al docente quando una consegna è ambigua, almeno una "
                             "volta al giorno, anche per iscritto.",
    "comunicazionale_medio": "Gestire una breve esposizione orale davanti alla classe con supporto visivo.",

    "linguistico_attuale": "Lessico ricco e preciso, morfosintassi adeguata. Difficoltà di tipo "
                           "pragmatico: interpretazione letterale di metafore, ironia e doppi sensi; "
                           "testi argomentativi poco articolati.",
    "linguistico_breve": "Individuare il significato figurato in testi letterari con una guida di domande.",
    "linguistico_medio": "Produrre un testo argomentativo con tesi, due argomenti e conclusione.",

    "sensoriale_attuale": "Ipersensibilità uditiva: rumori di fondo e voci sovrapposte (laboratori, "
                          "palestra, intervallo) generano disagio e calo dell'attenzione. Vista e udito "
                          "nella norma.",
    "sensoriale_breve": "Usare le cuffie antirumore nei momenti concordati e chiedere di uscire in "
                        "modo appropriato.",
    "sensoriale_medio": "Restare in laboratorio per l'intera esercitazione con un posto riservato in "
                        "zona più tranquilla.",

    "motorio_prassico_attuale": "Motricità globale adeguata, qualche goffaggine nei giochi di squadra. "
                                "Grafia lenta e poco leggibile nelle prove lunghe; usa bene la tastiera.",
    "motorio_prassico_breve": "Usare il computer per le prove scritte più lunghe di un'ora.",
    "motorio_prassico_medio": "Partecipare alle attività di squadra in educazione fisica con un ruolo "
                              "concordato.",

    "neuropsicologico_attuale": "Attenzione sostenuta buona sui compiti di interesse, più fragile in "
                                "ambienti rumorosi. Funzioni esecutive: pianificazione e gestione del "
                                "tempo sono i punti più deboli (consegne dimenticate, studio non distribuito).",
    "neuropsicologico_breve": "Usare con costanza il diario digitale per consegne e verifiche.",
    "neuropsicologico_medio": "Pianificare lo studio settimanale in autonomia, con un controllo "
                              "quindicinale.",

    "autonomia_attuale": "Autonomo nella cura di sé e negli spostamenti casa-scuola con il pullman. "
                         "Fatica ad organizzare materiali e tempi e a muoversi in luoghi nuovi.",
    "autonomia_breve": "Preparare lo zaino in base all'orario senza promemoria dei genitori.",
    "autonomia_medio": "Raggiungere in autonomia la sede del PCTO dopo un percorso di prova.",

    "apprendimento_attuale": "Profitto buono in matematica, fisica e informatica; sufficiente in "
                             "italiano, storia e lingua inglese, con difficoltà nelle domande aperte e "
                             "nell'interpretazione dei testi.",
    "apprendimento_breve": "Rispondere a domande aperte di storia con una traccia di parole chiave.",
    "apprendimento_medio": "Raggiungere gli obiettivi della classe in tutte le discipline, con le "
                           "personalizzazioni delle modalità di verifica.",

    "sintesi": "Studente con buone risorse cognitive e interessi spiccati in ambito scientifico, il cui "
               "funzionamento è limitato soprattutto da barriere di contesto (rumore, imprevisti, "
               "consegne implicite) e dalle difficoltà pragmatiche ed esecutive. Con un ambiente "
               "prevedibile e consegne esplicite può seguire la progettazione della classe.",
    "note": "Profilo di Funzionamento non ancora disponibile: il GLO usa DF e PDF (art. 21 c.6 D.I. 182/2020).",
}

ESEMPIO_PEI = {
    "soggetto": "Studente L.R. (caso didattico)",
    "scuola": "Liceo scientifico, opzione scienze applicate — classe 3ª",
    "anno_scolastico": ANNO,
    "tipo_pei": "definitivo",
    "accertamento": "Verbale di accertamento del 02/2024, rivedibile nel 2027",
    "pf_disponibile": False,
    "pf_data": "",
    "df_riferimento": "DF UONPIA 03/2024; PDF del 12/10/2026",
    "progetto_individuale": "richiesto e non ancora redatto",
    "glo": [
        {"nome": "", "ruolo": "Dirigente scolastico (presidente)"},
        {"nome": "", "ruolo": "Docente di sostegno"},
        {"nome": "", "ruolo": "Coordinatore di classe (matematica)"},
        {"nome": "", "ruolo": "Docenti del consiglio di classe"},
        {"nome": "", "ruolo": "Genitori"},
        {"nome": "", "ruolo": "Referente UONPIA (UMV)"},
        {"nome": "", "ruolo": "Assistente alla comunicazione"},
        {"nome": "", "ruolo": "Studente (per le parti che lo riguardano)"},
    ],
    "data_approvazione": "2026-10-28",

    "situazione_familiare": "Vive con i genitori e una sorella minore. La famiglia collabora con la "
                            "scuola e segue un percorso di parent training presso la UONPIA. Nel tempo "
                            "libero frequenta un club di robotica.",
    "descrizione_di_se": "«Mi piacciono la fisica e programmare robot. Mi dà fastidio quando cambiano "
                         "le cose all'ultimo momento o quando tutti parlano insieme. Vorrei fare "
                         "ingegneria.» (colloquio del 20/10)",

    "sintesi_profilo": "Dalla DF e dal PDF: disturbo dello spettro autistico livello 1, senza disabilità "
                       "intellettiva. Punti di forza: ragionamento logico, memoria visiva, interessi "
                       "scientifici. Aree di bisogno: comunicazione pragmatica, flessibilità, "
                       "pianificazione, ipersensibilità uditiva, ansia per gli imprevisti.",
    "dimensioni_interessate": [
        "A. Dimensione della relazione, dell'interazione e della socializzazione",
        "B. Dimensione della comunicazione e del linguaggio",
        "C. Dimensione dell'autonomia e dell'orientamento",
        "D. Dimensione cognitiva, neuropsicologica e dell'apprendimento",
    ],

    "raccordo": "",
    "indicazioni_progetto": "La famiglia chiede che il Progetto Individuale includa attività "
                            "extrascolastiche di socializzazione e, dal quarto anno, l'orientamento "
                            "universitario con i servizi per studenti con disabilità.",

    "oss_relazione": "Punti di forza: rapporto stabile con due compagni, disponibilità quando il compito "
                     "è chiaro. Criticità: isolamento nei momenti destrutturati (intervallo, uscite), "
                     "reazioni di chiusura ai cambi di programma.",
    "oss_comunicazione": "Punti di forza: lessico ricco, buona scrittura tecnica. Criticità: "
                         "interpretazione letterale, difficoltà nei turni di parola e nelle richieste "
                         "implicite; raramente chiede aiuto.",
    "oss_autonomia": "Punti di forza: autonomo negli spostamenti abituali e nella cura di sé. "
                     "Criticità: organizzazione di materiali e tempi, ambienti nuovi e rumorosi.",
    "oss_cognitiva": "Punti di forza: logica, calcolo, memoria visiva, uso del computer. Criticità: "
                     "domande aperte, testi argomentativi, pianificazione dello studio.",
    "revisione_s4": "",

    "obiettivi_relazione": "Partecipare a un lavoro di gruppo settimanale con ruolo definito "
                           "(esito atteso: completa il proprio compito in 4 attività su 5).",
    "attivita_relazione": "Cooperative learning in matematica e scienze; tutoraggio tra pari in "
                          "informatica, in cui lo studente è tutor.",
    "strategie_relazione": "Ruoli scritti su cartellini, tempi dichiarati, preavviso dei cambi di "
                           "attività, gruppo scelto con il docente.",
    "verifica_relazione": "Griglia di osservazione del docente di sostegno, compilata ogni due settimane.",

    "obiettivi_comunicazione": "Chiedere chiarimenti quando una consegna è ambigua; comprendere "
                               "linguaggio figurato in testi guidati.",
    "attivita_comunicazione": "«Cartellino domanda» per chiedere chiarimenti anche per iscritto; "
                              "laboratorio sul linguaggio figurato con il docente di italiano.",
    "strategie_comunicazione": "Consegne esplicite e scritte, esempi concreti, verifica della "
                               "comprensione con domande dirette.",
    "verifica_comunicazione": "Numero di richieste spontanee registrate a settimana; prove guidate "
                              "di comprensione del testo.",

    "obiettivi_autonomia": "Gestire materiali, orario e consegne con il diario digitale; usare le "
                           "cuffie antirumore nei momenti concordati.",
    "attivita_autonomia": "Controllo settimanale del diario con il docente di sostegno; percorso di "
                          "prova verso la sede del PCTO.",
    "strategie_autonomia": "Agenda visiva, promemoria digitali, angolo tranquillo in aula, permesso di "
                           "uscita concordato con un segnale.",
    "verifica_autonomia": "Consegne rispettate sul totale; uso autonomo delle cuffie senza richiamo.",

    "obiettivi_cognitiva": "Usare una scaletta per i compiti aperti e una traccia di parole chiave "
                           "per le interrogazioni di storia e filosofia.",
    "attivita_cognitiva": "Mappe concettuali costruite insieme, schede di metodo di studio, "
                          "simulazioni di interrogazione programmata.",
    "strategie_cognitiva": "Interrogazioni programmate, domande chiuse affiancate a quelle aperte, "
                           "tempi aggiuntivi, uso del computer con correttore ortografico.",
    "verifica_cognitiva": "Esiti delle prove disciplinari con le personalizzazioni della sezione 8.2.",
    "revisione_s5": "",
    "verifica_conclusiva_s5": "",

    "barriere": "Rumore nei laboratori e in palestra; cambi d'aula e d'orario comunicati all'ultimo "
                "momento; consegne solo orali; intervallo nel corridoio affollato.",
    "facilitatori": "Compagni di riferimento; docenti disponibili a scrivere le consegne; registro "
                    "elettronico aggiornato; aula di informatica; interesse per le materie scientifiche.",
    "indicazioni_studente_contesto": "Chiede di sapere prima le verifiche e i cambi d'aula, e di poter "
                                     "stare in aula durante l'intervallo.",

    "interventi_contesto": "Comunicazione dei cambi d'orario sul registro entro il giorno prima; "
                           "consegne sempre anche scritte; postazione fissa vicino alla porta in "
                           "laboratorio; intervallo in aula con un compagno; attività di "
                           "sensibilizzazione sulla neurodiversità per tutta la classe.",
    "revisione_s7": "",
    "verifica_conclusiva_s7": "",

    "modalita_sostegno": "Docente di sostegno in compresenza soprattutto in italiano, storia, filosofia "
                         "e inglese; in sua assenza il docente curricolare fornisce consegne scritte e "
                         "la scaletta di lavoro concordata.",
    "modalita_verifica": "Verifiche programmate con almeno una settimana di anticipo; tempi aggiuntivi "
                         "del 30% o riduzione del numero di quesiti; computer per prove scritte lunghe; "
                         "domande aperte affiancate da domande chiuse; interrogazioni programmate "
                         "con traccia di parole chiave; ambiente silenzioso se richiesto.",
    "progettazione_disciplinare": [
        {"disciplina": "Matematica", "opzione": "A - segue la progettazione della classe",
         "dettaglio": ""},
        {"disciplina": "Fisica", "opzione": "A - segue la progettazione della classe",
         "dettaglio": ""},
        {"disciplina": "Informatica", "opzione": "A - segue la progettazione della classe",
         "dettaglio": ""},
        {"disciplina": "Lingua e letteratura italiana",
         "opzione": "B - personalizzata, verifiche identiche o equipollenti",
         "dettaglio": "Analisi del testo guidata da domande; criteri di valutazione centrati su "
                      "contenuto e struttura più che sullo stile."},
        {"disciplina": "Storia e filosofia",
         "opzione": "B - personalizzata, verifiche identiche o equipollenti",
         "dettaglio": "Interrogazioni programmate con traccia; prove semistrutturate equipollenti."},
        {"disciplina": "Lingua e cultura inglese",
         "opzione": "B - personalizzata, verifiche identiche o equipollenti",
         "dettaglio": "Comprensione con domande chiuse; produzione orale su argomenti preparati."},
        {"disciplina": "Scienze motorie", "opzione": "B - personalizzata, verifiche identiche o equipollenti",
         "dettaglio": "Ruoli concordati nei giochi di squadra; valutazione sulle abilità individuali."},
    ],
    "percorso": "personalizzato (con prove equipollenti)",
    "pcto_tipologia": "aziendale",
    "pcto_progetto": "Percorso presso un laboratorio di robotica educativa del territorio. Obiettivi: "
                     "lavorare in un piccolo gruppo con ruoli definiti, rispettare orari e consegne, "
                     "spiegare il proprio lavoro a un adulto. Contesto: ambiente poco rumoroso "
                     "(facilitatore), presenza di estranei e imprevisti (barriera, gestita con un "
                     "sopralluogo preliminare e un tutor aziendale di riferimento). Fasi: sopralluogo, "
                     "affiancamento, progetto autonomo, presentazione finale.",
    "pcto_monitoraggio": "Indicatori: puntualità, completamento dei compiti, richieste d'aiuto "
                         "appropriate, valutazione del tutor aziendale. Rete: centro per l'impiego e "
                         "servizio di orientamento dell'università. Lo studente ha scelto il settore.",
    "comportamento": "stessi criteri della classe",
    "comportamento_obiettivi": "",
    "revisione_s8": "",
    "verifica_conclusiva_s8": "",

    "orario_presenza": "intero orario",
    "orario_motivazione": "",
    "ore_sostegno": 9,
    "assistenza_base": "Non necessaria.",
    "assistenza_specialistica": "Assistente alla comunicazione: 6 ore settimanali, nelle discipline "
                                "con maggiore carico linguistico e nei momenti destrutturati.",
    "altre_risorse": "Referente per l'inclusione; sportello di ascolto psicologico della scuola.",
    "uscite": "Preavviso con programma scritto e foto dei luoghi; un docente o l'assistente "
              "di riferimento; possibilità di pause in un luogo tranquillo.",
    "comportamenti_problema": "Prevenzione: preavviso dei cambi, segnale concordato per uscire. "
                              "Gestione: pausa di 5-10 minuti in un luogo tranquillo con un adulto, "
                              "poi rientro guidato; nessun richiamo davanti alla classe.",
    "progetti_classe": "Progetto «Menti diverse» sulla neurodiversità; tutoraggio tra pari in informatica.",
    "trasporto": "Autonomo con il servizio di linea.",
    "extrascolastico": "Club di robotica il sabato; parent training alla UONPIA.",

    "certificazione": "",
    "verifica_finale": "",
    "aggiornamento_contesto": "",
    "debito_funzionamento": [],
    "proposta_ore_sostegno": 0,
    "motivazione_ore": "",
    "proposta_assistenza": "",
    "proposta_trasporto": "",
    "pei_provvisorio": "",
    "provv_ore_sostegno": 0,
    "provv_assistenza": "",
}


def crea_esempio(conn, rif_tipo: str, rif_id: int, utente: str = "",
                 tenant_id: int | None = None) -> tuple[int, int]:
    """Crea nel database il PDF e il PEI d'esempio collegati. Restituisce (id_pdf, id_pei)."""
    from . import db
    from .model import Documento
    pdf = Documento("PDF", contenuto=dict(ESEMPIO_PDF), anno_scolastico=ANNO, anonimo=True)
    id_pdf = db.salva_documento(conn, pdf, rif_tipo, rif_id, utente, tenant_id)
    pei = Documento("PEI", contenuto=dict(ESEMPIO_PEI), anno_scolastico=ANNO, anonimo=True)
    id_pei = db.salva_documento(conn, pei, rif_tipo, rif_id, utente, tenant_id, sorgente_id=id_pdf)
    return id_pdf, id_pei
