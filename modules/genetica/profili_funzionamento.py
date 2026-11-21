"""
Modulo Genetica PNEV · profili di funzionamento delle sindromi e incrocio con il volto.

Contiene le 30 schede del manuale «Sindromi genetiche e profilo di funzionamento»
(Studio The Organism, novembre 2026) e la funzione che incrocia, per ciascuna:
  - quanto la sindrome somiglia al paziente guardando SOLO i segni del volto;
  - quanto gli somiglia guardando SOLO i segni funzionali (visione, udito, motricità, linguaggio…);
  - quanto gli somiglia con tutti i segni insieme.

Le schede descrivono tendenze di gruppo riportate in letteratura: non sono il profilo del
singolo bambino. La riga «Lettura PNEV» è un'ipotesi di lavoro clinica, non una raccomandazione
validata per la singola sindrome. Strumento di ORIENTAMENTO: nessun valore diagnostico.

Quattro sindromi (Turner, Klinefelter, tripla X, XYY) non hanno un codice nei dati HPO del
modulo (solo OMIM e DECIPHER): la scheda si consulta, ma non entra nell'incrocio.
"""
from __future__ import annotations

from .ponte_pnev import BRIDGE
from .volto import VOLTO

# campo della scheda -> etichetta
CAMPI = [
    ("base", "Base genetica"),
    ("forza", "Punti di forza relativi"),
    ("fragilita", "Fragilità tipiche"),
    ("sensoriale", "Sensoriale e motorio"),
    ("regolazione", "Regolazione e relazione"),
    ("salute", "Salute da monitorare"),
    ("leve", "Leve di intervento"),
    ("pnev", "Lettura PNEV"),
]

# dimensione della griglia individuale -> (etichetta, campi della scheda da mostrare come «atteso»)
DIMENSIONI = [
    ("cognitiva", "Cognitiva, neuropsicologica e dell'apprendimento", ("forza", "fragilita")),
    ("comunicazione", "Comunicazione e linguaggio", ("fragilita",)),
    ("udito", "Sensoriale: udito", ("sensoriale",)),
    ("visione", "Sensoriale: visione e oculomotricità", ("sensoriale",)),
    ("reattivita", "Reattività sensoriale (suoni, tatto, dolore)", ("sensoriale",)),
    ("motorio", "Tono, postura, motricità", ("sensoriale",)),
    ("regolazione", "Regolazione, attenzione, comportamento", ("regolazione",)),
    ("relazione", "Relazione, interazione, socializzazione", ("regolazione",)),
    ("autonomia", "Autonomia e orientamento", ("leve",)),
    ("salute", "Salute e controlli medici", ("salute",)),
    ("pnev", "Priorità e cautele PNEV", ("pnev",)),
]

QUALIFICATORI = ["—", "0 · nessuna difficoltà", "1 · lieve", "2 · media", "3 · grave", "4 · completa"]

SINOSSI_ETICHETTE = {"cognitivo": "Cognitivo globale", "linguaggio": "Linguaggio espressivo",
                     "visuo_spaziale": "Visuo-spaziale", "motorio": "Tono e motricità",
                     "sensi": "Udito, vista, reattività", "socialita": "Socialità"}
SINOSSI_VALORI = {"P": "punto di forza", "V": "variabile", "F": "fragilità", "FF": "fragilità marcata"}

SOGLIA_TIPICO = 0.55    # frequenza da cui un segno è «tipico» (esclude i segni a frequenza ignota, che valgono 0.5)
PRIME = 50              # «tra le prime 50 su 8.512»: soglia usata per dire che volto/funzionamento indicano la sindrome
MIN_SEGNI = 2           # sotto questo numero di segni presenti il confronto per gruppo non si calcola

