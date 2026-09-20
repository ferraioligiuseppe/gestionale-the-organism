# -*- coding: utf-8 -*-
"""Intestazione e chiusura standard per tutte le relazioni dello Studio.

Un unico punto da cui passano carta intestata, trafiletto sul Metodo PNEV e
presentazione dell'équipe multidisciplinare: così se cambia un recapito o un
professionista si modifica qui e si aggiorna in tutte le relazioni.
"""
from __future__ import annotations
import datetime

# ── Carta intestata ───────────────────────────────────────────────────
STUDIO_NOME = "STUDIO ASSOCIATO THE ORGANISM"
STUDIO_TITOLARE = "Dott. Giuseppe Ferraioli — Psicologo, Optometrista Comportamentale"
STUDIO_INDIRIZZO = "Via De Rosa 46, Pagani (SA) · Via Tino di Camaino 23, Napoli · Studio Della Ragione, Via Balsamo 19, Sant'Agnello (NA)"
STUDIO_CONTATTI = "Tel. 081 5152334 — 393 5171571"
STUDIO_EMAIL = "info@theorganism.it"
STUDIO_WEB = "www.pnev.it"

# ── Équipe multidisciplinare ──────────────────────────────────────────
EQUIPE = [
    "Dott. Giuseppe Ferraioli — Psicologo, Optometrista Comportamentale",
    "Dott.ssa Chiara Scarpa — Neuropsichiatra Infantile",
    "Logopedia e TNPEE",
    "Osteopatia",
    "Terapia miofunzionale",
]

TRAFILETTO_PNEV = (
    "Il Metodo PNEV (Psico-Neuro-Evolutivo Visivo) nasce dall'osservazione clinica "
    "che linguaggio, attenzione, postura e apprendimento non dipendono da un solo "
    "sistema, ma dall'integrazione fra più sistemi sensoriali e motori — uditivo, "
    "visivo, propriocettivo, vestibolare. Per questo la valutazione è multidisciplinare "
    "e il percorso terapeutico integra stimolazione uditiva (MAPS), stimolazione visiva, "
    "integrazione dei riflessi primitivi e posturali, lavoro miofunzionale e osteopatico, "
    "scelti e combinati in base a quanto emerge dalla valutazione."
)


def intestazione(titolo_documento: str, nome_paziente: str = "",
                 data_nascita: str = "", eta: str = "") -> str:
    """Blocco di apertura: carta intestata + titolo + dati del paziente."""
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    righe = [
        STUDIO_NOME,
        STUDIO_TITOLARE,
        f"{STUDIO_INDIRIZZO} · {STUDIO_CONTATTI}",
        f"{STUDIO_EMAIL} · {STUDIO_WEB}",
        "",
        "─" * 64,
        "",
        titolo_documento.upper(),
        "",
    ]
    if nome_paziente:
        riga_paz = f"Paziente: {nome_paziente}"
        if data_nascita:
            riga_paz += f"   ·   Data di nascita: {data_nascita}"
        if eta:
            riga_paz += f"   ·   Età: {eta}"
        righe.append(riga_paz)
    righe.append(f"Data della valutazione: {oggi}")
    righe.append("")
    righe.append("─" * 64)
    righe.append("")
    return "\n".join(righe)


def chiusura(includi_pnev: bool = True, includi_equipe: bool = True,
             includi_npi_interna: bool = False) -> str:
    """Blocco di chiusura: metodo PNEV, équipe, firma."""
    righe = ["", "─" * 64, ""]
    if includi_pnev:
        righe += ["IL METODO PNEV", "", TRAFILETTO_PNEV, ""]
    if includi_equipe:
        righe += ["L'ÉQUIPE MULTIDISCIPLINARE", ""]
        righe += [f"· {m}" for m in EQUIPE]
        righe += [""]
        righe += [
            "La presenza di più professionisti nello stesso studio permette di "
            "confrontare le osservazioni delle diverse aree e di costruire un percorso "
            "unico, senza che la famiglia debba ricomporre indicazioni raccolte in "
            "luoghi e tempi diversi.",
            "",
        ]
    if includi_npi_interna:
        righe += [
            "La valutazione neuropsichiatrica infantile e l'eventuale presa in carico "
            "possono avvenire direttamente presso il nostro studio, con la Dott.ssa "
            "Chiara Scarpa, garantendo continuità con il percorso già avviato. Resta "
            "naturalmente possibile rivolgersi al pediatra curante per accedere al "
            "servizio territoriale.",
            "",
        ]
    righe += [
        f"{STUDIO_TITOLARE}",
        STUDIO_NOME,
        f"{STUDIO_EMAIL} · {STUDIO_WEB}",
    ]
    return "\n".join(righe)


def premessa_metodo() -> str:
    """Inquadramento PNEV in apertura.

    In una relazione di screening chi legge — un genitore, un insegnante,
    a volte un collega — deve sapere dentro quale cornice sono stati letti
    quei numeri prima di incontrarli, non dopo.
    """
    return (
        "PREMESSA — L'INQUADRAMENTO\n\n"
        + TRAFILETTO_PNEV + "\n\n"
        "Per questo i risultati che seguono non vanno letti come prestazioni "
        "isolate: ogni dato è messo in relazione con gli altri sistemi, e il "
        "profilo che ne esce orienta il percorso più di quanto non faccia il "
        "singolo punteggio.\n\n"
        + "─" * 64 + "\n"
    )


def incornicia(corpo: str, titolo_documento: str, nome_paziente: str = "",
               data_nascita: str = "", eta: str = "",
               includi_npi_interna: bool = False,
               metodo_in_apertura: bool = False) -> str:
    """Avvolge un testo di relazione fra intestazione e chiusura.

    metodo_in_apertura: mette l'inquadramento PNEV prima del corpo (e non
    lo ripete in fondo). Utile negli screening, dove chi legge spesso non
    conosce il metodo.
    """
    return (intestazione(titolo_documento, nome_paziente, data_nascita, eta)
            + (premessa_metodo() + "\n" if metodo_in_apertura else "")
            + corpo.strip()
            + chiusura(includi_pnev=not metodo_in_apertura,
                       includi_npi_interna=includi_npi_interna))
