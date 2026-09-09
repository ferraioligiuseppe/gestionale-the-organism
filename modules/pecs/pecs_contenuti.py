# -*- coding: utf-8 -*-
"""
modules/pecs/pecs_contenuti.py
------------------------------
Contenuti clinici del protocollo PECS (Bondy & Frost) e motore dei criteri
di passaggio di fase. Nessuna dipendenza da database o da Streamlit:
questo file e' puro contenuto + logica, cosi' e' testabile e riutilizzabile
(schede a video, PDF, validazioni lato db).

Studio The Organism - Dott. Giuseppe Ferraioli
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ordine delle fasi
# ---------------------------------------------------------------------------

ORDINE_FASI: List[str] = ["I", "II", "IIIA", "IIIB", "IV", "V", "VI"]

ETICHETTE_ESITO = {
    "autonoma": "Autonoma",
    "prompt": "Con prompt",
    "errore": "Errore / nessuna risposta",
}


def fase_successiva(fase: str) -> Optional[str]:
    """Restituisce la fase successiva nell'ordine, o None se e' l'ultima."""
    if fase not in ORDINE_FASI:
        return None
    i = ORDINE_FASI.index(fase)
    return ORDINE_FASI[i + 1] if i + 1 < len(ORDINE_FASI) else None


# ---------------------------------------------------------------------------
# Descrizione dei campi specifici di ogni fase
# ---------------------------------------------------------------------------

@dataclass
class CampoParametro:
    """Un campo dati che l'operatore compila per quella fase."""
    chiave: str
    etichetta: str
    tipo: str                      # "int" | "float" | "bool" | "testo" | "scelta"
    opzioni: Optional[List[str]] = None
    default: Any = None
    aiuto: str = ""


@dataclass
class Fase:
    codice: str
    nome: str
    obiettivo: str
    operatori: str
    materiali: List[str]
    procedura: List[str]
    prompt: List[str]
    errori: List[str]
    criterio_testo: str
    campi: List[CampoParametro] = field(default_factory=list)
    fedelta: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Checklist di fedelta' comuni a tutte le fasi
# ---------------------------------------------------------------------------

FEDELTA_COMUNE = [
    "Item verificati come motivanti oggi, non per abitudine",
    "Nessun prompt verbale ne' istruzione da parte del partner comunicativo",
    "Consegna del rinforzatore entro mezzo secondo dallo scambio",
    "Etichettamento verbale senza richiesta di ripetere la parola",
    "Almeno 30 opportunita' distribuite nella giornata",
]


# ---------------------------------------------------------------------------
# Le sei fasi
# ---------------------------------------------------------------------------

FASI: Dict[str, Fase] = {}