PROFILI = \
[
 {
  "slug": "down",
  "nome": "Sindrome di Down",
  "codici": [
   "OMIM:190685"
  ],
  "base": "Trisomia 21 (libera nella maggior parte dei casi; più rare traslocazione e mosaico).",
  "forza": "Apprendimento per via visiva e per imitazione, memoria visuo-spaziale a breve termine, comprensione superiore alla produzione, socialità e uso dei gesti.",
  "fragilita": "Disabilità intellettiva in genere lieve-moderata; memoria verbale a breve termine, morfosintassi e intelligibilità dell'eloquio; lentezza di elaborazione.",
  "sensoriale": "Ipotonia e lassità legamentosa, tappe motorie ritardate. Ipoacusia frequente, spesso trasmissiva per otiti. Vizi refrattivi, strabismo, accomodazione ridotta, nistagmo.",
  "regolazione": "Buona motivazione sociale; possibili ostinazione ed evitamento del compito difficile; in una minoranza coesistono autismo o ADHD.",
  "salute": "Cardiopatie congenite, tiroide, apnee del sonno, instabilità atlanto-assiale, celiachia; invecchiamento precoce e rischio di demenza in età adulta.",
  "leve": "Supporti visivi e lettura precoce come sostegno al linguaggio, gesti e segni, controllo periodico di udito e vista, lavoro su tono e postura.",
  "pnev": "Priorità: udito (verificare la componente trasmissiva prima della stimolazione uditiva), accomodazione e oculomotricità, tono e stabilità posturale. Cautela: niente manovre forzate sul collo finché non è esclusa l'instabilità atlanto-assiale.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "FF",
   "visuo_spaziale": "P",
   "motorio": "F",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "x_fragile",
  "nome": "Sindrome dell'X fragile",
  "codici": [
   "OMIM:300624"
  ],
  "base": "Espansione oltre 200 triplette CGG nel gene FMR1 (Xq27.3) con silenziamento del gene. Maschi più colpiti; femmine con quadro più lieve e variabile.",
  "forza": "Memoria visiva e a lungo termine per ciò che interessa, vocabolario ricettivo, imitazione, abilità della vita quotidiana, senso dell'umorismo.",
  "fragilita": "Disabilità intellettiva (nei maschi spesso moderata); funzioni esecutive, memoria di lavoro, elaborazione sequenziale, matematica; eloquio rapido, ripetitivo, perseverante.",
  "sensoriale": "Iperreattività a suoni, contatto e affollamento; ipotonia e lassità articolare; otiti ricorrenti; strabismo e difetti refrattivi.",
  "regolazione": "Ansia sociale con evitamento dello sguardo pur con desiderio di relazione; iperattività e impulsività; stereotipie (sfarfallio delle mani); frequenti tratti dello spettro autistico.",
  "salute": "Epilessia in una parte dei casi, prolasso mitralico. Familiari portatori di premutazione: possibili quadri correlati, utile la consulenza genetica.",
  "leve": "Ambiente prevedibile e a bassa stimolazione, avvicinamento laterale senza richiesta di contatto oculare, apprendimento globale e visivo, pause di autoregolazione.",
  "pnev": "Priorità: regolazione sensoriale e uditiva con ingresso molto graduale, riflessi e tono, oculomotricità. Sedute brevi e prevedibili; evitare il contatto oculare imposto.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "FF",
   "socialita": "F"
  }
 },
 {
  "slug": "williams",
  "nome": "Sindrome di Williams",
  "codici": [
   "OMIM:194050"
  ],
  "base": "Microdelezione 7q11.23, che comprende il gene dell'elastina (ELN).",
  "forza": "Linguaggio espressivo e vocabolario, memoria uditiva verbale, riconoscimento dei volti, sensibilità musicale, forte spinta sociale.",
  "fragilita": "Disabilità intellettiva lieve-moderata; marcata difficoltà visuo-spaziale e visuo-costruttiva (disegno, copia, orientamento); calcolo; pragmatica più debole della forma.",
  "sensoriale": "Iperacusia e paura di rumori specifici; ipotonia iniziale, poi rigidità articolare; goffaggine, difficoltà nelle scale e nei dislivelli; strabismo, ipermetropia.",
  "regolazione": "Ipersocialità e fiducia indiscriminata verso gli estranei; ansia anticipatoria e fobie; disattenzione.",
  "salute": "Stenosi aortica sopravalvolare e altre stenosi arteriose, ipertensione, ipercalcemia nella prima infanzia, problemi alimentari precoci.",
  "leve": "Usare il canale verbale per guidare i compiti spaziali (istruzioni a voce, passo dopo passo), musica come mediatore, educazione esplicita alla sicurezza sociale.",
  "pnev": "Priorità: area visuo-spaziale e visuo-motoria (optometria comportamentale), equilibrio sui dislivelli. Stimolazione uditiva a volume contenuto e progressivo per l'iperacusia; la musica è un ottimo aggancio.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "P",
   "visuo_spaziale": "FF",
   "motorio": "F",
   "sensi": "FF",
   "socialita": "P"
  }
 },
 {
  "slug": "prader_willi",
  "nome": "Sindrome di Prader-Willi",
  "codici": [
   "OMIM:176270"
  ],
  "base": "Assenza dell'espressione dei geni paterni in 15q11-q13: delezione paterna, disomia uniparentale materna o difetto di imprinting.",
  "forza": "Abilità visuo-percettive (puzzle), memoria a lungo termine, lettura e vocabolario spesso migliori del previsto.",
  "fragilita": "Disabilità intellettiva lieve o funzionamento limite; elaborazione sequenziale, memoria uditiva a breve termine, aritmetica; articolazione e voce ipernasale.",
  "sensoriale": "Ipotonia grave neonatale con difficoltà di suzione; in seguito scarsa forza e resistenza; soglia del dolore elevata; strabismo e miopia.",
  "regolazione": "Iperfagia e ricerca del cibo dalla prima infanzia; rigidità, ripetitività, crisi di rabbia ai cambiamenti; skin picking.",
  "salute": "Obesità e complicanze, deficit di ormone della crescita, ipogonadismo, apnee del sonno, scoliosi.",
  "leve": "Controllo ambientale dell'accesso al cibo condiviso tra casa e scuola, routine e preavviso dei cambiamenti, attività motoria quotidiana, compiti visuo-percettivi come rinforzo.",
  "pnev": "Priorità: tono, resistenza e schema corporeo; binocularità (strabismo). Cautela: la soglia del dolore alta nasconde traumi e sovraccarichi; rinforzi mai alimentari.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "P",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "angelman",
  "nome": "Sindrome di Angelman",
  "codici": [
   "OMIM:105830"
  ],
  "base": "Perdita di funzione della copia materna di UBE3A (15q11-q13): delezione materna, variante del gene, disomia paterna o difetto di imprinting.",
  "forza": "Comprensione superiore all'espressione, interesse sociale, memoria per persone e luoghi, comunicazione non verbale.",
  "fragilita": "Disabilità intellettiva grave; linguaggio verbale assente o limitato a pochissime parole; attenzione molto breve.",
  "sensoriale": "Andatura atassica a base allargata, tremori, movimenti a scatti; strabismo; attrazione per l'acqua e per i materiali che riflettono.",
  "regolazione": "Disposizione felice con riso frequente, eccitabilità, ipermotricità; sonno ridotto e frammentato.",
  "salute": "Epilessia (frequente, a esordio precoce) con EEG caratteristico; scoliosi; reflusso.",
  "leve": "Comunicazione aumentativa e alternativa avviata presto, igiene del sonno, sicurezza negli ambienti con acqua, lavoro su equilibrio e deambulazione.",
  "pnev": "Priorità: equilibrio e deambulazione, attenzione visiva condivisa, regolazione sonno-veglia. Cautela: epilessia - evitare stimoli luminosi intermittenti senza parere del neurologo.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "delezione_22q11_2",
  "nome": "Sindrome da delezione 22q11.2",
  "codici": [
   "OMIM:188400",
   "OMIM:192430"
  ],
  "base": "Microdelezione 22q11.2 (DiGeorge / velo-cardio-facciale); in una parte dei casi ereditata da un genitore.",
  "forza": "Memoria verbale meccanica, lettura strumentale, abilità verbali spesso superiori a quelle non verbali.",
  "fragilita": "Funzionamento limite o disabilità intellettiva lieve; matematica, ragionamento astratto, abilità visuo-spaziali, attenzione e funzioni esecutive; comprensione del testo.",
  "sensoriale": "Insufficienza velofaringea con voce ipernasale e ritardo del linguaggio; ipotonia; ipoacusia per otiti; goffaggine motoria.",
  "regolazione": "Timidezza, ansia, ADHD; rischio aumentato di disturbi psicotici dall'adolescenza, da sorvegliare.",
  "salute": "Cardiopatie conotruncali, anomalie del palato, ipocalcemia, deficit immunitario, problemi alimentari.",
  "leve": "Valutazione foniatrica e logopedica precoce, materiali concreti per la matematica, monitoraggio psicologico longitudinale.",
  "pnev": "Priorità: udito ed elaborazione uditiva, abilità visuo-spaziali, coordinazione. Il lavoro sul palato e sulla voce resta di competenza foniatrica e logopedica.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "F",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "rett",
  "nome": "Sindrome di Rett",
  "codici": [
   "OMIM:312750"
  ],
  "base": "Varianti del gene MECP2 (Xq28) nella forma classica; quasi esclusivamente femmine.",
  "forza": "Sguardo intenso usato per comunicare, interesse per le persone e per la musica, comprensione spesso sottostimata.",
  "fragilita": "Dopo uno sviluppo iniziale apparentemente tipico, regressione tra 6 e 18 mesi con perdita dell'uso finalizzato delle mani e del linguaggio; disabilità grave.",
  "sensoriale": "Stereotipie delle mani sulla linea mediana, aprassia, atassia, deambulazione compromessa o assente; alterazioni del tono; soglia del dolore modificata.",
  "regolazione": "Fase di ritiro durante la regressione, poi recupero del contatto; irritabilità, disturbi del sonno, irregolarità del respiro in veglia.",
  "salute": "Epilessia, scoliosi, rallentamento della crescita del capo, problemi di alimentazione e crescita, QT lungo.",
  "leve": "Comunicazione con puntatore oculare, tempi di risposta lunghi, mantenimento della stazione eretta e del cammino, contenimento delle stereotipie durante il compito.",
  "pnev": "Priorità: sguardo e inseguimento visivo come canale comunicativo (eye tracking), mantenimento posturale, ritmo e musica. Cautela: epilessia, irregolarità respiratorie, QT lungo; tempi di risposta lunghi.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "V"
  }
 },
 {
  "slug": "turner",
  "nome": "Sindrome di Turner",
  "codici": [],
  "base": "Monosomia completa o parziale del cromosoma X (45,X e varianti, anche a mosaico); femmine.",
  "forza": "Intelligenza generalmente nella norma; abilità verbali, vocabolario e lettura strumentale buoni.",
  "fragilita": "Abilità visuo-spaziali, matematica, memoria di lavoro, funzioni esecutive, velocità di elaborazione; lettura dei segnali sociali.",
  "sensoriale": "Otiti ricorrenti e ipoacusia (trasmissiva e, con l'età, neurosensoriale); strabismo; coordinazione motoria talvolta impacciata.",
  "regolazione": "Immaturità sociale, ansia, bassa autostima; ADHD più frequente rispetto alla popolazione generale.",
  "salute": "Bassa statura, disgenesia gonadica, cardiopatie (coartazione aortica, valvola bicuspide), anomalie renali, tiroide.",
  "leve": "Strategie verbali per i compiti spaziali, sostegno mirato in matematica, abilità sociali, controlli audiologici regolari.",
  "pnev": "Priorità: abilità visuo-spaziali e visuo-motorie, udito (controlli ripetuti), coordinazione. Cautela: sforzi isometrici intensi solo con via libera cardiologica.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "P",
   "visuo_spaziale": "F",
   "motorio": "V",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "klinefelter",
  "nome": "Sindrome di Klinefelter",
  "codici": [],
  "base": "Un cromosoma X in più nei maschi (47,XXY e varianti); spesso diagnosticata tardi.",
  "forza": "Intelligenza per lo più nella norma; abilità non verbali e visuo-spaziali relativamente conservate.",
  "fragilita": "Ritardo e fragilità del linguaggio espressivo, lettura e scrittura (frequenti difficoltà di tipo dislessico), memoria verbale, funzioni esecutive.",
  "sensoriale": "Ipotonia lieve, ritardo delle tappe motorie, coordinazione e forza ridotte, facile affaticabilità.",
  "regolazione": "Timidezza, ritiro, ansia, scarsa assertività; difficoltà attentive.",
  "salute": "Ipogonadismo con possibile terapia sostitutiva dalla pubertà, ginecomastia, alta statura, infertilità.",
  "leve": "Logopedia precoce, sostegno agli apprendimenti letto-scrittori, attività motoria strutturata, lavoro sull'autostima.",
  "pnev": "Priorità: elaborazione uditivo-verbale a sostegno di linguaggio e lettura, tono e coordinazione, oculomotricità di lettura.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "P",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "neurofibromatosi_tipo_1",
  "nome": "Neurofibromatosi tipo 1",
  "codici": [
   "OMIM:162200"
  ],
  "base": "Varianti del gene NF1 (17q11.2); autosomica dominante, in circa metà dei casi de novo.",
  "forza": "Intelligenza in genere nella norma o medio-bassa; linguaggio di base e memoria verbale spesso adeguati.",
  "fragilita": "Disturbi dell'apprendimento molto frequenti; abilità visuo-spaziali e visuo-motorie, attenzione, funzioni esecutive, pianificazione.",
  "sensoriale": "Coordinazione fine e globale impacciata, ipotonia lieve. Il glioma delle vie ottiche può ridurre visus e campo visivo.",
  "regolazione": "ADHD frequente; difficoltà nelle relazioni con i pari; possibili tratti autistici.",
  "salute": "Controlli oculistici periodici nell'infanzia, neurofibromi, scoliosi e displasie ossee, pressione arteriosa, cefalea.",
  "leve": "Valutazione neuropsicologica all'ingresso a scuola, strumenti compensativi, lavoro visuo-motorio, attenzione ai cambiamenti della vista.",
  "pnev": "Priorità: abilità visuo-motorie e visuo-spaziali, attenzione, coordinazione. Ogni calo di visus o di campo visivo va inviato subito all'oculista (vie ottiche).",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "V",
   "visuo_spaziale": "F",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "sclerosi_tuberosa",
  "nome": "Sclerosi tuberosa",
  "codici": [
   "OMIM:191100",
   "OMIM:613254"
  ],
  "base": "Varianti di TSC1 (9q34) o TSC2 (16p13.3) con iperattivazione della via mTOR.",
  "forza": "Molto variabili: circa metà delle persone ha un'intelligenza nella norma.",
  "fragilita": "Dalla norma alla disabilità grave; più rischio con epilessia precoce e resistente. Attenzione, memoria, funzioni esecutive fragili anche con QI nella norma.",
  "sensoriale": "Dipende dalla sede delle lesioni cerebrali; possibili amartomi retinici, per lo più senza effetto sulla vista.",
  "regolazione": "Insieme dei disturbi neuropsichiatrici associati (TAND): autismo, ADHD, ansia, aggressività, disturbi del sonno.",
  "salute": "Epilessia (spasmi infantili), lesioni renali, cardiache, cutanee e polmonari: follow-up multispecialistico.",
  "leve": "Controllo delle crisi come priorità, screening periodico TAND, rivalutazione del profilo a ogni passaggio scolastico.",
  "pnev": "Priorità definite dal profilo individuale: attenzione, regolazione, sonno. Cautela: epilessia - nessuna stimolazione luminosa intermittente senza parere del neurologo.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "V",
   "visuo_spaziale": "V",
   "motorio": "V",
   "sensi": "F",
   "socialita": "F"
  }
 },
 {
  "slug": "cornelia_de_lange",
  "nome": "Sindrome di Cornelia de Lange",
  "codici": [
   "OMIM:122470",
   "OMIM:300590",
   "OMIM:610759",
   "OMIM:614701",
   "OMIM:300882"
  ],
  "base": "Varianti di NIPBL (più frequente) e di altri geni del complesso della coesina (SMC1A, SMC3, RAD21, HDAC8).",
  "forza": "Memoria visuo-spaziale, organizzazione percettiva, motricità fine nelle forme lievi, comprensione migliore della produzione.",
  "fragilita": "Disabilità intellettiva da lieve a grave; linguaggio espressivo molto compromesso, talvolta assente.",
  "sensoriale": "Ipoacusia frequente (trasmissiva e neurosensoriale); miopia, ptosi, blefarite; anomalie degli arti superiori; iper- o iporeattività sensoriale.",
  "regolazione": "Ansia sociale, mutismo selettivo, tratti autistici, autolesionismo che spesso segnala dolore.",
  "salute": "Reflusso gastroesofageo (causa frequente di disagio e comportamenti problema), ritardo di crescita, cardiopatie.",
  "leve": "Cercare sempre una causa fisica dietro il comportamento, comunicazione aumentativa, protesizzazione acustica precoce.",
  "pnev": "Priorità: udito (con protesi se indicate), regolazione sensoriale, attenzione visiva. Prima di lavorare sul comportamento escludere dolore e reflusso.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "P",
   "motorio": "F",
   "sensi": "F",
   "socialita": "F"
  }
 },
 {
  "slug": "smith_magenis",
  "nome": "Sindrome di Smith-Magenis",
  "codici": [
   "OMIM:182290"
  ],
  "base": "Microdelezione 17p11.2 che include RAI1, oppure variante del solo gene RAI1.",
  "forza": "Memoria a lungo termine per persone, luoghi ed eventi; ragionamento visivo; desiderio di relazione con l'adulto; umorismo.",
  "fragilita": "Disabilità intellettiva lieve-moderata; elaborazione sequenziale, memoria a breve termine; ritardo del linguaggio espressivo.",
  "sensoriale": "Ipotonia, ridotta sensibilità al dolore e alla temperatura; ipoacusia e otiti; miopia, strabismo; voce rauca.",
  "regolazione": "Ritmo sonno-veglia invertito per alterata secrezione di melatonina; impulsività, crisi di rabbia, autolesionismo, auto-abbraccio, ricerca continua di attenzione.",
  "salute": "Disturbo del sonno da trattare con lo specialista, scoliosi, anomalie cardiache e renali.",
  "leve": "Gestione del sonno come primo intervento, rapporto uno a uno, routine visive, prevenzione dei fattori scatenanti.",
  "pnev": "Priorità: regolazione del ritmo sonno-veglia concordata con lo specialista, autoregolazione, udito. Cautela: sensibilità al dolore ridotta.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "F",
   "socialita": "P"
  }
 },
 {
  "slug": "noonan",
  "nome": "Sindrome di Noonan",
  "codici": [
   "OMIM:163950"
  ],
  "base": "RASopatia: varianti di PTPN11 (circa metà dei casi), SOS1, RAF1, RIT1 e altri geni della via RAS-MAPK.",
  "forza": "Intelligenza nella norma nella maggioranza dei casi; buona socievolezza.",
  "fragilita": "Disabilità lieve in una minoranza; linguaggio e articolazione, attenzione, funzioni esecutive, memoria.",
  "sensoriale": "Ipotonia, ritardo motorio, goffaggine, lassità; ptosi, strabismo, difetti refrattivi; possibile ipoacusia.",
  "regolazione": "Difficoltà nel riconoscere ed esprimere le emozioni, immaturità sociale, disattenzione.",
  "salute": "Stenosi della valvola polmonare, cardiomiopatia ipertrofica, bassa statura, tendenza al sanguinamento, difficoltà alimentari precoci.",
  "leve": "Sostegno motorio e logopedico precoce, valutazione ortottica, verifica dell'idoneità cardiologica per l'attività fisica.",
  "pnev": "Priorità: binocularità e ptosi (valutazione optometrica e ortottica), tono e coordinazione, udito. Cautela: carichi motori da concordare con il cardiologo.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "V",
   "socialita": "V"
  }
 },
 {
  "slug": "cri_du_chat",
  "nome": "Sindrome del Cri du chat",
  "codici": [
   "OMIM:123450"
  ],
  "base": "Delezione del braccio corto del cromosoma 5 (5p-).",
  "forza": "Comprensione nettamente superiore all'espressione, interesse sociale, buona risposta ai gesti e ai segni.",
  "fragilita": "Disabilità intellettiva moderata-grave; linguaggio espressivo molto ritardato; motricità fine.",
  "sensoriale": "Ipotonia nella prima infanzia; ipersensibilità ai suoni; strabismo e miopia; pianto acuto caratteristico nel lattante.",
  "regolazione": "Iperattività, attenzione breve, stereotipie, talvolta autolesionismo; carattere affettuoso.",
  "salute": "Difficoltà di suzione e deglutizione, infezioni respiratorie, cardiopatie, scoliosi.",
  "leve": "Segni e comunicazione aumentativa fin dall'inizio, intervento precoce intensivo, strutturazione dell'ambiente.",
  "pnev": "Priorità: regolazione dell'ipersensibilità uditiva con ingresso graduale, tono, attenzione condivisa a sostegno della comunicazione gestuale.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "F",
   "socialita": "P"
  }
 },
 {
  "slug": "sotos",
  "nome": "Sindrome di Sotos",
  "codici": [
   "OMIM:117550"
  ],
  "base": "Varianti o delezione del gene NSD1 (5q35).",
  "forza": "Memoria verbale e abilità verbali relativamente migliori di quelle non verbali.",
  "fragilita": "Disabilità intellettiva per lo più lieve-moderata (possibile funzionamento nella norma); ragionamento non verbale, calcolo, ritardo del linguaggio.",
  "sensoriale": "Ipotonia, goffaggine e coordinazione scarsa, aggravate dalle dimensioni corporee; strabismo; otiti.",
  "regolazione": "Tratti autistici, ADHD, ansia, crisi di collera. L'aspetto «da più grande» induce aspettative eccessive.",
  "salute": "Iperaccrescimento con macrocefalia, scoliosi, epilessia in una parte dei casi, anomalie cardiache e renali.",
  "leve": "Tarare le richieste sull'età reale e sul profilo, non sulla statura; lavoro motorio e sulle abilità sociali.",
  "pnev": "Priorità: coordinazione e schema corporeo (corpo grande, controllo immaturo), binocularità, regolazione. Cautela se è presente epilessia.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "F",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "phelan_mcdermid",
  "nome": "Sindrome di Phelan-McDermid",
  "codici": [
   "OMIM:606232"
  ],
  "base": "Delezione 22q13.3 o variante del gene SHANK3.",
  "forza": "Interesse per le persone note, comprensione migliore della produzione, risposta alla musica e al movimento.",
  "fragilita": "Disabilità intellettiva moderata-grave; linguaggio assente o molto ritardato; possibili regressioni di abilità acquisite.",
  "sensoriale": "Ipotonia neonatale marcata, andatura instabile; soglia del dolore elevata; tendenza a portare oggetti alla bocca; ridotta sudorazione con rischio di surriscaldamento.",
  "regolazione": "Tratti dello spettro autistico molto frequenti, iperattività, disturbi del sonno.",
  "salute": "Epilessia, anomalie renali, linfedema, reflusso; sorvegliare i cambiamenti improvvisi del comportamento.",
  "leve": "Comunicazione aumentativa, routine stabili, ambiente fresco, osservazione attenta dei segnali di dolore.",
  "pnev": "Priorità: tono e stabilità posturale, attenzione visiva e uditiva condivisa. Cautela: epilessia, dolore non segnalato, surriscaldamento durante l'attività.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "F",
   "socialita": "F"
  }
 },
 {
  "slug": "kabuki",
  "nome": "Sindrome Kabuki",
  "codici": [
   "OMIM:147920",
   "OMIM:300867"
  ],
  "base": "Varianti di KMT2D (maggioranza dei casi) o KDM6A.",
  "forza": "Socievolezza, abilità verbali e memoria verbale relativamente migliori, interesse per la musica.",
  "fragilita": "Disabilità intellettiva lieve-moderata; abilità visuo-spaziali e visuo-costruttive; articolazione e prosodia.",
  "sensoriale": "Ipotonia e lassità articolare; ipoacusia e otiti ricorrenti; strabismo, ptosi, difetti refrattivi; anomalie del palato.",
  "regolazione": "Carattere aperto; ansia, disattenzione, rigidità in una parte dei casi.",
  "salute": "Cardiopatie congenite, infezioni ricorrenti, anomalie renali, difficoltà di alimentazione nei primi anni.",
  "leve": "Sfruttare il canale verbale, sostegno visuo-spaziale, controlli audiologici e oculistici regolari.",
  "pnev": "Priorità: udito, binocularità e abilità visuo-spaziali, tono. Carichi motori da adattare alla lassità articolare.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "P",
   "visuo_spaziale": "F",
   "motorio": "F",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "charge",
  "nome": "Sindrome CHARGE",
  "codici": [
   "OMIM:214800"
  ],
  "base": "Varianti del gene CHD7 nella maggior parte dei casi.",
  "forza": "Potenziale cognitivo spesso sottostimato per il doppio deficit sensoriale; buona memoria per routine e persone; tenacia.",
  "fragilita": "Sviluppo molto variabile; comunicazione e linguaggio condizionati da udito e vista; funzioni esecutive e autoregolazione.",
  "sensoriale": "Coloboma con deficit di campo e visus; ipoacusia mista; anomalie dei canali semicircolari con grave deficit di equilibrio; anosmia; coinvolgimento dei nervi cranici (deglutizione, mimica).",
  "regolazione": "Comportamenti ripetitivi e di autostimolazione, spesso funzionali a regolarsi; ansia; bassa tolleranza alla frustrazione.",
  "salute": "Cardiopatie, atresia delle coane, disfagia, ritardo di crescita e puberale.",
  "leve": "Approccio da sordocecità: comunicazione multimodale (tattile, segni, oggetti), tempi lunghi, ambiente leggibile.",
  "pnev": "Priorità: equilibrio e compensi vestibolari per via visiva e propriocettiva, uso del residuo visivo e uditivo. Cautela: disfagia e cardiopatia; stimolazione uditiva solo con quadro audiologico definito.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "FF",
   "socialita": "F"
  }
 },
 {
  "slug": "rubinstein_taybi",
  "nome": "Sindrome di Rubinstein-Taybi",
  "codici": [
   "OMIM:180849",
   "OMIM:613684"
  ],
  "base": "Varianti di CREBBP (maggioranza) o EP300; pollici e alluci larghi come segno caratteristico.",
  "forza": "Socievolezza e contatto facile, comprensione superiore all'espressione, amore per la musica.",
  "fragilita": "Disabilità intellettiva in genere moderata; linguaggio espressivo; attenzione breve; motricità fine.",
  "sensoriale": "Ipotonia, andatura rigida; strabismo, difetti refrattivi, ostruzione del dotto lacrimale, possibile glaucoma; otiti.",
  "regolazione": "Umore allegro; intolleranza al rumore e alla folla; con l'età possibili ansia e sbalzi d'umore.",
  "salute": "Cardiopatie, stipsi, apnee del sonno, cheloidi, attenzioni anestesiologiche.",
  "leve": "Segni e supporti visivi, attività brevi e variate, adattamenti per la presa.",
  "pnev": "Priorità: funzione visiva (inviare all'oculista ogni dubbio su pressione o trasparenza), motricità fine, regolazione uditiva.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "wolf_hirschhorn",
  "nome": "Sindrome di Wolf-Hirschhorn",
  "codici": [
   "OMIM:194190"
  ],
  "base": "Delezione del braccio corto del cromosoma 4 (4p16.3).",
  "forza": "Socialità e interesse per l'interazione, comprensione migliore dell'espressione, comunicazione gestuale.",
  "fragilita": "Disabilità intellettiva per lo più grave; linguaggio limitato a suoni o poche parole.",
  "sensoriale": "Ipotonia e massa muscolare ridotta, acquisizioni motorie tardive; ipoacusia; coloboma, strabismo, difetti refrattivi.",
  "regolazione": "Carattere socievole; stereotipie; disturbi del sonno.",
  "salute": "Epilessia molto frequente nei primi anni (tende a migliorare), ritardo di crescita, cardiopatie, anomalie renali, difficoltà alimentari.",
  "leve": "Comunicazione aumentativa, lavoro motorio precoce, obiettivi di autonomia graduali.",
  "pnev": "Priorità: tono e controllo posturale, attenzione visiva e uditiva. Cautela: epilessia - nessuna stimolazione luminosa intermittente senza parere del neurologo.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "pitt_hopkins",
  "nome": "Sindrome di Pitt-Hopkins",
  "codici": [
   "OMIM:610954"
  ],
  "base": "Varianti o delezione del gene TCF4 (18q21).",
  "forza": "Disposizione sorridente, piacere per la musica e per il contatto, interesse sociale.",
  "fragilita": "Disabilità intellettiva grave; linguaggio verbale assente nella maggior parte dei casi.",
  "sensoriale": "Ipotonia, andatura atassica e tardiva; miopia spesso elevata, strabismo; stereotipie delle mani.",
  "regolazione": "Episodi di iperventilazione e apnea in veglia, favoriti da emozione o stanchezza; ansia nei cambiamenti; sonno disturbato.",
  "salute": "Epilessia in una parte dei casi, stipsi grave, reflusso.",
  "leve": "Comunicazione aumentativa, correzione ottica precoce, routine, lavoro sul cammino.",
  "pnev": "Priorità: correzione e uso della visione, equilibrio, regolazione. Sospendere l'attività durante gli episodi respiratori; cautela se epilessia.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "P"
  }
 },
 {
  "slug": "distrofia_muscolare_duchenne",
  "nome": "Distrofia muscolare di Duchenne",
  "codici": [
   "OMIM:310200"
  ],
  "base": "Varianti del gene della distrofina (DMD, Xp21); maschi.",
  "forza": "Abilità visuo-spaziali e ragionamento non verbale in genere conservati; il profilo cognitivo non peggiora con la malattia.",
  "fragilita": "Intelligenza media spostata verso il basso; memoria di lavoro verbale, ritardo del linguaggio, lettura e scrittura, attenzione.",
  "sensoriale": "Debolezza muscolare progressiva a partenza prossimale, cadute, affaticabilità; perdita del cammino nel tempo.",
  "regolazione": "ADHD, tratti autistici e ossessivi più frequenti; umore da sorvegliare, anche per la terapia cortisonica.",
  "salute": "Cardiomiopatia, funzione respiratoria, scoliosi, fragilità ossea da corticosteroidi.",
  "leve": "Sostegno precoce a linguaggio e letto-scrittura, ausili e tecnologie, risparmio energetico, partecipazione sociale.",
  "pnev": "Priorità: elaborazione uditivo-verbale e oculomotricità di lettura, da seduto. Cautela assoluta: nessun esercizio di forza intenso o eccentrico; il lavoro motorio spetta al fisiatra e al fisioterapista.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "P",
   "motorio": "FF",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "usher",
  "nome": "Sindrome di Usher",
  "codici": [
   "OMIM:276900",
   "OMIM:276901"
  ],
  "base": "Autosomica recessiva; diversi geni (tra cui MYO7A nel tipo 1 e USH2A nel tipo 2).",
  "forza": "Intelligenza nella norma; buone risorse di compenso se i canali comunicativi sono costruiti per tempo.",
  "fragilita": "Accesso al linguaggio condizionato dalla sordità; con gli anni, perdita progressiva di autonomia visiva.",
  "sensoriale": "Ipoacusia neurosensoriale congenita; retinite pigmentosa con cecità notturna e restringimento del campo visivo; nel tipo 1 assenza di funzione vestibolare con cammino tardivo.",
  "regolazione": "Rischio di isolamento e di ansia legati alla doppia perdita sensoriale, soprattutto in adolescenza.",
  "salute": "Follow-up audiologico e oculistico-retinologico; protesi o impianto cocleare.",
  "leve": "Orientamento e mobilità, illuminazione e contrasto, comunicazione preparata prima del calo visivo (lingua dei segni, anche tattile).",
  "pnev": "Priorità: uso efficiente del campo visivo residuo ed esplorazione visiva, equilibrio per via propriocettiva. La stimolazione uditiva va concordata con l'audiologo.",
  "sinossi": {
   "cognitivo": "P",
   "linguaggio": "V",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "FF",
   "socialita": "V"
  }
 },
 {
  "slug": "tripla_x",
  "nome": "Sindrome della tripla X",
  "codici": [],
  "base": "Un cromosoma X in più nelle femmine (47,XXX); spesso non diagnosticata.",
  "forza": "Intelligenza per lo più nella norma; abilità non verbali e adattive buone.",
  "fragilita": "Linguaggio espressivo e ricettivo, lettura, memoria verbale, funzioni esecutive.",
  "sensoriale": "Ipotonia lieve, coordinazione impacciata, tappe motorie talvolta tardive; statura alta.",
  "regolazione": "Timidezza, ansia, bassa autostima, difficoltà attentive.",
  "salute": "Salute generalmente buona; possibili anomalie renali, crisi epilettiche, insufficienza ovarica precoce.",
  "leve": "Sostegno linguistico e agli apprendimenti, lavoro sulle abilità sociali e sull'autostima.",
  "pnev": "Priorità: elaborazione uditivo-verbale, tono e coordinazione, oculomotricità di lettura.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "xyy",
  "nome": "Sindrome XYY",
  "codici": [],
  "base": "Un cromosoma Y in più nei maschi (47,XYY); spesso non diagnosticata.",
  "forza": "Intelligenza per lo più nella norma; abilità non verbali relativamente conservate.",
  "fragilita": "Ritardo del linguaggio, lettura e scrittura, funzioni esecutive.",
  "sensoriale": "Ipotonia, coordinazione scarsa, tremore fine; statura alta.",
  "regolazione": "ADHD e impulsività, tratti autistici più frequenti. Lo stereotipo storico di aggressività non ha fondamento e va chiarito con famiglia e scuola.",
  "salute": "Salute generalmente buona; acne, asma e crisi epilettiche un po' più frequenti.",
  "leve": "Logopedia precoce, strategie per l'attenzione, attività motoria strutturata.",
  "pnev": "Priorità: elaborazione uditivo-verbale, autoregolazione, coordinazione.",
  "sinossi": {
   "cognitivo": "V",
   "linguaggio": "F",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "V",
   "socialita": "F"
  }
 },
 {
  "slug": "duplicazione_15q_dup15q",
  "nome": "Sindrome da duplicazione 15q (Dup15q)",
  "codici": [
   "OMIM:608636"
  ],
  "base": "Duplicazione di origine materna della regione 15q11.2-q13.1 (cromosoma isodicentrico o duplicazione interstiziale).",
  "forza": "Interesse per stimoli sensoriali e musica; nelle forme interstiziali quadro più lieve.",
  "fragilita": "Disabilità intellettiva moderata-grave; linguaggio molto compromesso; autismo molto frequente.",
  "sensoriale": "Ipotonia importante, ritardo motorio, andatura a base allargata; reattività sensoriale atipica.",
  "regolazione": "Ritiro sociale, stereotipie, iperattività, disturbi del sonno.",
  "salute": "Epilessia frequente e talvolta difficile da controllare (anche spasmi infantili).",
  "leve": "Intervento precoce, comunicazione aumentativa, strutturazione dell'ambiente.",
  "pnev": "Priorità: tono e postura, regolazione sensoriale. Cautela: epilessia - nessuna stimolazione luminosa intermittente senza parere del neurologo.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "F",
   "socialita": "F"
  }
 },
 {
  "slug": "delezione_16p11_2",
  "nome": "Delezione 16p11.2",
  "codici": [
   "OMIM:611913"
  ],
  "base": "Microdelezione 16p11.2; spesso de novo, talvolta ereditata da un genitore con quadro lieve.",
  "forza": "Abilità non verbali spesso migliori di quelle verbali; socialità variabile ma presente.",
  "fragilita": "Disturbo del linguaggio con difficoltà di programmazione articolatoria; funzionamento limite o disabilità lieve; apprendimenti.",
  "sensoriale": "Ipotonia lieve, coordinazione motoria impacciata.",
  "regolazione": "Tratti dello spettro autistico in una parte dei casi, ADHD, ansia.",
  "salute": "Tendenza all'obesità dall'infanzia, epilessia in una parte dei casi, macrocefalia.",
  "leve": "Logopedia intensiva e precoce, eventuale supporto aumentativo, attività fisica regolare.",
  "pnev": "Priorità: elaborazione uditiva e sequenze motorie, coordinazione. Il trattamento del disturbo articolatorio è logopedico.",
  "sinossi": {
   "cognitivo": "F",
   "linguaggio": "FF",
   "visuo_spaziale": "P",
   "motorio": "F",
   "sensi": "V",
   "socialita": "V"
  }
 },
 {
  "slug": "marfan",
  "nome": "Sindrome di Marfan",
  "codici": [
   "OMIM:154700"
  ],
  "base": "Varianti del gene della fibrillina-1 (FBN1); autosomica dominante.",
  "forza": "Intelligenza nella norma; nessun profilo cognitivo specifico.",
  "fragilita": "Apprendimento ostacolato da problemi visivi, affaticabilità, dolore e assenze; attenzione in una parte dei casi.",
  "sensoriale": "Lussazione del cristallino, miopia elevata, rischio di distacco di retina; lassità articolare, scoliosi, statura alta e arti lunghi.",
  "regolazione": "Vissuti legati all'aspetto fisico e alle limitazioni sportive; ansia per la salute.",
  "salute": "Dilatazione dell'aorta: follow-up cardiologico e limitazione di sport di contatto e sforzi isometrici.",
  "leve": "Correzione ottica accurata, postazione e carichi adattati, attività fisica consentita dal cardiologo.",
  "pnev": "Priorità: valutazione optometrica fine. Cautela assoluta: niente sforzi isometrici, apnee da sforzo o urti; ogni sintomo visivo improvviso (lampi, ombre) va inviato d'urgenza all'oculista.",
  "sinossi": {
   "cognitivo": "P",
   "linguaggio": "P",
   "visuo_spaziale": "V",
   "motorio": "F",
   "sensi": "FF",
   "socialita": "V"
  }
 },
 {
  "slug": "delezione_1p36",
  "nome": "Delezione 1p36",
  "codici": [
   "OMIM:607872"
  ],
  "base": "Delezione terminale del braccio corto del cromosoma 1; tra le microdelezioni terminali più frequenti.",
  "forza": "Interesse per l'interazione, comunicazione gestuale, miglioramento lento ma continuo.",
  "fragilita": "Disabilità intellettiva moderata-grave; linguaggio assente o a poche parole.",
  "sensoriale": "Ipotonia marcata, ritardo motorio; ipoacusia; strabismo, difetti refrattivi, possibili difficoltà visive di origine centrale.",
  "regolazione": "Stereotipie, crisi di collera, talvolta autolesionismo.",
  "salute": "Epilessia, cardiopatie e cardiomiopatia, disfagia, ipotiroidismo.",
  "leve": "Comunicazione aumentativa, sostegno alla deglutizione con gli specialisti, ausili posturali.",
  "pnev": "Priorità: tono e controllo posturale, attenzione visiva (anche con ipotesi di deficit centrale), udito. Cautela: epilessia e cardiopatia.",
  "sinossi": {
   "cognitivo": "FF",
   "linguaggio": "FF",
   "visuo_spaziale": "V",
   "motorio": "FF",
   "sensi": "F",
   "socialita": "V"
  }
 }
]

