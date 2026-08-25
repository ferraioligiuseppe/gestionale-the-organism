# -*- coding: utf-8 -*-
"""
modules/soglie_cliniche.py

Il criterio clinico dei giochi PNEV — centri, bande di tolleranza, fasce
d'età, mappa metrica→dominio e regola del segnale ripetuto.

PERCHÉ STA QUI E NON NEI GIOCHI
Fino alla versione precedente questa tabella viveva dentro pnev-lead.js, cioè
in un file pubblico scaricabile da chiunque: chi copiava il gioco si portava
via anche il ragionamento. Ora i giochi raccolgono soltanto i numeri grezzi
(quanti bersagli, quanti errori, che tempi) e li passano al gestionale; il
giudizio — quale area è in difficoltà, di quanto, se il quadro è specifico o
diffuso — viene fatto qui, su un file che non lascia mai il server.

I giochi mantengono soltanto una soglia rozza e volutamente generica, che
serve solo a decidere se vale la pena proporre l'approfondimento. Non è il
criterio clinico e non lo ricostruisce.

⚠️ Centri e bande sono riferimenti interni di screening, non norme validate
su popolazione: servono a decidere se approfondire, non a fare diagnosi.
"""

DOMINI = {
    "attenzione":   ("Attenzione e costanza",
                     "Tenuta attentiva e variabilità delle risposte."),
    "inibizione":   ("Controllo degli impulsi",
                     "Difficoltà a frenare la risposta già avviata."),
    "occhiomano":   ("Coordinazione occhio-mano",
                     "Prassie e controllo del gesto guidato dalla vista: "
                     "da leggere insieme a integrazione sensoriale e riflessi."),
    "oculomotor":   ("Controllo dei movimenti oculari",
                     "Inseguimenti e stabilità dello sguardo: da confermare "
                     "con DEM e valutazione oculomotoria."),
    "memoria":      ("Memoria di lavoro",
                     "Tenuta e manipolazione dell'informazione a breve termine."),
    "flessibilita": ("Flessibilità nel cambiare regola",
                     "Costo del passaggio da una regola all'altra (set-shifting)."),
    "linguaggio":   ("Linguaggio e lettura",
                     "Accesso fonologico e rapidità di riconoscimento."),
    "bilaterale":   ("Integrazione destra/sinistra",
                     "Coordinazione fra i due lati del corpo e schema corporeo: "
                     "area centrale per i riflessi primitivi."),
    "sensomotoria": ("Integrazione sensoriale",
                     "Errori che si ripetono o peggiorano su più giochi diversi, "
                     "a prescindere dal dominio cognitivo specifico: possibile deficit "
                     "di integrazione sensoriale nella pianificazione del gesto."),
}

# Fasce d'età: i centri sono tarati sulla fascia media (7-9 anni).
# Per i più piccoli il centro si abbassa e la banda si allarga.
FASCE = [
    (4,  6,  "4-6 anni",  0.78, 1.45),
    (7,  9,  "7-9 anni",  1.00, 1.00),
    (10, 99, "10+ anni",  1.10, 0.85),
]