FASI["I"] = Fase(
    codice="I",
    nome="Lo scambio fisico",
    obiettivo=(
        "Alla vista di un item desiderato, l'utente prende l'immagine, tende il "
        "braccio verso il partner e la lascia nella sua mano. Nessun prerequisito "
        "richiesto: non servono contatto oculare, imitazione o attenzione condivisa."
    ),
    operatori=(
        "Due operatori. Partner comunicativo di fronte (mostra l'item, attende, "
        "riceve, consegna). Prompter fisico dietro o di lato (guida la mano, "
        "non parla mai, non cerca il contatto oculare)."
    ),
    materiali=[
        "5-10 item rinforzanti verificati, fuori portata dell'utente",
        "Una sola immagine plastificata ~5x5 cm, con velcro",
        "Quaderno di comunicazione con copertina",
    ],
    procedura=[
        "Il partner rende l'item desiderabile senza chiedere nulla (tentazione).",
        "1. L'utente PRENDE l'immagine.",
        "2. TENDE il braccio verso il partner.",
        "3. RILASCIA l'immagine nella mano del partner.",
        "Consegna immediata dell'item con etichettamento verbale.",
    ],
    prompt=[
        "A - guida fisica completa sui tre passi",
        "B - guida su presa e braccio, rilascio libero",
        "C - guida solo sulla presa, braccio e rilascio liberi",
        "D - nessuna guida, sola attesa",
        "La mano aperta del partner e' essa stessa un prompt: va sfumata.",
    ],
    errori=[
        "Prompt verbali: 'Cosa vuoi?', 'Prendi la figura', 'Dammi'",
        "Piu' immagini disponibili contemporaneamente (la discriminazione e' in Fase III)",
        "Un solo operatore: si perde il controllo del prompt",
        "Item scelti dall'adulto e non verificati",
        "PECS praticato solo in seduta, senza generalizzazione",
    ],
    criterio_testo=(
        "Scambio completo e autonomo, senza alcun prompt fisico o gestuale "
        "(mano aperta compresa), in almeno l'80% delle opportunita', con 2 partner "
        "diversi, 2 contesti diversi e almeno 3 item differenti."
    ),
    campi=[
        CampoParametro("livello_prompt", "Livello di prompt raggiunto", "scelta",
                       opzioni=["A", "B", "C", "D"], default="A",
                       aiuto="D = nessuna guida fisica"),
        CampoParametro("mano_aperta_sfumata", "Mano aperta del partner sfumata", "bool",
                       default=False),
    ],
    fedelta=[
        "Erano presenti due operatori con ruoli distinti",
        "Sul tavolo c'era una sola immagine per volta",
        "Il prompter non ha parlato e non ha cercato il contatto oculare",
        "La guida fisica e' stata sfumata dall'ultimo passo verso il primo",
    ],
)

FASI["II"] = Fase(
    codice="II",
    nome="Distanza e persistenza",
    obiettivo=(
        "L'utente va al quaderno di comunicazione, stacca l'immagine, raggiunge "
        "il partner, ne richiama l'attenzione e gli mette l'immagine in mano, "
        "anche a distanza e in presenza di ostacoli."
    ),
    operatori=(
        "Partner comunicativo (si allontana progressivamente) e prompter fisico "
        "nelle prime prove, poi si sfuma fino al partner unico."
    ),
    materiali=[
        "Quaderno di comunicazione con UNA immagine sulla copertina",
        "Item rinforzanti disponibili in ambienti diversi",
    ],
    procedura=[
        "Si aumenta la distanza UTENTE - PARTNER (passi progressivi).",
        "Si aumenta la distanza UTENTE - QUADERNO.",
        "Si allena la PERSISTENZA: partner girato, distratto, occupato.",
        "Si generalizza a stanze, persone e momenti diversi della giornata.",
    ],
    prompt=[
        "Prompter fisico solo per avviare lo spostamento, poi sfumato.",
        "Mai richiamare verbalmente l'utente ('vieni qui', 'guarda').",
    ],
    errori=[
        "Restare seduti al tavolo: la distanza non aumenta mai",
        "Il partner che va incontro all'utente",
        "Aumentare le due distanze contemporaneamente",
    ],
    criterio_testo=(
        "L'utente si sposta autonomamente di almeno 3 metri verso il quaderno e "
        "di almeno 3 metri verso il partner, con persistenza di fronte a partner "
        "distratto, nell'80% delle opportunita', con 2 partner e 2 contesti."
    ),
    campi=[
        CampoParametro("distanza_partner_cm", "Distanza utente-partner (cm)", "int",
                       default=100),
        CampoParametro("distanza_quaderno_cm", "Distanza utente-quaderno (cm)", "int",
                       default=100),
        CampoParametro("persistenza_ok", "Persistenza con partner distratto superata",
                       "bool", default=False),
    ],
    fedelta=[
        "Il partner non si e' avvicinato all'utente",
        "Nessun richiamo verbale per attirare l'utente",
        "Le due distanze sono state aumentate una per volta",
    ],
)

