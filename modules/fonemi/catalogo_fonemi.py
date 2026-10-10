# -*- coding: utf-8 -*-
"""
Catalogo PNEV - Facilitazioni tattili-cinestesiche per l'impostazione dei fonemi.
Materiale originale PNEV (Dott. Giuseppe Ferraioli - www.pnev.it).
Non riproduce il protocollo PROMPT(R), marchio del PROMPT Institute.
"""

LIVELLI = {
    1: ("Stabilità di base", "Postura e mandibola controllate"),
    2: ("Posizione", "Articolatore nel punto giusto, in silenzio"),
    3: ("Fonema isolato", "Produzione corretta con tutti gli appoggi"),
    4: ("Sillaba", "Coarticolazione con le vocali"),
    5: ("Parola", "Iniziale, poi intermedia e gruppi consonantici"),
    6: ("Frase e conversazione", "Automatizzazione con appoggi ridotti"),
}

APPOGGI = ["tatto", "specchio", "ascolto", "mano_aria", "vibrazione"]
APPOGGI_LABEL = {
    "tatto": "Input tattile",
    "specchio": "Specchio",
    "ascolto": "Modello uditivo",
    "mano_aria": "Aria sul dorso della mano",
    "vibrazione": "Vibrazione (gola/naso)",
}