# trova = parole chiave nell'etichetta della metrica
# verso = "alto" (più alto è meglio) | "basso" (più basso è meglio)
# pct   = se True, preferisce la percentuale quando presente
REGOLE = {
    "gonogo": [
        (["risposte corrette"],    "alto",  85,   15, "attenzione",   False),
        (["errori di inibizione"], "basso", 10,   10, "inibizione",   True),
        (["omissioni"],            "basso", 10,   10, "attenzione",   True),
        (["variabilit"],           "basso", 120,  80, "attenzione",   False),
        (["centrati"],             "alto",  70,   20, "occhiomano",   False),
        (["errore medio"],         "basso", 30,   25, "occhiomano",   False),
    ],
    "talpa": [
        (["talpe acchiappate"],    "alto",  85,   15, "attenzione",   False),
        (["errori di inibizione"], "basso", 10,   10, "inibizione",   True),
        (["omissioni"],            "basso", 12,   12, "attenzione",   True),
        (["variabilit"],           "basso", 130,  90, "attenzione",   False),
        (["tocchi a vuoto"],       "basso", 3,    4,  "occhiomano",   False),
    ],
    "palloncini": [
        (["palloncini presi"],     "alto",  85,   15, "attenzione",   False),
        (["errori"],               "basso", 10,   10, "inibizione",   True),
        (["sfuggiti"],             "basso", 12,   12, "attenzione",   True),
        (["tocchi a vuoto"],       "basso", 3,    4,  "occhiomano",   False),
    ],
    "seguipuntino": [
        (["sul bersaglio"],        "alto",  70,   20, "oculomotor",   False),
        (["errore medio"],         "basso", 35,   25, "oculomotor",   False),
        (["agganci persi"],        "basso", 3,    4,  "oculomotor",   False),
    ],
    "labirinto": [
        (["uscite dal percorso"],  "basso", 3,    4,  "occhiomano",   False),
    ],
    "coppie": [
        (["efficienza"],           "alto",  60,   20, "memoria",      False),
        (["errori"],               "basso", 6,    6,  "memoria",      False),
    ],
    "sequenza": [
        (["sequenza più lunga", "sequenza piu lunga", "span"],
                                   "alto",  5,    2,  "memoria",      False),
    ],
    "smista": [
        (["giuste"],               "alto",  85,   15, "flessibilita", False),
        (["cambio di regola"],     "basso", 1,    2,  "flessibilita", False),
        (["errori"],               "basso", 4,    4,  "flessibilita", False),
    ],
    "parolelampo": [
        (["parole lette"],         "alto",  80,   20, "linguaggio",   False),
        (["tempo di scelta"],      "basso", 1800, 900, "linguaggio",  False),
    ],
    "sillabe": [
        (["sillabe giuste"],       "alto",  85,   15, "linguaggio",   False),
    ],
    "rime": [
        (["rime giuste"],          "alto",  85,   15, "linguaggio",   False),
    ],
    "slaptap": [
        (["giuste"],               "alto",  85,   15, "bilaterale",   False),
        (["errori"],               "basso", 3,    4,  "bilaterale",   False),
        (["tempo di risposta"],    "basso", 1500, 800, "bilaterale",  False),
    ],
}

# Coppie di domini che, cadendo insieme, indicano convergenza e non rumore
VICINI = [
    ("occhiomano", "oculomotor"), ("occhiomano", "bilaterale"),
    ("oculomotor", "bilaterale"), ("linguaggio", "uditivo"),
    ("attenzione", "inibizione"), ("memoria", "flessibilita"),
    ("sensomotoria", "occhiomano"), ("sensomotoria", "bilaterale"),
]

MIN_GIOCHI_DIVERSI = 2     # giochi diversi dello stesso dominio → segnale
MIN_PARTITE_STESSO = 3     # se il dominio ha un solo gioco, servono più prove
DEV_PERIFERIA      = 1.0   # oltre quante bande si considera periferia
DEV_MARCATA        = 2.0   # scarto marcato: vale come due prove
MAX_DOMINI_SPARSI  = 3     # da qui è quadro globale, non debolezza specifica
SCARTA_PRIMA       = True  # la prima partita di ogni gioco è familiarizzazione


def _fascia(eta):
    if not eta:
        return FASCE[1]
    for f in FASCE:
        if f[0] <= eta <= f[1]:
            return f
    return FASCE[1]