FASI["IIIA"] = Fase(
    codice="IIIA",
    nome="Discriminazione: preferito vs. distrattore",
    obiettivo=(
        "L'utente discrimina l'immagine dell'item desiderato da quella di un "
        "distrattore non preferito o irrilevante."
    ),
    operatori="Un partner comunicativo. Il prompter interviene solo nella correzione.",
    materiali=[
        "Immagine dell'item preferito + immagine di un distrattore",
        "Entrambi gli oggetti reali disponibili sul tavolo",
    ],
    procedura=[
        "Due immagini sulla copertina del quaderno, posizioni ruotate a ogni prova.",
        "Se la risposta e' corretta: consegna immediata dell'item + lode.",
        "Se sbagliata: PROCEDURA DI CORREZIONE A 4 PASSI - "
        "1) Mostra l'immagine corretta, 2) Sollecita (prompt), "
        "3) Cambia (attivita' ponte: batti le mani, tocca il naso), 4) Ripeti.",
        "Verifica di corrispondenza: se porge l'immagine del distrattore, offrire "
        "quell'oggetto e osservare la reazione di rifiuto.",
    ],
    prompt=[
        "Nella correzione si usa il prompt gestuale/fisico, mai quello verbale.",
        "Rinforzo differenziale: entusiasmo maggiore per la risposta autonoma.",
    ],
    errori=[
        "Non ruotare le posizioni: l'utente impara la posizione, non l'immagine",
        "Saltare il passo 'Cambia': senza attivita' ponte la correzione non tiene",
        "Usare un distrattore che l'utente in realta' gradisce",
    ],
    criterio_testo=(
        "80% di risposte corrette su 3 sessioni consecutive, con posizioni "
        "ruotate a ogni prova e verifica di corrispondenza superata."
    ),
    campi=[
        CampoParametro("rotazione_posizioni", "Posizioni ruotate a ogni prova", "bool",
                       default=True),
        CampoParametro("correzioni_4_passi", "N. correzioni a 4 passi effettuate", "int",
                       default=0),
        CampoParametro("verifica_corrispondenza", "Verifica di corrispondenza superata",
                       "bool", default=False),
    ],
    fedelta=[
        "Posizioni delle immagini ruotate a ogni prova",
        "Procedura di correzione a 4 passi applicata per intero",
        "Rinforzo differenziale rispettato",
    ],
)

FASI["IIIB"] = Fase(
    codice="IIIB",
    nome="Discriminazione fra piu' item preferiti",
    obiettivo=(
        "L'utente discrimina fra due o piu' immagini di item entrambi desiderati "
        "e chiede effettivamente cio' che vuole in quel momento."
    ),
    operatori="Un partner comunicativo.",
    materiali=[
        "Almeno 5 immagini di item preferiti nel quaderno",
        "Quaderno organizzato (pagine, categorie)",
    ],
    procedura=[
        "Due immagini di item entrambi graditi, posizioni ruotate.",
        "PROVA DI CORRISPONDENZA: dopo lo scambio si offrono gli oggetti e si "
        "verifica che l'utente prenda quello corrispondente all'immagine data.",
        "Si aumenta progressivamente il numero di immagini disponibili.",
        "Si struttura il quaderno per categorie (cibo, gioco, attivita').",
    ],
    prompt=[
        "Correzione a 4 passi come in Fase IIIA.",
        "Nessun prompt verbale.",
    ],
    errori=[
        "Fermarsi a due immagini e non ampliare il vocabolario",
        "Non fare mai la prova di corrispondenza: si scambia senza intenzione",
    ],
    criterio_testo=(
        "80% di scelte corrette con almeno 5 immagini disponibili, prova di "
        "corrispondenza superata, su 3 sessioni consecutive."
    ),
    campi=[
        CampoParametro("n_immagini_disponibili", "N. immagini disponibili nel quaderno",
                       "int", default=2),
        CampoParametro("verifica_corrispondenza", "Prova di corrispondenza superata",
                       "bool", default=False),
    ],
    fedelta=[
        "Prova di corrispondenza eseguita almeno una volta",
        "Numero di immagini disponibili aumentato rispetto alla scorsa sessione",
        "Quaderno organizzato e accessibile all'utente",
    ],
)

