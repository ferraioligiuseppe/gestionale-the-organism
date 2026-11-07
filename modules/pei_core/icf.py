"""
pei_core.icf — ICF-CY (OMS 2007) per PF, Profilo Dinamico Funzionale e PEI.

Contiene:
  - un catalogo ridotto di codici di secondo livello utili a scuola
    (b funzioni, s strutture, d attività e partecipazione, e fattori ambientali);
  - i qualificatori (0-4, 8, 9; barriere/facilitatori per i codici e);
  - il raccordo codici -> dimensioni del PEI (A-D, D.I. 182/2020);
  - la bozza automatica delle sezioni 4, 6 e 11 del PEI a partire dal profilo ICF.

Le denominazioni sono abbreviate: per la codifica ufficiale fare riferimento
al testo OMS (ed. it. Erickson). Per ampliare il catalogo basta aggiungere
righe a CATALOGO: (codice, denominazione, dimensione PEI o None).
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Qualificatori
# --------------------------------------------------------------------------
QUALIFICATORI = [
    "0 - nessuna difficoltà (0-4%)",
    "1 - difficoltà lieve (5-24%)",
    "2 - difficoltà media (25-49%)",
    "3 - difficoltà grave (50-95%)",
    "4 - difficoltà completa (96-100%)",
    "8 - non specificato",
    "9 - non applicabile",
]

QUALIFICATORI_AMBIENTE = [
    "+4 facilitatore completo",
    "+3 facilitatore sostanziale",
    "+2 facilitatore medio",
    "+1 facilitatore lieve",
    "0 nessun effetto",
    ".1 barriera lieve",
    ".2 barriera media",
    ".3 barriera grave",
    ".4 barriera completa",
    ".8 barriera non specificata",
    "+8 facilitatore non specificato",
]

COMPONENTI = {
    "b": "Funzioni corporee",
    "s": "Strutture corporee",
    "d": "Attività e partecipazione",
    "e": "Fattori ambientali",
}

# dimensioni del PEI (stesse chiavi di schema.DIMENSIONI_PEI)
R, C, A, G = "relazione", "comunicazione", "autonomia", "cognitiva"

# --------------------------------------------------------------------------
# Catalogo (secondo livello; [CY] = codice introdotto o ampliato dall'ICF-CY)
# --------------------------------------------------------------------------
CATALOGO = [
    # ---- b: funzioni mentali
    ("b110", "Funzioni della coscienza", G),
    ("b114", "Funzioni dell'orientamento", A),
    ("b117", "Funzioni intellettive", G),
    ("b122", "Funzioni psicosociali globali", R),
    ("b125", "Funzioni e disposizioni intrapersonali [CY]", R),
    ("b126", "Funzioni del temperamento e della personalità", R),
    ("b130", "Funzioni dell'energia e delle pulsioni", G),
    ("b134", "Funzioni del sonno", A),
    ("b140", "Funzioni dell'attenzione", G),
    ("b144", "Funzioni della memoria", G),
    ("b147", "Funzioni psicomotorie", A),
    ("b152", "Funzioni emozionali", R),
    ("b156", "Funzioni percettive", G),
    ("b160", "Funzioni del pensiero", G),
    ("b163", "Funzioni cognitive di base [CY]", G),
    ("b164", "Funzioni cognitive di livello superiore (esecutive)", G),
    ("b167", "Funzioni mentali del linguaggio", C),
    ("b172", "Funzioni di calcolo", G),
    ("b176", "Funzione mentale di sequenza dei movimenti complessi", A),
    ("b180", "Funzioni dell'esperienza del sé e del tempo", G),
    # ---- b: sensoriali, voce, movimento
    ("b210", "Funzioni della vista", A),
    ("b215", "Funzioni delle strutture adiacenti all'occhio (motilità oculare)", A),
    ("b230", "Funzioni uditive", C),
    ("b235", "Funzioni vestibolari", A),
    ("b260", "Funzione propriocettiva", A),
    ("b265", "Funzione del tatto", A),
    ("b270", "Funzioni sensoriali correlate a temperatura e altri stimoli", A),
    ("b280", "Sensazione di dolore", A),
    ("b310", "Funzioni della voce", C),
    ("b320", "Funzioni dell'articolazione", C),
    ("b330", "Funzioni della fluidità e del ritmo dell'eloquio", C),
    ("b510", "Funzioni di ingestione (masticazione, deglutizione)", A),
    ("b525", "Funzioni di defecazione", A),
    ("b620", "Funzioni urinarie", A),
    ("b710", "Funzioni della mobilità delle articolazioni", A),
    ("b730", "Funzioni della forza muscolare", A),
    ("b735", "Funzioni del tono muscolare", A),
    ("b750", "Funzioni del riflesso motorio", A),
    ("b755", "Funzioni di reazione di movimento involontario", A),
    ("b760", "Funzioni di controllo del movimento volontario", A),
    ("b765", "Funzioni del movimento involontario", A),
    ("b770", "Funzioni del pattern dell'andatura", A),
    # ---- s: strutture
    ("s110", "Struttura del cervello", None),
    ("s120", "Midollo spinale e strutture correlate", None),
    ("s220", "Struttura del bulbo oculare", None),
    ("s250", "Struttura dell'orecchio medio", None),
    ("s260", "Struttura dell'orecchio interno", None),
    ("s320", "Struttura della bocca", None),
    ("s730", "Struttura dell'arto superiore", None),
    ("s750", "Struttura dell'arto inferiore", None),
    # ---- d1: apprendimento e applicazione delle conoscenze
    ("d110", "Guardare", G),
    ("d115", "Ascoltare", G),
    ("d120", "Altre percezioni sensoriali intenzionali", G),
    ("d130", "Copiare", G),
    ("d131", "Imparare attraverso le azioni con gli oggetti [CY]", G),
    ("d132", "Acquisire informazioni [CY]", G),
    ("d133", "Acquisire il linguaggio [CY]", C),
    ("d134", "Acquisire un linguaggio aggiuntivo [CY]", C),
    ("d135", "Ripetere", G),
    ("d137", "Acquisire concetti [CY]", G),
    ("d140", "Imparare a leggere", G),
    ("d145", "Imparare a scrivere", G),
    ("d150", "Imparare a calcolare", G),
    ("d155", "Acquisizione di abilità", G),
    ("d160", "Focalizzare l'attenzione", G),
    ("d161", "Dirigere l'attenzione [CY]", G),
    ("d163", "Pensare", G),
    ("d166", "Leggere", G),
    ("d170", "Scrivere", G),
    ("d172", "Calcolare", G),
    ("d175", "Risoluzione di problemi", G),
    ("d177", "Prendere decisioni", G),
    # ---- d2: compiti e richieste generali
    ("d210", "Intraprendere un compito singolo", G),
    ("d220", "Intraprendere compiti articolati", G),
    ("d230", "Eseguire la routine quotidiana", A),
    ("d240", "Gestire la tensione e altre richieste psicologiche", R),
    ("d250", "Controllare il proprio comportamento [CY]", R),
    # ---- d3: comunicazione
    ("d310", "Comunicare - ricevere - messaggi verbali", C),
    ("d315", "Comunicare - ricevere - messaggi non verbali", C),
    ("d320", "Comunicare - ricevere - messaggi nel linguaggio dei segni", C),
    ("d325", "Comunicare - ricevere - messaggi scritti", C),
    ("d330", "Parlare", C),
    ("d331", "Pre-linguaggio (vocalizzi, lallazione) [CY]", C),
    ("d335", "Produrre messaggi non verbali", C),
    ("d340", "Produrre messaggi nel linguaggio dei segni", C),
    ("d345", "Scrivere messaggi", C),
    ("d350", "Conversazione", C),
    ("d355", "Discussione", C),
    ("d360", "Utilizzo di strumenti e tecniche di comunicazione (CAA)", C),
    # ---- d4: mobilità
    ("d410", "Cambiare la posizione corporea di base", A),
    ("d415", "Mantenere una posizione corporea", A),
    ("d430", "Sollevare e trasportare oggetti", A),
    ("d440", "Uso fine della mano", A),
    ("d445", "Uso della mano e del braccio", A),
    ("d450", "Camminare", A),
    ("d455", "Spostarsi", A),
    ("d460", "Spostarsi in diverse collocazioni", A),
    ("d465", "Spostarsi usando apparecchiature/ausili", A),
    ("d470", "Usare un mezzo di trasporto", A),
    # ---- d5: cura della propria persona
    ("d510", "Lavarsi", A),
    ("d520", "Prendersi cura di singole parti del corpo", A),
    ("d530", "Bisogni corporali", A),
    ("d540", "Vestirsi", A),
    ("d550", "Mangiare", A),
    ("d560", "Bere", A),
    ("d570", "Prendersi cura della propria salute", A),
    ("d571", "Badare alla propria sicurezza [CY]", A),
    # ---- d6 / d8: vita domestica, aree di vita principali
    ("d620", "Procurarsi beni e servizi", A),
    ("d810", "Istruzione informale", G),
    ("d815", "Istruzione prescolastica", G),
    ("d820", "Istruzione scolastica", G),
    ("d825", "Formazione professionale", G),
    ("d830", "Istruzione superiore", G),
    ("d835", "Vita scolastica e attività correlate [CY]", G),
    ("d840", "Apprendistato (preparazione al lavoro) - PCTO", A),
    ("d845", "Acquisire, conservare e lasciare un lavoro", A),
    ("d860", "Transazioni economiche semplici", A),
    ("d880", "Coinvolgimento nel gioco [CY]", R),
    # ---- d7 / d9: relazioni, vita sociale
    ("d710", "Interazioni interpersonali semplici", R),
    ("d720", "Interazioni interpersonali complesse", R),
    ("d730", "Entrare in relazione con estranei", R),
    ("d740", "Relazioni formali (es. con i docenti)", R),
    ("d750", "Relazioni sociali informali (es. con i compagni)", R),
    ("d760", "Relazioni familiari", R),
    ("d910", "Vita nella comunità", R),
    ("d920", "Ricreazione e tempo libero", R),
    # ---- e: fattori ambientali
    ("e110", "Prodotti o sostanze per il consumo personale (farmaci, alimenti)", None),
    ("e115", "Prodotti e tecnologia per la vita quotidiana", None),
    ("e120", "Prodotti e tecnologia per mobilità e trasporto", None),
    ("e125", "Prodotti e tecnologia per la comunicazione", None),
    ("e130", "Prodotti e tecnologia per l'istruzione (strumenti compensativi)", None),
    ("e140", "Prodotti e tecnologia per cultura, ricreazione e sport", None),
    ("e150", "Edifici per uso pubblico (accessibilità della scuola)", None),
    ("e155", "Edifici per uso privato", None),
    ("e240", "Luce", None),
    ("e250", "Suono (rumore ambientale)", None),
    ("e310", "Famiglia ristretta", None),
    ("e315", "Famiglia allargata", None),
    ("e320", "Amici", None),
    ("e325", "Conoscenti, compagni, vicini e membri della comunità", None),
    ("e330", "Persone in posizione di autorità (docenti)", None),
    ("e340", "Persone che forniscono aiuto o assistenza", None),
    ("e355", "Operatori sanitari", None),
    ("e360", "Altri operatori (educatori, assistenti)", None),
    ("e410", "Atteggiamenti dei membri della famiglia ristretta", None),
    ("e420", "Atteggiamenti degli amici", None),
    ("e425", "Atteggiamenti di conoscenti e compagni", None),
    ("e430", "Atteggiamenti delle persone in posizione di autorità (docenti)", None),
    ("e440", "Atteggiamenti di chi fornisce aiuto o assistenza", None),
    ("e450", "Atteggiamenti degli operatori sanitari", None),
    ("e460", "Atteggiamenti della società", None),
    ("e465", "Norme sociali, costumi e ideologie", None),
    ("e540", "Servizi, sistemi e politiche di trasporto", None),
    ("e575", "Servizi, sistemi e politiche di sostegno sociale", None),
    ("e580", "Servizi, sistemi e politiche sanitarie", None),
    ("e585", "Servizi, sistemi e politiche dell'istruzione e della formazione", None),
    ("e590", "Servizi, sistemi e politiche del lavoro", None),
]

_PER_CODICE = {c: (t, d) for c, t, d in CATALOGO}


def etichetta(codice: str) -> str:
    """'d166' -> 'd166 Leggere' (la stringa salvata nel documento)."""
    t = _PER_CODICE.get(codice)
    return f"{codice} {t[0]}" if t else codice


def opzioni(componenti: str) -> list[str]:
    """Voci per il menu a tendina, filtrate per componente (es. 'bsd' o 'e')."""
    return [f"{c} {t}" for c, t, _ in CATALOGO if c[0] in componenti]


def codice_di(voce: str) -> str:
    return str(voce or "").split(" ", 1)[0].strip().lower()


def dimensione_di(voce: str) -> str | None:
    t = _PER_CODICE.get(codice_di(voce))
    return t[1] if t else None


def livello(qual: str) -> int | None:
    """'2 - difficoltà media' -> 2; 8 e 9 -> None."""
    q = str(qual or "").strip()
    if q[:1].isdigit() and q[0] in "01234":
        return int(q[0])
    return None


# --------------------------------------------------------------------------
# Colonne delle due tabelle (usate da schema.py come campi «tabella»)
# --------------------------------------------------------------------------
COLONNE_FUNZIONAMENTO = [
    {"key": "codice", "label": "Codice ICF-CY (b, s, d)", "tipo": "select", "opzioni": opzioni("bsd")},
    {"key": "performance", "label": "Qualificatore (per i codici d: performance)", "tipo": "select",
     "opzioni": QUALIFICATORI},
    {"key": "capacita", "label": "Capacità (solo codici d)", "tipo": "select", "opzioni": QUALIFICATORI},
    {"key": "note", "label": "Osservazioni / fonte", "tipo": "text"},
]

COLONNE_CONTESTO = [
    {"key": "codice", "label": "Fattore ambientale (e)", "tipo": "select", "opzioni": opzioni("e")},
    {"key": "valore", "label": "Barriera / facilitatore", "tipo": "select",
     "opzioni": QUALIFICATORI_AMBIENTE},
    {"key": "note", "label": "In che modo, in quale contesto", "tipo": "text"},
]

CAMPO_FUNZIONAMENTO = "icf_funzionamento"
CAMPO_CONTESTO = "icf_contesto"


# --------------------------------------------------------------------------
# Controlli
# --------------------------------------------------------------------------
def controlla_icf(contenuto: dict) -> list[str]:
    avvisi = []
    visti = set()
    for r in contenuto.get(CAMPO_FUNZIONAMENTO) or []:
        cod = codice_di(r.get("codice"))
        if not cod:
            continue
        if cod in visti:
            avvisi.append(f"ICF: il codice {cod} compare più volte.")
        visti.add(cod)
        if not r.get("performance"):
            avvisi.append(f"ICF: {cod} senza qualificatore.")
        if r.get("capacita") and not cod.startswith("d"):
            avvisi.append(f"ICF: la capacità si usa solo per i codici d ({cod}).")
    for r in contenuto.get(CAMPO_CONTESTO) or []:
        cod = codice_di(r.get("codice"))
        if cod and not r.get("valore"):
            avvisi.append(f"ICF: {cod} senza indicazione barriera/facilitatore.")
    return avvisi


# --------------------------------------------------------------------------
# Bozze per il PEI
# --------------------------------------------------------------------------
_MARCA = "BOZZA DA ICF-CY — da rivedere con l'osservazione in classe"


def _riga_funz(r: dict) -> str:
    cod = codice_di(r.get("codice"))
    testo = etichetta(cod)
    q = r.get("performance") or ""
    pezzi = [f"{'performance' if cod.startswith('d') else 'qualificatore'} {q.split(' (')[0]}"] if q else []
    if r.get("capacita") and cod.startswith("d"):
        pezzi.append(f"capacità {r['capacita'].split(' (')[0]}")
    s = f"• {testo}" + (f" — {'; '.join(pezzi)}" if pezzi else "")
    if r.get("note"):
        s += f". {r['note']}"
    return s


def bozza_sezione4(contenuto: dict) -> dict[str, str]:
    """{dimensione: testo} per le osservazioni della sezione 4."""
    per_dim: dict[str, list[str]] = {}
    for r in contenuto.get(CAMPO_FUNZIONAMENTO) or []:
        dim = dimensione_di(r.get("codice"))
        if dim:
            per_dim.setdefault(dim, []).append(_riga_funz(r))
    return {d: _MARCA + "\n" + "\n".join(v) for d, v in per_dim.items()}


def bozza_sezione6(contenuto: dict) -> tuple[str, str]:
    """(barriere, facilitatori) dai codici e."""
    barr, fac = [], []
    for r in contenuto.get(CAMPO_CONTESTO) or []:
        cod, val = codice_di(r.get("codice")), str(r.get("valore") or "")
        if not cod or not val:
            continue
        riga = f"• {etichetta(cod)} ({val})" + (f": {r['note']}" if r.get("note") else "")
        if val.startswith("."):
            barr.append(riga)
        elif val.startswith("+"):
            fac.append(riga)
    return ("\n".join([_MARCA] + barr) if barr else "",
            "\n".join([_MARCA] + fac) if fac else "")


ENTITA = ["assente", "lieve", "media", "elevata", "molto elevata"]
DOMINI_ALLEGATO_C = [("cognitiva", "Apprendimento"), ("comunicazione", "Comunicazione"),
                     ("relazione", "Relazioni e socializzazione"),
                     ("autonomia", "Autonomia personale e sociale")]


def proposta_allegato_c(contenuto: dict) -> list[dict]:
    """Entità delle difficoltà per dominio: il qualificatore d più alto (performance)
    di ogni dimensione. È solo una proposta: la decide il GLO."""
    massimo: dict[str, int] = {}
    for r in contenuto.get(CAMPO_FUNZIONAMENTO) or []:
        cod = codice_di(r.get("codice"))
        lv = livello(r.get("performance"))
        dim = dimensione_di(cod)
        if cod.startswith("d") and dim and lv is not None:
            massimo[dim] = max(massimo.get(dim, 0), lv)
    return [{"dominio": nome, "entita": ENTITA[massimo[k]]}
            for k, nome in DOMINI_ALLEGATO_C if k in massimo]


def riporta_nel_pei(pei_contenuto: dict, sovrascrivi: bool = False) -> list[str]:
    """Scrive le bozze nelle sezioni 4, 6 e 11 del PEI. Non tocca i campi già
    compilati a meno di sovrascrivi=True. Restituisce cosa ha fatto."""
    fatto = []

    def metti(chiave, valore, nome):
        if not valore:
            return
        att = pei_contenuto.get(chiave)
        if isinstance(att, str) and att.startswith("BOZZA") and not sovrascrivi:
            if _MARCA in att:
                fatto.append(f"{nome}: bozza ICF già presente.")
            else:                     # c'è solo la bozza automatica dal PDF: si accoda
                pei_contenuto[chiave] = att.rstrip() + "\n\n" + valore
                fatto.append(f"{nome}: bozza ICF aggiunta sotto la bozza dal PDF.")
            return
        if att and not sovrascrivi:
            fatto.append(f"{nome}: già compilato, lasciato com'è.")
            return
        pei_contenuto[chiave] = valore
        fatto.append(f"{nome}: bozza inserita.")

    for dim, testo in bozza_sezione4(pei_contenuto).items():
        metti(f"oss_{dim}", testo, f"Sezione 4 ({dim})")
    barr, fac = bozza_sezione6(pei_contenuto)
    metti("barriere", barr, "Sezione 6 barriere")
    metti("facilitatori", fac, "Sezione 6 facilitatori")
    metti("debito_funzionamento", proposta_allegato_c(pei_contenuto), "Sezione 11 entità delle difficoltà")
    return fatto or ["Nessun dato ICF da riportare."]


def aggiungi_righe(contenuto: dict, campo: str, nuove: list[dict]) -> tuple[int, int]:
    """Aggiunge righe ICF senza toccare i codici già presenti.
    Restituisce (aggiunte, saltate perché il codice c'era già)."""
    righe = list(contenuto.get(campo) or [])
    presenti = {codice_di(r.get("codice")) for r in righe}
    agg = salt = 0
    for r in nuove:
        cod = codice_di(r.get("codice"))
        if not cod:
            continue
        if cod in presenti:
            salt += 1
            continue
        righe.append(dict(r))
        presenti.add(cod)
        agg += 1
    contenuto[campo] = righe
    return agg, salt


def qualificatore_da_percentuale(perc: float) -> str:
    """Percentuale di difficoltà -> qualificatore ICF (stesse soglie dell'OMS)."""
    p = float(perc or 0)
    i = 0 if p < 5 else 1 if p < 25 else 2 if p < 50 else 3 if p < 96 else 4
    return QUALIFICATORI[i]