def _numero(testo, preferisci_pct=False):
    """Legge un numero da un valore testuale ('12 (30%)', '2/6', '±120 ms')."""
    import re
    if testo is None:
        return None
    s = str(testo).replace("\u00a0", " ")
    if preferisci_pct:
        m = re.search(r"(-?[\d.,]+)\s*%", s)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except Exception:
                pass
    m = re.search(r"(-?\d+)\s*/\s*(\d+)", s)
    if m:
        return float(m.group(1))
    m = re.search(r"-?\d+(?:[.,]\d+)?", s.replace("±", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except Exception:
        return None


# Ogni gioco ha almeno una metrica "errori" generica: qui viene riletta una
# seconda volta, sempre, per il dominio trasversale sensomotorio — non
# sostituisce il giudizio specifico del gioco (es. inibizione, memoria),
# lo affianca. Centro/banda volutamente larghi: serve a cogliere una deriva
# che si ripete su più giochi, non a segnalare un singolo brutto risultato.
_ERRORE_GENERICO = (
    ["errori", "errore medio", "tocchi a vuoto", "uscite dal percorso",
     "agganci persi", "errori di inibizione"],
    "basso", 10, 10, True,
)


def valuta_partita(slug, metriche, eta=None):
    """metriche: lista di dict {etichetta, valore, sotto}.
    Ritorna {dominio: scostamento} per quella partita."""
    regole = REGOLE.get(slug, [])
    _, _, _, k_centro, k_banda = _fascia(eta)
    out = {}
    for trova, verso, centro, banda, dom, pct in regole:
        trovata = None
        for m in metriche:
            et = str(m.get("etichetta", "")).lower()
            if any(k in et for k in trova):
                trovata = m
                break
        if not trovata:
            continue
        val = _numero(trovata.get("valore"), pct)
        if val is None and pct:
            val = _numero(trovata.get("sotto"), True)
        if val is None:
            continue
        c = centro * k_centro if verso == "alto" else centro / k_centro
        b = banda * k_banda
        if not b:
            continue
        dev = (c - val) / b if verso == "alto" else (val - c) / b
        if dom not in out or dev > out[dom]:
            out[dom] = round(dev, 2)

    trova, verso, centro, banda, pct = _ERRORE_GENERICO
    for m in metriche:
        et = str(m.get("etichetta", "")).lower()
        if not any(k in et for k in trova):
            continue
        val = _numero(m.get("valore"), pct)
        if val is None and pct:
            val = _numero(m.get("sotto"), True)
        if val is None:
            continue
        c = centro / k_centro
        b = banda * k_banda
        if not b:
            continue
        dev = (val - c) / b
        if "sensomotoria" not in out or dev > out["sensomotoria"]:
            out["sensomotoria"] = round(dev, 2)
        break
    return out


def _vicini(a, b):
    return (a, b) in VICINI or (b, a) in VICINI


def calcola_segnale(storico):
    """storico: lista di partite {g: slug, n: numero partita, eta, m: [metriche]}.
    Ritorna il segnale (specifico / convergenza / globale) o None."""
    peso, somma, n_prove, giochi = {}, {}, {}, {}

    for i, p in enumerate(storico):
        if SCARTA_PRIMA and (p.get("n") == 1 or (p.get("n") is None and i == 0)):
            continue
        dom = valuta_partita(p.get("g", ""), p.get("m", []), p.get("eta"))
        for d, v in dom.items():
            if v < DEV_PERIFERIA:
                continue
            peso[d] = peso.get(d, 0) + (2 if v >= DEV_MARCATA else 1)
            somma[d] = somma.get(d, 0) + v
            n_prove[d] = n_prove.get(d, 0) + 1
            giochi.setdefault(d, set()).add(p.get("g"))

    sospetti = []
    for d, pz in peso.items():
        n_g = len(giochi[d])
        if not (n_g >= MIN_GIOCHI_DIVERSI or pz >= MIN_PARTITE_STESSO):
            continue
        sospetti.append({"dominio": d, "n": n_prove[d], "nGiochi": n_g,
                         "peso": pz, "dev": round(somma[d] / n_prove[d], 2)})
    if not sospetti:
        return None
    sospetti.sort(key=lambda s: -s["dev"])

    if len(sospetti) >= MAX_DOMINI_SPARSI:
        return {"tipo": "globale", "dominio": None, "nDomini": len(sospetti),
                "domini": [s["dominio"] for s in sospetti],
                "n": sospetti[0]["n"], "nGiochi": sospetti[0]["nGiochi"],
                "dev": sospetti[0]["dev"]}

    if len(sospetti) == 2 and _vicini(sospetti[0]["dominio"], sospetti[1]["dominio"]):
        return {"tipo": "convergenza", "dominio": sospetti[0]["dominio"],
                "dominio2": sospetti[1]["dominio"], "nDomini": 2,
                "n": sospetti[0]["n"] + sospetti[1]["n"],
                "nGiochi": sospetti[0]["nGiochi"] + sospetti[1]["nGiochi"],
                "dev": max(sospetti[0]["dev"], sospetti[1]["dev"])}

    s0 = sospetti[0]
    return {"tipo": "specifico", "dominio": s0["dominio"],
            "nDomini": len(sospetti), "n": s0["n"],
            "nGiochi": s0["nGiochi"], "dev": s0["dev"]}


def decodifica_payload(raw):
    """Decodifica il pacchetto grezzo inviato dai giochi (base64 di JSON)."""
    import base64
    import json
    if not raw:
        return []
    try:
        pad = "=" * (-len(raw) % 4)
        testo = base64.urlsafe_b64decode(raw + pad).decode("utf-8")
        dati = json.loads(testo)
        return dati if isinstance(dati, list) else []
    except Exception:
        return []