FASI["IV"] = Fase(
    codice="IV",
    nome="Struttura della frase",
    obiettivo=(
        "L'utente costruisce sulla striscia-frase 'Io voglio' + immagine dell'item "
        "e consegna l'intera striscia al partner."
    ),
    operatori="Un partner comunicativo; prompter fisico nelle prime prove.",
    materiali=[
        "Striscia-frase staccabile sulla copertina del quaderno",
        "Simbolo 'Io voglio' fisso a sinistra",
        "20 o piu' immagini nel quaderno",
    ],
    procedura=[
        "Backward chaining: prima si insegna ad aggiungere l'immagine dell'item "
        "alla striscia dove 'Io voglio' e' gia' posizionato.",
        "Poi si insegna a posizionare anche 'Io voglio'.",
        "Il partner gira la striscia verso l'utente e la legge indicando i simboli.",
        "LETTURA RITARDATA: dopo 'Io voglio...' si attende 3-5 secondi prima di "
        "nominare l'item, creando l'opportunita' di vocalizzazione. La vocalizzazione "
        "non e' mai richiesta ne' obbligatoria.",
        "Dopo la Fase IV si introducono gli ATTRIBUTI (colore, dimensione, quantita', "
        "posizione) allungando la striscia a 3 o piu' simboli.",
    ],
    prompt=[
        "Prompt fisico sulla costruzione della striscia, sfumato all'indietro.",
        "Nessun sollecito verbale a parlare.",
    ],
    errori=[
        "Pretendere la vocalizzazione come condizione per consegnare l'item",
        "Leggere la striscia troppo in fretta, senza il delay",
        "Non staccare mai la striscia: si perde la struttura della frase",
    ],
    criterio_testo=(
        "L'utente costruisce e consegna autonomamente la striscia completa "
        "nell'80% delle opportunita', con almeno 20 immagini nel quaderno e "
        "2 partner diversi."
    ),
    campi=[
        CampoParametro("n_immagini_quaderno", "N. immagini nel quaderno", "int",
                       default=20),
        CampoParametro("striscia_completa", "Striscia completa costruita autonomamente",
                       "bool", default=False),
        CampoParametro("lettura_ritardata_sec", "Delay della lettura ritardata (sec)",
                       "float", default=3.0),
        CampoParametro("vocalizzazioni", "N. vocalizzazioni spontanee osservate", "int",
                       default=0),
        CampoParametro("attributi_introdotti", "Attributi introdotti (colore/dimensione/n.)",
                       "bool", default=False),
    ],
    fedelta=[
        "La striscia e' stata staccata e consegnata per intero",
        "Lettura ritardata applicata con delay di almeno 3 secondi",
        "Nessuna vocalizzazione richiesta come condizione",
    ],
)

FASI["V"] = Fase(
    codice="V",
    nome="Rispondere a 'Cosa vuoi?'",
    obiettivo=(
        "L'utente risponde alla domanda 'Cosa vuoi?' costruendo la frase, "
        "mantenendo al tempo stesso la richiesta spontanea."
    ),
    operatori="Un partner comunicativo.",
    materiali=["Quaderno con striscia-frase e vocabolario ampio"],
    procedura=[
        "PROMPT RITARDATO COSTANTE: si pone la domanda indicando "
        "contemporaneamente il simbolo 'Io voglio' (delay 0 secondi).",
        "Si aumenta progressivamente il ritardo dell'indicazione: 1, 2, 3, 4 secondi.",
        "Si alternano prove su domanda e opportunita' di richiesta spontanea, per "
        "non sostituire l'iniziativa con la risposta.",
    ],
    prompt=[
        "Il prompt e' l'indicazione del simbolo 'Io voglio', mai la parola.",
        "Se compaiono errori, si torna al delay precedente.",
    ],
    errori=[
        "Fare solo prove su domanda: l'utente smette di chiedere spontaneamente",
        "Aumentare il delay troppo in fretta",
    ],
    criterio_testo=(
        "80% di risposte corrette alla domanda con delay di almeno 4 secondi, "
        "mantenendo richieste spontanee in ogni sessione."
    ),
    campi=[
        CampoParametro("delay_sec", "Delay del prompt ritardato (sec)", "float",
                       default=0.0),
        CampoParametro("n_risposte_domanda", "N. risposte corrette su domanda", "int",
                       default=0),
        CampoParametro("n_richieste_spontanee", "N. richieste spontanee nella sessione",
                       "int", default=0),
    ],
    fedelta=[
        "Alternate prove su domanda e opportunita' spontanee",
        "Delay aumentato solo dopo stabilita' del livello precedente",
        "Il prompt e' stato gestuale, non verbale",
    ],
)