PER_SLUG = {p["slug"]: p for p in PROFILI}
PER_CODICE = {c: p for p in PROFILI for c in p["codici"]}

_COD_VOLTO = {v[1] for v in VOLTO} | {b[1] for b in BRIDGE if b[0] == "F"}


def per_codice(disease_id: str | None) -> dict | None:
    """La scheda di funzionamento per un codice sindrome (es. 'OMIM:194050'), se esiste."""
    return PER_CODICE.get((disease_id or "").strip().upper())


def dividi_segni(profilo: dict[str, dict]) -> dict[str, dict[str, list[str]]]:
    """Divide i segni del paziente in «volto» e «funzionamento», presenti e assenti.
    È volto ciò che viene dalla scheda «Volto e foto» o dall'area «Volto e corpo» della tabella ponte."""
    out = {"volto": {"presenti": [], "assenti": []}, "funzionamento": {"presenti": [], "assenti": []}}
    for h, v in profilo.items():
        gruppo = "volto" if (h in _COD_VOLTO or (v.get("fonte") or "").startswith("volto")) else "funzionamento"
        chiave = "presenti" if v.get("stato") == "presente" else "assenti"
        out[gruppo][chiave].append(h)
    return out


def _punteggi(m, presenti: list[str], assenti: list[str]):
    """Punteggio di tutte le sindromi per un gruppo di segni, oppure None se i segni sono troppo pochi."""
    pres = [m.idx[h] for h in presenti if h in m.idx]
    ass = [m.idx[h] for h in assenti if h in m.idx]
    if len(pres) < MIN_SEGNI:
        return None
    return m._score_all(pres, ass)


