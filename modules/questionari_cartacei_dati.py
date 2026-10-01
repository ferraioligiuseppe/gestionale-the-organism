# -*- coding: utf-8 -*-
"""Questionari cartacei aggiuntivi, estratti dalle app di screening e
valutazione dello studio (stesse domande della versione a schermo) e il
questionario INPP-R adulti di app_core.

Formato: codice -> [etichetta, titolo, sottotitolo, blocchi]
blocchi: ["scala", intestazione, etichette, voci, nota] | ["campi", [[etichetta, opzioni|None, multipla]]]
         | ["h3", testo] | ["label", testo] | ["linea", n] | ["item", voci]
"""

QUESTIONARI_EXTRA = {
 "A_SINTOMI_VISIVI": [
  "👓 Adulti · Sintomi visivi",
  "Sintomi visivi e affaticamento",
  "Per ogni voce indichi quanto spesso le capita.",
  [
   [
    "scala",
    "Sintomi visivi (0 mai · 4 sempre)",
    [
     "0",
     "1",
     "2",
     "3",
     "4"
    ],
    [
     "Occhi stanchi o pesanti leggendo o al computer",
     "Bruciore, prurito o lacrimazione",
     "Mal di testa dopo il lavoro da vicino",
     "Visione annebbiata da vicino",
     "Visione doppia",
     "Righe che si muovono o si confondono",
     "Perde il segno o rilegge la stessa riga",
     "Fatica a mettere a fuoco passando da vicino a lontano",
     "Sonnolenza leggendo",
     "Fatica a concentrarsi sul testo"
    ],
    ""
   ]
  ]
 ],
 "A_ATTENZIONE": [
  "🎯 Adulti · Attenzione nella vita quotidiana",
  "Attenzione e memoria nella vita di tutti i giorni",
  "",
  [
   [
    "scala",
    "Nella vita di tutti i giorni (0 mai · 1 a volte · 2 spesso)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "Perde il filo mentre legge o ascolta",
     "Dimentica appuntamenti o cose da fare",
     "Fatica a concentrarsi con rumori o interruzioni",
     "Lascia a metà ciò che inizia",
     "Si sente mentalmente stanco a metà giornata",
     "Deve rileggere più volte per capire"
    ],
    ""
   ]
  ]
 ],
 "A_CEFALEA": [
  "🤕 Adulti · Cefalea e dolore",
  "Cefalea e dolore",
  "Se ha uno dei segnali d'allarme in fondo, ne parli con il medico prima della visita.",
  [
   [
    "campi",
    [
     [
      "Giorni con mal di testa al mese",
      [],
      0
     ],
     [
      "Intensità abituale (0–10)",
      [],
      0
     ],
     [
      "Sede",
      [
       "frontale",
       "temporale",
       "nucale",
       "dietro gli occhi",
       "emicrania (metà testa)",
       "diffusa"
      ],
      0
     ],
     [
      "Quando compare",
      [
       "dopo lavoro da vicino o schermo",
       "al risveglio",
       "a fine giornata",
       "con stress",
       "con il ciclo",
       "senza un momento preciso"
      ],
      1
     ],
     [
      "Giorni al mese con antidolorifici",
      [],
      0
     ],
     [
      "Dolore cervicale o alle spalle",
      [
       "no",
       "a volte",
       "spesso"
      ],
      0
     ],
     [
      "Segnali d'allarme (se presenti: invio medico)",
      [
       "esordio improvviso e violento",
       "cefalea nuova dopo i 50 anni",
       "con febbre o rigidità del collo",
       "con debolezza, formicolii o difficoltà a parlare",
       "peggiora progressivamente",
       "la sveglia di notte",
       "dopo un trauma recente"
      ],
      1
     ]
    ]
   ]
  ]
 ],
 "A_ABITUDINI": [
  "🌙 Adulti · Sonno, stress, alimentazione",
  "Sonno, stress e alimentazione",
  "",
  [
   [
    "campi",
    [
     [
      "Ore di sonno per notte",
      [],
      0
     ],
     [
      "Sonno",
      [
       "riposante",
       "fatica ad addormentarsi",
       "risvegli frequenti",
       "risveglio precoce",
       "russa o apnee riferite"
      ],
      0
     ],
     [
      "Stress percepito (0–10)",
      [],
      0
     ],
     [
      "Schermi nell'ora prima di dormire",
      [
       "no",
       "sì"
      ],
      0
     ],
     [
      "Colazione",
      [
       "tutti i giorni",
       "a volte",
       "mai"
      ],
      0
     ],
     [
      "Frutta e verdura",
      [
       "5 porzioni o più",
       "2–4 porzioni",
       "meno di 2"
      ],
      0
     ],
     [
      "Cibi industriali, dolci, bibite zuccherate",
      [
       "raramente",
       "ogni settimana",
       "ogni giorno"
      ],
      0
     ],
     [
      "Caffè al giorno",
      [],
      0
     ],
     [
      "Alcol",
      [
       "no",
       "occasionale",
       "ogni giorno"
      ],
      0
     ],
     [
      "Attività fisica",
      [
       "almeno 150 minuti a settimana",
       "meno",
       "quasi nessuna"
      ],
      0
     ]
    ]
   ]
  ]
 ],
 "A_VDT": [
  "🖥️ Adulti · Videoterminale",
  "Lavoro al videoterminale",
  "",
  [
   [
    "campi",
    [
     [
      "Ore al giorno davanti allo schermo",
      [],
      0
     ],
     [
      "Pause",
      [
       "ogni ora o meno",
       "ogni 2 ore",
       "raramente"
      ],
      0
     ],
     [
      "Distanza occhi-schermo (cm)",
      [],
      0
     ],
     [
      "Bordo alto dello schermo",
      [
       "all'altezza degli occhi o sotto",
       "sopra gli occhi"
      ],
      0
     ],
     [
      "Luce e riflessi",
      [
       "adeguati",
       "finestra davanti o dietro",
       "riflessi sullo schermo"
      ],
      0
     ],
     [
      "Numero di schermi",
      [],
      0
     ],
     [
      "Lenti da lavoro",
      [
       "no",
       "monofocali da vicino",
       "progressive",
       "office"
      ],
      0
     ]
    ]
   ]
  ]
 ],
 "A_TRAUMA": [
  "🩹 Adulti · Trauma cranico e colpo di frusta",
  "Trauma cranico o colpo di frusta",
  "Se ha uno dei segnali d'allarme, vada subito dal medico o al pronto soccorso.",
  [
   [
    "campi",
    [
     [
      "Data dell'evento",
      [],
      0
     ],
     [
      "Tipo",
      [
       "trauma cranico",
       "colpo di frusta",
       "entrambi"
      ],
      0
     ],
     [
      "Perdita di coscienza",
      [
       "no",
       "sì, meno di 1 minuto",
       "sì, più a lungo",
       "non ricorda"
      ],
      0
     ],
     [
      "Segnali d'allarme (se presenti: invio medico urgente)",
      [
       "vomito ripetuto",
       "mal di testa in peggioramento",
       "confusione o sonnolenza crescente",
       "debolezza o formicolii",
       "convulsioni",
       "evento da meno di 48 ore"
      ],
      1
     ]
    ]
   ],
   [
    "scala",
    "Sintomi da allora (0 no · 3 molto)",
    [
     "0",
     "1",
     "2",
     "3"
    ],
    [
     "Mal di testa",
     "Vertigini o instabilità",
     "Nausea",
     "Fastidio per la luce",
     "Fastidio per il rumore",
     "Visione offuscata",
     "Visione doppia",
     "Difficoltà di concentrazione",
     "Difficoltà di memoria",
     "Stanchezza",
     "Irritabilità",
     "Sonno alterato"
    ],
    ""
   ]
  ]
 ],
 "A_DSA": [
  "📖 Adulti · Lettura e scrittura (DSA)",
  "Lettura, scrittura e calcolo",
  "",
  [
   [
    "scala",
    "Storia e vita di oggi (0 no · 1 in parte · 2 sì)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "A scuola leggeva più lentamente dei compagni",
     "Ha avuto difficoltà a imparare le tabelline",
     "Fa ancora errori di ortografia che conosce",
     "Evita di leggere ad alta voce in pubblico",
     "Legge lentamente testi lunghi di lavoro",
     "Confonde numeri di telefono o cifre",
     "Fatica a prendere appunti mentre ascolta",
     "In famiglia c'è qualcuno con dislessia"
    ],
    ""
   ],
   [
    "campi",
    [
     [
      "Certificazione DSA",
      [
       "no",
       "sì, da bambino",
       "sì, da adulto"
      ],
      0
     ]
    ]
   ]
  ]
 ],
 "A_ADHD": [
  "⚡ Adulti · Attenzione e impulsività (ADHD)",
  "Attenzione, organizzazione e impulsività",
  "Domande dello studio, non un test tarato.",
  [
   [
    "scala",
    "Negli ultimi 6 mesi (0 mai · 1 a volte · 2 spesso)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "Fatica a finire i dettagli di un lavoro",
     "Fatica a organizzare compiti che richiedono ordine",
     "Rimanda le cose che richiedono concentrazione",
     "Muove mani o piedi quando deve stare seduto a lungo",
     "Si sente spinto a fare, come da un motore",
     "Interrompe gli altri o finisce le loro frasi",
     "Perde oggetti di uso quotidiano",
     "Si distrae con rumori o attività intorno",
     "Fatica ad aspettare il proprio turno"
    ],
    "Items dello studio, non un test tarato."
   ],
   [
    "campi",
    [
     [
      "Difficoltà simili già da bambino",
      [
       "no",
       "non ricorda",
       "sì"
      ],
      0
     ]
    ]
   ]
  ]
 ],
 "A_UMORE": [
  "💬 Adulti · Umore e ansia (PHQ-9, GAD-7)",
  "Umore e ansia",
  "Se alla domanda 9 ha risposto diverso da 0, ne parli subito con il suo medico o chiami lo studio.",
  [
   [
    "scala",
    "PHQ-9 — nelle ultime 2 settimane (0 mai · 1 alcuni giorni · 2 più della metà dei giorni · 3 quasi ogni giorno)",
    [
     "0",
     "1",
     "2",
     "3"
    ],
    [
     "Scarso interesse o piacere nel fare le cose",
     "Sentirsi giù, depresso o senza speranza",
     "Difficoltà ad addormentarsi, a dormire tutta la notte, o dormire troppo",
     "Sentirsi stanco o avere poca energia",
     "Scarso appetito o mangiare troppo",
     "Avere una scarsa opinione di sé, o sentirsi un fallito",
     "Difficoltà a concentrarsi, per esempio leggendo o guardando la televisione",
     "Muoversi o parlare così lentamente da essere notato, oppure essere così agitato da muoversi molto più del solito",
     "Pensare che sarebbe meglio essere morto o farsi del male in qualche modo"
    ],
    "La domanda 9 va sempre letta: se la risposta non è 0, parlarne subito con la persona e indirizzarla al medico."
   ],
   [
    "scala",
    "GAD-7 — nelle ultime 2 settimane",
    [
     "0",
     "1",
     "2",
     "3"
    ],
    [
     "Sentirsi nervoso, ansioso o teso",
     "Non riuscire a smettere di preoccuparsi o a controllare le preoccupazioni",
     "Preoccuparsi troppo per varie cose",
     "Avere difficoltà a rilassarsi",
     "Essere così irrequieto da far fatica a stare seduto",
     "Irritarsi o arrabbiarsi facilmente",
     "Avere paura che possa succedere qualcosa di terribile"
    ],
    ""
   ]
  ]
 ],
 "A_VERTIGINI": [
  "🌀 Adulti · Vertigini e mal d'auto",
  "Vertigini e mal di movimento",
  "Se ha uno dei segni che accompagnano la vertigine, vada subito dal medico.",
  [
   [
    "campi",
    [
     [
      "Che cosa prova",
      [
       "nessuna vertigine",
       "gira tutto (rotatoria)",
       "instabilità, come su una barca",
       "sensazione di svenire",
       "testa leggera"
      ],
      0
     ],
     [
      "Frequenza",
      [
       "rara",
       "ogni mese",
       "ogni settimana",
       "ogni giorno"
      ],
      0
     ],
     [
      "Quando compare",
      [
       "girando la testa o a letto",
       "alzandosi in piedi",
       "in luoghi affollati o supermercati",
       "guardando schermi o scorrendo pagine",
       "in auto o in treno",
       "senza un motivo preciso"
      ],
      1
     ],
     [
      "Insieme alla vertigine (se presenti: invio medico urgente)",
      [
       "visione doppia",
       "difficoltà a parlare o a deglutire",
       "debolezza o formicolio a un lato",
       "perdita improvvisa dell'udito",
       "mal di testa violento"
      ],
      1
     ]
    ]
   ],
   [
    "scala",
    "Mal di movimento (0 mai · 3 sempre)",
    [
     "0",
     "1",
     "2",
     "3"
    ],
    [
     "In auto da passeggero",
     "Leggendo in auto",
     "In nave o in traghetto",
     "Al cinema, con i videogiochi o la realtà virtuale",
     "Scorrendo lo schermo del telefono"
    ],
    ""
   ]
  ]
 ],
 "A_STOPBANG": [
  "😴 Adulti · Russamento e apnee (STOP-Bang)",
  "Russamento e apnee nel sonno",
  "Risponda sì o no. Pressione, peso e collo li misuriamo in studio se non li conosce.",
  [
   [
    "scala",
    "STOP-Bang",
    [
     "no",
     "sì"
    ],
    [
     "Russa forte",
     "Si sente spesso stanco o assonnato di giorno",
     "Qualcuno ha notato che smette di respirare durante il sonno",
     "Ha o è in cura per la pressione alta",
     "Indice di massa corporea oltre 35",
     "Età oltre 50 anni",
     "Circonferenza del collo oltre 40 cm",
     "Sesso maschile"
    ],
    ""
   ]
  ]
 ],
 "A_FAMILIARE": [
  "👪 Adulti · Domande al familiare",
  "Domande al familiare",
  "Da far compilare a un familiare o a chi conosce bene la persona.",
  [
   [
    "scala",
    "Rispetto a qualche anno fa, ci sono cambiamenti in… (a un familiare o a chi lo conosce bene)",
    [
     "no",
     "sì"
    ],
    [
     "Capacità di giudizio o decisioni",
     "Interesse per hobby e attività",
     "Ripete le stesse domande o racconti",
     "Imparare a usare strumenti nuovi",
     "Ricordare il mese o l'anno",
     "Gestire conti e pagamenti",
     "Ricordare appuntamenti",
     "Problemi quotidiani di memoria o ragionamento"
    ],
    "Items dello studio."
   ]
  ]
 ],
 "B_SINTOMI_VISIVI": [
  "👁️ Bambini · Sintomi visivi",
  "Sintomi visivi",
  "Da compilare con i genitori.",
  [
   [
    "scala",
    "Sintomi visivi (0 mai · 1 a volte · 2 spesso)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "Bruciore, prurito o lacrimazione leggendo",
     "Mal di testa dopo lo studio o gli schermi",
     "Righe che si muovono o si sdoppiano",
     "Perde il segno o salta righe",
     "Vista che si annebbia dopo un po'"
    ],
    ""
   ]
  ]
 ],
 "B_ATTENZIONE": [
  "🎯 Bambini · Attenzione",
  "Attenzione nella vita di tutti i giorni",
  "Da compilare con i genitori.",
  [
   [
    "scala",
    "Questionario (0 mai · 1 a volte · 2 spesso)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "Si distrae facilmente",
     "Fatica a finire ciò che inizia",
     "Perde o dimentica le cose",
     "Si agita quando dovrebbe stare fermo",
     "Risponde prima che la domanda sia finita",
     "Fatica ad aspettare il proprio turno"
    ],
    "Ai genitori; dai 14 anni al ragazzo e a un genitore insieme."
   ]
  ]
 ],
 "B_EMOTIVO": [
  "💛 Bambini · Emotivo-comportamentale",
  "Emozioni e comportamento",
  "Da compilare con i genitori.",
  [
   [
    "scala",
    "Questionario (0 mai · 1 a volte · 2 spesso)",
    [
     "0",
     "1",
     "2"
    ],
    [
     "Si preoccupa molto, anche per piccole cose",
     "Appare triste o giù di morale",
     "Ha paure che gli impediscono cose della sua età",
     "Si arrabbia facilmente e fatica a calmarsi",
     "Si oppone alle regole più dei coetanei",
     "Fatica a fare o a mantenere amicizie",
     "Preferisce stare da solo",
     "Lamenta mal di pancia o di testa senza una causa evidente",
     "Evita situazioni nuove o si separa a fatica dai genitori",
     "Ha cambi d'umore improvvisi"
    ],
    "Si può far compilare ai genitori mentre si svolgono le altre prove; dai 14 anni al ragazzo e a un genitore insieme. Items interni dello studio, non un test tarato."
   ],
   [
    "campi",
    [
     [
      "Punti di forza",
      [],
      0
     ]
    ]
   ]
  ]
 ],
 "B_ABITUDINI": [
  "🍎 Bambini · Sonno, alimentazione, schermi",
  "Sonno, alimentazione e schermi",
  "Da compilare con i genitori.",
  [
   [
    "h3",
    "Sonno e schermi"
   ],
   [
    "campi",
    [
     [
      "Ore di sonno per notte",
      [],
      0
     ],
     [
      "Sonno",
      [
       "tranquillo",
       "fatica ad addormentarsi",
       "risvegli frequenti",
       "incubi o pavor nocturnus",
       "russamento"
      ],
      0
     ],
     [
      "Schermi al giorno",
      [
       "nessuno",
       "meno di 1 ora",
       "1–2 ore",
       "2–4 ore",
       "oltre 4 ore"
      ],
      0
     ],
     [
      "Schermi nell'ora prima di dormire",
      [
       "no",
       "sì"
      ],
      0
     ],
     [
      "Gioco all'aperto o attività fisica",
      [
       "ogni giorno",
       "2–3 volte a settimana",
       "raramente"
      ],
      0
     ]
    ]
   ],
   [
    "h3",
    "Alimentazione"
   ],
   [
    "campi",
    [
     [
      "Colazione",
      [
       "tutti i giorni",
       "a volte",
       "mai"
      ],
      0
     ],
     [
      "Frutta e verdura",
      [
       "5 porzioni o più al giorno",
       "2–4 porzioni",
       "meno di 2"
      ],
      0
     ],
     [
      "Dolci, merendine, bibite zuccherate",
      [
       "raramente",
       "qualche volta a settimana",
       "ogni giorno"
      ],
      0
     ],
     [
      "Cibi industriali, fast food, snack salati",
      [
       "raramente",
       "ogni settimana",
       "ogni giorno"
      ],
      0
     ],
     [
      "Latte e latticini",
      [
       "poco o niente",
       "una volta al giorno",
       "più volte al giorno"
      ],
      0
     ],
     [
      "Acqua durante il giorno",
      [
       "a sufficienza",
       "poca"
      ],
      0
     ],
     [
      "Selettività alimentare",
      [
       "no",
       "lieve",
       "marcata"
      ],
      0
     ],
     [
      "Masticazione",
      [
       "normale",
       "difficoltosa"
      ],
      0
     ],
     [
      "Intolleranze o allergie note",
      [],
      0
     ]
    ]
   ]
  ]
 ],
 "INPPS_ADULTI": [
  "🧬 INPP-R Adulti",
  "INPP-R — Screening riflessi primitivi (adulti)",
  "Questionario INPP adattato per l'età adulta. Barri le voci a cui risponde sì.",
  [
   [
    "label",
    "Ha ricevuto qualche diagnosi (dislessia, disprassia, disturbo da deficit di attenzione, iperattività, agorafobia, crisi di panico o altro)? Se sì, quale:"
   ],
   [
    "linea",
    2
   ],
   [
    "label",
    "Farmaci che assume attualmente (con dosaggio e data di inizio):"
   ],
   [
    "linea",
    2
   ],
   [
    "label",
    "Sintomi o difficoltà principali:"
   ],
   [
    "linea",
    2
   ],
   [
    "label",
    "Diagnosi o terapie psichiatriche:"
   ],
   [
    "linea",
    1
   ],
   [
    "label",
    "Altre informazioni sulla sua salute:"
   ],
   [
    "linea",
    1
   ],
   [
    "h3",
    "Prima parte — Storia dello sviluppo"
   ],
   [
    "item",
    [
     "C'è qualche caso di difficoltà simili fra i genitori o le loro famiglie?",
     "È stato/a concepito/a con fecondazione assistita (FIVET)?",
     "Durante la gravidanza c'è stato qualche problema medico? (pressione alta, nausea eccessiva, rischio di aborto, infezioni virali, stress emotivo importante)",
     "Ha fumato la madre durante la gravidanza?",
     "Ha bevuto alcol la madre durante la gravidanza?",
     "Ha sofferto la madre di un'importante infezione virale durante le prime 13 settimane di gravidanza?",
     "Ha sofferto la madre di stress emotivo importante tra le 25 e 27 settimane?",
     "Il parto è stato pre-termine o post-termine?",
     "È stata la nascita particolarmente difficoltosa o anomala in qualche senso? (parto indotto, troppo lungo, troppo veloce, forcipe, ventosa, cesareo)",
     "Era particolarmente piccolo/a per l'età gestazionale al momento del parto?",
     "C'era qualcosa di inusuale alla nascita? (problemi craniali, colorito bluastro, itterizia, crosta lattea, terapia intensiva)",
     "Durante le prime 13 settimane di vita ha avuto difficoltà di suzione, alimentazione o rigurgito?",
     "Durante i primi 6 mesi, è stato un bambino/a particolarmente tranquillo/a, anche troppo?",
     "Fra i 6 e i 18 mesi, era particolarmente agitato/a, dormiva poco e piangeva molto?",
     "Si dondolava così forte da muovere il lettino o il passeggino, o si colpiva la testa con oggetti solidi?",
     "Ha imparato a camminare troppo presto (prima dei 10 mesi) o in ritardo (dopo i 16 mesi)?",
     "Ha saltato le fasi di striscio e gattonamento (saltellava sul sedere, rotolava, si è alzato in piedi direttamente)?",
     "Ha imparato a parlare in ritardo (frasi di 3 parole dopo i 2 anni)?",
     "Nei primi 18 mesi ha avuto febbre molto alta e/o convulsioni?",
     "C'è stato qualche segno di eczema, asma o allergia? Reazione a un vaccino?",
     "Ha avuto difficoltà a imparare a vestirsi da solo/a?",
     "Ha continuato a succhiarsi il pollice fino ai 5 anni o oltre?",
     "Ha continuato a bagnare il letto (anche solo ogni tanto) sopra i 5 anni?",
     "Ha sofferto di mal d'auto?",
     "Nei primi due anni di scuola, ha avuto problemi a imparare a leggere o scrivere (anche in corsivo)?",
     "Ha fatto più fatica a leggere l'ora da un orologio analogico rispetto a quelli digitali?",
     "Ha avuto difficoltà a imparare ad andare in bicicletta con due ruote?",
     "Nei primi 8 anni di vita, ci sono state febbri molto alte, delirio o crisi convulsive?",
     "È stato/a un bambino/a con frequenti malattie alle alte vie respiratorie (otite, bronchite, sinusite)?",
     "Ha avuto difficoltà a imparare a prendere una palla al volo, fare capriole, salire la corda, saltare il \"cavallo\" o stare in equilibrio?",
     "Faceva fatica a stare fermo/a seduto/a (\"formiche nei pantaloni\") ed era ripreso/a spesso dagli insegnanti?",
     "Fa molti errori quando copia un testo da un libro?",
     "Quando scriveva a scuola, gli/le capitava di \"girare\" le lettere o saltare lettere/parole?"
    ]
   ],
   [
    "h3",
    "Seconda parte — Età adulta"
   ],
   [
    "item",
    [
     "Se c'è un rumore o movimento inaspettato, si spaventa in modo esagerato?",
     "Ha paura degli spazi aperti, attacchi di panico, ansia esagerata?",
     "Questi sintomi peggiorano in un luogo o momento specifico?",
     "Le capita di percepire il movimento di oggetti che in realtà sono fermi? (alberi, palazzi, ecc.)",
     "Le capita di vedere sfuocato o percepire altre alterazioni visive?",
     "Ha nausea frequentemente?",
     "Ha spesso nausea mentre è coricato/a sul letto?",
     "Considera di avere uno scarso senso dell'equilibrio?",
     "Pensa di essere molto scoordinato/a ogni tanto?",
     "Soffre o ha sofferto di emicrania?",
     "È molto sensibile alle luci brillanti? (es. luci delle discoteche)",
     "Direbbe di essere particolarmente sensibile ai suoni rispetto alle altre persone?",
     "Fa fatica con destra e sinistra quando deve dare indicazioni?",
     "Quando scrive qualcosa di lungo/complesso, le capita di iniziare a fare errori (ordine di lettere/parole, ortografia) che di solito non farebbe?",
     "Le capita, quando è molto stanco/a, di sapere cosa vuole dire ma non riuscire a parlare correttamente?",
     "Le capita, quando è molto stanco/a, di diventare goffo/a e scoordinato/a e colpirsi con oggetti?"
    ]
   ]
  ]
 ]
}