FASI["VI"] = Fase(
    codice="VI",
    nome="Commentare",
    obiettivo=(
        "L'utente commenta l'ambiente rispondendo a domande ('Cosa vedi?', "
        "'Cosa senti?', 'Cosa hai?') e, progressivamente, in modo spontaneo."
    ),
    operatori="Un partner comunicativo.",
    materiali=[
        "Nuovi simboli starter: 'Vedo', 'Sento', 'Ho', 'E' un...'",
        "Oggetti e situazioni interessanti ma non necessariamente desiderati",
    ],
    procedura=[
        "Si introduce un solo starter per volta, con prompt ritardato come in Fase V.",
        "Si sfuma la domanda per arrivare al commento spontaneo.",
        "RINFORZO SOCIALE, non l'oggetto: il commento non serve a ottenere l'item. "
        "Confondere richiesta e commento e' l'errore centrale di questa fase.",
        "Si mantengono attive richieste (Fasi IV-V) e commenti in parallelo.",
    ],
    prompt=[
        "Indicazione del simbolo starter, con delay crescente.",
        "Piccoli rinforzatori tangibili possono accompagnare, ma non sostituire, "
        "il rinforzo sociale.",
    ],
    errori=[
        "Consegnare l'oggetto commentato: si insegna di nuovo la richiesta",
        "Introdurre piu' starter insieme",
        "Abbandonare le richieste per lavorare solo sui commenti",
    ],
    criterio_testo=(
        "L'utente risponde a diverse domande di commento e produce commenti "
        "spontanei in modo stabile (indicativamente almeno 5 per sessione su "
        "3 sessioni, con almeno 2 starter diversi)."
    ),
    campi=[
        CampoParametro("n_commenti_domanda", "N. commenti su domanda", "int", default=0),
        CampoParametro("n_commenti_spontanei", "N. commenti spontanei", "int", default=0),
        CampoParametro("starter_usati", "Starter usati (separati da virgola)", "testo",
                       default=""),
    ],
    fedelta=[
        "Il commento e' stato rinforzato socialmente, non con l'oggetto",
        "Un solo starter nuovo per volta",
        "Richieste (Fasi IV-V) mantenute attive in parallelo",
    ],
)


def get_fase(codice: str) -> Fase:
    if codice not in FASI:
        raise KeyError("Fase PECS sconosciuta: %r" % codice)
    return FASI[codice]


def etichetta_fase(codice: str) -> str:
    f = FASI.get(codice)
    return "Fase %s - %s" % (codice, f.nome) if f else "Fase %s" % codice


# ---------------------------------------------------------------------------
# Motore dei criteri di passaggio
# ---------------------------------------------------------------------------

SOGLIA_PERCENTUALE = 0.80
SESSIONI_CONSECUTIVE = 3


@dataclass
class Requisito:
    etichetta: str
    soddisfatto: bool
    valore: str = ""


@dataclass
class EsitoCriterio:
    fase: str
    soddisfatto: bool
    requisiti: List[Requisito]
    sessioni_valutate: int

    @property
    def mancanti(self) -> List[Requisito]:
        return [r for r in self.requisiti if not r.soddisfatto]