def _migliore(m, sc, codici: list[str]):
    """(punteggio, posizione su tutte le sindromi) del codice migliore fra quelli della scheda."""
    if sc is None:
        return None, None
    best = None
    for c in codici:
        di = m.dis_index.get(c)
        if di is None:
            continue
        s = float(sc[di])
        if best is None or s > best[0]:
            best = (s, int((sc > sc[di]).sum()) + 1)
    return best if best else (None, None)


def _lettura(pos_v, pos_f) -> str:
    if pos_v is None and pos_f is None:
        return "segni insufficienti"
    if pos_v is None:
        return "volto non valutato"
    if pos_f is None:
        return "funzionamento non valutato"
    v, f = pos_v <= PRIME, pos_f <= PRIME
    if v and f:
        return "volto e funzionamento concordano"
    if v:
        return "solo il volto"
    if f:
        return "solo il funzionamento"
    return "nessuno dei due"


def incrocio(m, profilo: dict[str, dict]) -> list[dict]:
    """Per ogni scheda con codice HPO: somiglianza dal volto, dal funzionamento e complessiva.
    Ordinata per somiglianza complessiva. m è il MotoreGenetica."""
    g = dividi_segni(profilo)
    sc_v = _punteggi(m, g["volto"]["presenti"], g["volto"]["assenti"])
    sc_f = _punteggi(m, g["funzionamento"]["presenti"], g["funzionamento"]["assenti"])
    sc_t = _punteggi(m, g["volto"]["presenti"] + g["funzionamento"]["presenti"],
                     g["volto"]["assenti"] + g["funzionamento"]["assenti"])
    righe = []
    for p in PROFILI:
        if not any(c in m.dis_index for c in p["codici"]):
            continue
        sv, pv = _migliore(m, sc_v, p["codici"])
        sf, pf = _migliore(m, sc_f, p["codici"])
        stt, pt = _migliore(m, sc_t, p["codici"])
        righe.append({"slug": p["slug"], "nome": p["nome"],
                      "volto": None if sv is None else round(max(sv, 0.0), 3), "pos_volto": pv,
                      "funzionamento": None if sf is None else round(max(sf, 0.0), 3), "pos_funzionamento": pf,
                      "insieme": None if stt is None else round(max(stt, 0.0), 3), "pos_insieme": pt,
                      "lettura": _lettura(pv, pf)})
    righe.sort(key=lambda r: -(r["insieme"] if r["insieme"] is not None else -1))
    return righe