# codice -> dati
FONEMI = {
    "p":  dict(simbolo="/p/", gruppo="Consonanti", punto_modo="bilabiale occlusiva sorda",
               facilitazione="Indice orizzontale sulle labbra chiuse, poi rilascio",
               appoggio="Sbuffo d'aria sul dorso della mano", vocale_favorevole="a"),
    "b":  dict(simbolo="/b/", gruppo="Consonanti", punto_modo="bilabiale occlusiva sonora",
               facilitazione="Indice orizzontale sulle labbra chiuse, poi rilascio",
               appoggio="Mano sulla gola per la vibrazione", vocale_favorevole="a"),
    "m":  dict(simbolo="/m/", gruppo="Consonanti", punto_modo="bilabiale nasale",
               facilitazione="Labbra chiuse con leggera pressione",
               appoggio="Dito sull'ala del naso per la vibrazione nasale", vocale_favorevole="a"),
    "f":  dict(simbolo="/f/", gruppo="Consonanti", punto_modo="labiodentale fricativa sorda",
               facilitazione="Dito sotto il labbro inferiore che lo accompagna verso gli incisivi superiori",
               appoggio="Flusso d'aria continuo sulla mano", vocale_favorevole="a"),
    "v":  dict(simbolo="/v/", gruppo="Consonanti", punto_modo="labiodentale fricativa sonora",
               facilitazione="Dito sotto il labbro inferiore che lo accompagna verso gli incisivi superiori",
               appoggio="Vibrazione alla gola", vocale_favorevole="a"),
    "t":  dict(simbolo="/t/", gruppo="Consonanti", punto_modo="alveolare occlusiva sorda",
               facilitazione="Spatola o dito sugli alveoli dietro gli incisivi superiori",
               appoggio="Sbuffo breve sulla mano", vocale_favorevole="a"),
    "d":  dict(simbolo="/d/", gruppo="Consonanti", punto_modo="alveolare occlusiva sonora",
               facilitazione="Spatola o dito sugli alveoli dietro gli incisivi superiori",
               appoggio="Vibrazione alla gola", vocale_favorevole="a"),
    "n":  dict(simbolo="/n/", gruppo="Consonanti", punto_modo="alveolare nasale",
               facilitazione="Come /t/", appoggio="Vibrazione nasale", vocale_favorevole="a"),
    "l":  dict(simbolo="/l/", gruppo="Consonanti", punto_modo="alveolare laterale",
               facilitazione="Apice sugli alveoli, aria ai lati",
               appoggio="Prolungare il suono", vocale_favorevole="a"),
    "r":  dict(simbolo="/r/", gruppo="Consonanti", punto_modo="vibrante alveolare",
               facilitazione="Da /d/ ripetuto rapido con mandibola stabile, poi 'dr' -> 'r'",
               appoggio="Soffio forte e breve sulla punta della lingua", vocale_favorevole="a"),
    "s":  dict(simbolo="/s/", gruppo="Consonanti", punto_modo="alveolare fricativa sorda",
               facilitazione="Labbra a sorriso, denti accostati; cannuccia sulla linea mediana della lingua",
               appoggio="Aria fredda e sottile sul dorso della mano", vocale_favorevole="i"),
    "z":  dict(simbolo="/z/", gruppo="Consonanti", punto_modo="alveolare fricativa sonora",
               facilitazione="Come /s/", appoggio="Vibrazione alla gola", vocale_favorevole="i"),
    "sc": dict(simbolo="/ʃ/", gruppo="Consonanti", punto_modo="postalveolare fricativa",
               facilitazione="Dita ai lati della bocca che spingono le labbra in avanti",
               appoggio="Aria più calda e larga della /s/", vocale_favorevole="i"),
    "c":  dict(simbolo="/tʃ/", gruppo="Consonanti", punto_modo="affricata postalveolare sorda",
               facilitazione="Sequenza /t/ + /ʃ/ fusa, prima lenta poi rapida",
               appoggio="Specchio per la protrusione", vocale_favorevole="i"),
    "g":  dict(simbolo="/dʒ/", gruppo="Consonanti", punto_modo="affricata postalveolare sonora",
               facilitazione="Sequenza /d/ + /ʃ/ sonora fusa",
               appoggio="Specchio per la protrusione; vibrazione alla gola", vocale_favorevole="i"),
    "k":  dict(simbolo="/k/", gruppo="Consonanti", punto_modo="velare occlusiva sorda",
               facilitazione="Spatola che tiene giù l'apice + leggera pressione sotto il mento verso l'alto e indietro",
               appoggio="Posizione supina facilitante", vocale_favorevole="o"),
    "gh": dict(simbolo="/g/", gruppo="Consonanti", punto_modo="velare occlusiva sonora",
               facilitazione="Come /k/", appoggio="Vibrazione alla gola", vocale_favorevole="o"),
    "gn": dict(simbolo="/ɲ/", gruppo="Consonanti", punto_modo="palatale nasale",
               facilitazione="Dorso della lingua contro il palato, apice in basso",
               appoggio="Vibrazione nasale", vocale_favorevole="a"),
    "gl": dict(simbolo="/ʎ/", gruppo="Consonanti", punto_modo="palatale laterale",
               facilitazione="Come /ɲ/ con aria ai lati", appoggio="Partire da /l/ + /i/",
               vocale_favorevole="i"),
    "va": dict(simbolo="/a/", gruppo="Vocali", punto_modo="vocale aperta",
               facilitazione="Dito sul mento che accompagna l'apertura ampia", appoggio="Specchio",
               vocale_favorevole="-"),
    "ve": dict(simbolo="/e/", gruppo="Vocali", punto_modo="vocale anteriore media",
               facilitazione="Apertura media, labbra leggermente stirate", appoggio="Specchio",
               vocale_favorevole="-"),
    "vi": dict(simbolo="/i/", gruppo="Vocali", punto_modo="vocale anteriore chiusa",
               facilitazione="Indici agli angoli delle labbra che stirano; mandibola quasi chiusa",
               appoggio="Specchio", vocale_favorevole="-"),
    "vo": dict(simbolo="/o/", gruppo="Vocali", punto_modo="vocale posteriore media",
               facilitazione="Pollice e indice che arrotondano le labbra; apertura media",
               appoggio="Specchio", vocale_favorevole="-"),
    "vu": dict(simbolo="/u/", gruppo="Vocali", punto_modo="vocale posteriore chiusa",
               facilitazione="Labbra arrotondate e protruse; mandibola quasi chiusa",
               appoggio="Specchio", vocale_favorevole="-"),
}

# Criterio di passaggio di livello (modificabile)
CRITERIO_PERC = 80          # % di produzioni corrette
CRITERIO_MIN_PROVE = 10     # prove minime per seduta
CRITERIO_SEDUTE = 2         # sedute consecutive che soddisfano il criterio

def etichetta(cod):
    f = FONEMI[cod]
    return f"{f['simbolo']}  {f['punto_modo']}"