def _perc(sessione: Dict[str, Any]) -> float:
    tot = sessione.get("n_opportunita") or 0
    if not tot:
        return 0.0
    return (sessione.get("n_autonome") or 0) / float(tot)


def _par(sessione: Dict[str, Any], chiave: str, default=None):
    parametri = sessione.get("parametri") or {}
    return parametri.get(chiave, default)


def _distinti(sessioni: List[Dict[str, Any]], chiave: str) -> set:
    valori = set()
    for s in sessioni:
        v = s.get(chiave)
        if isinstance(v, (list, tuple, set)):
            valori.update(x for x in v if x)
        elif v:
            valori.add(v)
    return valori


def _req_percentuale(sessioni: List[Dict[str, Any]]) -> Requisito:
    ok = bool(sessioni) and all(_perc(s) >= SOGLIA_PERCENTUALE for s in sessioni)
    valori = ", ".join("%.0f%%" % (_perc(s) * 100) for s in sessioni) or "nessuna sessione"
    return Requisito(
        "Almeno l'80%% di risposte autonome su %d sessioni consecutive" % SESSIONI_CONSECUTIVE,
        ok, valori,
    )


def _req_partner(sessioni, minimo=2) -> Requisito:
    p = _distinti(sessioni, "partner")
    return Requisito("Almeno %d partner diversi" % minimo, len(p) >= minimo,
                     ", ".join(sorted(p)) or "-")


def _req_contesti(sessioni, minimo=2) -> Requisito:
    c = _distinti(sessioni, "contesto")
    return Requisito("Almeno %d contesti diversi" % minimo, len(c) >= minimo,
                     ", ".join(sorted(c)) or "-")


def _req_item(sessioni, minimo=3) -> Requisito:
    i = _distinti(sessioni, "item_usati")
    return Requisito("Almeno %d item differenti" % minimo, len(i) >= minimo,
                     ", ".join(sorted(i)) or "-")


def _criterio_I(sessioni):
    ultima = sessioni[0] if sessioni else {}
    req = [
        _req_percentuale(sessioni),
        _req_partner(sessioni),
        _req_contesti(sessioni),
        _req_item(sessioni),
        Requisito("Livello di prompt D (nessuna guida fisica)",
                  _par(ultima, "livello_prompt") == "D",
                  str(_par(ultima, "livello_prompt") or "-")),
        Requisito("Mano aperta del partner sfumata",
                  bool(_par(ultima, "mano_aperta_sfumata")),
                  "si" if _par(ultima, "mano_aperta_sfumata") else "no"),
    ]
    return req


def _criterio_II(sessioni):
    ok_dist = [s for s in sessioni
               if (_par(s, "distanza_partner_cm") or 0) >= 300
               and (_par(s, "distanza_quaderno_cm") or 0) >= 300]
    persistenza = [s for s in sessioni if _par(s, "persistenza_ok")]
    return [
        _req_percentuale(sessioni),
        Requisito("Almeno 3 metri sia dal partner sia dal quaderno (>=2 sessioni)",
                  len(ok_dist) >= 2,
                  "; ".join("%s/%s cm" % (_par(s, "distanza_partner_cm"),
                                          _par(s, "distanza_quaderno_cm"))
                            for s in sessioni) or "-"),
        Requisito("Persistenza con partner distratto superata (>=2 sessioni)",
                  len(persistenza) >= 2, "%d sessioni" % len(persistenza)),
        _req_partner(sessioni),
        _req_contesti(sessioni),
    ]


def _criterio_IIIA(sessioni):
    return [
        _req_percentuale(sessioni),
        Requisito("Posizioni ruotate in tutte le sessioni",
                  bool(sessioni) and all(_par(s, "rotazione_posizioni") for s in sessioni),
                  "-"),
        Requisito("Verifica di corrispondenza superata",
                  any(_par(s, "verifica_corrispondenza") for s in sessioni), "-"),
        _req_partner(sessioni),
    ]