def dettaglio_segni(m, profilo: dict[str, dict], slug: str) -> dict:
    """Per la sindrome scelta: quali segni del paziente coincidono (volto / funzionamento) e quali
    segni tipici della sindrome non sono ancora stati valutati (da guardare sulla foto, da misurare)."""
    p = PER_SLUG[slug]
    vuoto = {"volto_ok": [], "funz_ok": [], "volto_da_guardare": [], "funz_da_misurare": [], "contrari": []}
    indici = [m.dis_index[c] for c in p["codici"] if c in m.dis_index]
    if not indici:
        return vuoto
    cl: dict[int, float] = {}
    for di in indici:
        for t, f in (m.overlay.get(di) or m.closure(m.dis_terms[di])).items():
            cl[t] = max(cl.get(t, 0.0), f)
    g = dividi_segni(profilo)
    out = dict(vuoto)
    out["volto_ok"] = [h for h in g["volto"]["presenti"] if h in m.idx and m.idx[h] in cl]
    out["funz_ok"] = [h for h in g["funzionamento"]["presenti"] if h in m.idx and m.idx[h] in cl]
    # segni segnati ASSENTI nel paziente ma tipici della sindrome: vanno contro l'ipotesi
    out["contrari"] = [h for h, v in profilo.items() if v.get("stato") == "assente"
                       and h in m.idx and cl.get(m.idx[h], 0.0) >= SOGLIA_TIPICO]

    def tipici(codici_etichette):
        r = []
        for h, etichetta in codici_etichette:
            if h in profilo or h not in m.idx:
                continue
            f = cl.get(m.idx[h], 0.0)
            if f >= SOGLIA_TIPICO:
                r.append((h, etichetta, round(f, 2)))
        return sorted(r, key=lambda x: -x[2])

    out["volto_da_guardare"] = tipici([(v[1], v[2]) for v in VOLTO] + [(b[1], b[2]) for b in BRIDGE if b[0] == "F"])
    out["funz_da_misurare"] = tipici([(b[1], b[2]) for b in BRIDGE if b[0] != "F"])
    return out


def testo_profilo(nome_paziente: str, slug: str | None, griglia: dict[str, dict]) -> str:
    """Profilo di funzionamento individuale in testo semplice (per relazione o stampa)."""
    p = PER_SLUG.get(slug or "")
    righe = [f"PROFILO DI FUNZIONAMENTO{' · ' + nome_paziente if nome_paziente else ''}"]
    if p:
        righe.append(f"Sindrome di riferimento: {p['nome']}")
    righe.append("Qualificatori ICF: 0 nessuna difficoltà, 1 lieve, 2 media, 3 grave, 4 completa.")
    for chiave, etichetta, campi in DIMENSIONI:
        v = griglia.get(chiave) or {}
        righe.append("")
        righe.append(etichetta.upper())
        if p:
            righe.append("Atteso per la sindrome: " + " ".join(dict.fromkeys(p[c] for c in campi)))
        righe.append("Osservato: " + ((v.get("osservato") or "").strip() or "non compilato"))
        q = v.get("qualificatore")
        righe.append("Qualificatore: " + ("non indicato" if q is None else str(q)))
        if (v.get("contesto") or "").strip():
            righe.append("Facilitatori / barriere: " + v["contesto"].strip())
    return "\n".join(righe)