def _criterio_IIIB(sessioni):
    n_img = max([(_par(s, "n_immagini_disponibili") or 0) for s in sessioni] or [0])
    return [
        _req_percentuale(sessioni),
        Requisito("Almeno 5 immagini disponibili nel quaderno", n_img >= 5,
                  "max %d" % n_img),
        Requisito("Prova di corrispondenza superata",
                  any(_par(s, "verifica_corrispondenza") for s in sessioni), "-"),
        _req_partner(sessioni),
    ]


def _criterio_IV(sessioni):
    n_img = max([(_par(s, "n_immagini_quaderno") or 0) for s in sessioni] or [0])
    return [
        _req_percentuale(sessioni),
        Requisito("Striscia completa costruita autonomamente in tutte le sessioni",
                  bool(sessioni) and all(_par(s, "striscia_completa") for s in sessioni),
                  "-"),
        Requisito("Almeno 20 immagini nel quaderno", n_img >= 20, "max %d" % n_img),
        _req_partner(sessioni),
    ]


def _criterio_V(sessioni):
    delay = max([(_par(s, "delay_sec") or 0) for s in sessioni] or [0])
    spontanee_ok = bool(sessioni) and all(
        (_par(s, "n_richieste_spontanee") or 0) > 0 for s in sessioni)
    return [
        _req_percentuale(sessioni),
        Requisito("Delay del prompt di almeno 4 secondi", delay >= 4,
                  "max %.1f s" % delay),
        Requisito("Richieste spontanee mantenute in ogni sessione", spontanee_ok,
                  ", ".join(str(_par(s, "n_richieste_spontanee") or 0) for s in sessioni)),
        _req_partner(sessioni),
    ]


def _criterio_VI(sessioni):
    spontanei_ok = bool(sessioni) and all(
        (_par(s, "n_commenti_spontanei") or 0) >= 5 for s in sessioni)
    starter = set()
    for s in sessioni:
        raw = _par(s, "starter_usati") or ""
        starter.update(x.strip() for x in str(raw).split(",") if x.strip())
    return [
        Requisito("Almeno 5 commenti spontanei per sessione", spontanei_ok,
                  ", ".join(str(_par(s, "n_commenti_spontanei") or 0) for s in sessioni)),
        Requisito("Almeno 2 starter diversi utilizzati", len(starter) >= 2,
                  ", ".join(sorted(starter)) or "-"),
        _req_partner(sessioni),
        _req_contesti(sessioni),
    ]


_MOTORI: Dict[str, Callable[[List[Dict[str, Any]]], List[Requisito]]] = {
    "I": _criterio_I,
    "II": _criterio_II,
    "IIIA": _criterio_IIIA,
    "IIIB": _criterio_IIIB,
    "IV": _criterio_IV,
    "V": _criterio_V,
    "VI": _criterio_VI,
}


def valuta_criterio(fase: str, sessioni: List[Dict[str, Any]]) -> EsitoCriterio:
    """
    Valuta il criterio di passaggio di una fase.

    `sessioni` = elenco delle sessioni di QUELLA fase, ordinate dalla piu'
    recente alla piu' vecchia. Vengono considerate solo le ultime
    SESSIONI_CONSECUTIVE.
    """
    motore = _MOTORI.get(fase)
    if motore is None:
        return EsitoCriterio(fase, False, [Requisito("Fase non riconosciuta", False)], 0)

    finestra = [s for s in sessioni][:SESSIONI_CONSECUTIVE]
    requisiti = [Requisito("Almeno %d sessioni registrate in questa fase"
                           % SESSIONI_CONSECUTIVE,
                           len(finestra) >= SESSIONI_CONSECUTIVE,
                           "%d registrate" % len(sessioni))]
    requisiti += motore(finestra)
    soddisfatto = all(r.soddisfatto for r in requisiti)
    return EsitoCriterio(fase, soddisfatto, requisiti, len(finestra))
