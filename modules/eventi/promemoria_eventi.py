# -*- coding: utf-8 -*-
"""
modules/eventi/promemoria_eventi.py

Orchestratore dei promemoria automatici pre-evento (48h e 24h).

Usato da:
- pages/cron_promemoria.py     → trigger automatico (GitHub Actions / cron-job.org)
- modules/eventi/ui_eventi.py  → invio manuale dal tab Azioni

L'invio EMAIL è automatico. Per WhatsApp questa logica prepara solo i testi
(la spedizione WhatsApp avviene a mano dall'utente, vedi genera_lista_whatsapp).
"""
from __future__ import annotations

import logging
from typing import Any

from .db_eventi import (
    eventi_con_promemoria_da_inviare,
    iscritti_senza_promemoria,
    marca_promemoria_inviato,
)
from .email_eventi import invia_promemoria_iscritto

logger = logging.getLogger(__name__)


def processa_promemoria_automatici(conn: Any, dry_run: bool = False) -> dict:
    """
    Funzione principale chiamata dal cron notturno.

    Trova tutti gli eventi che hanno promemoria da inviare ORA (finestre 48h/24h),
    invia le email agli iscritti che non li hanno ancora ricevuti, e li marca.

    Args:
        conn: connessione DB
        dry_run: se True, NON invia e NON marca, ritorna solo cosa farebbe

    Ritorna un report dict con il riepilogo.
    """
    report = {
        "eventi_processati": 0,
        "email_inviate": 0,
        "email_fallite": 0,
        "dettaglio": [],
        "errori": [],
    }

    try:
        eventi_da_fare = eventi_con_promemoria_da_inviare(conn)
    except Exception as e:
        report["errori"].append(f"Errore lettura eventi: {e}")
        logger.error(f"processa_promemoria: errore lettura eventi: {e}", exc_info=True)
        return report

    for item in eventi_da_fare:
        evento = item["evento"]
        tipi = item["tipi"]
        report["eventi_processati"] += 1

        for tipo in tipi:
            try:
                iscritti = iscritti_senza_promemoria(conn, evento["id"], tipo)
            except Exception as e:
                report["errori"].append(
                    f"Evento {evento['id']} tipo {tipo}: errore lettura iscritti: {e}"
                )
                continue

            for iscr in iscritti:
                voce = {
                    "evento": evento.get("titolo", ""),
                    "tipo": tipo,
                    "email": iscr.get("email", ""),
                    "nome": f"{iscr.get('nome','')} {iscr.get('cognome','')}".strip(),
                }

                if dry_run:
                    voce["stato"] = "DRY_RUN (non inviato)"
                    report["dettaglio"].append(voce)
                    continue

                try:
                    invia_promemoria_iscritto(evento, iscr, tipo)
                    marca_promemoria_inviato(conn, iscr["id"], tipo)
                    report["email_inviate"] += 1
                    voce["stato"] = "inviato"
                except Exception as e:
                    report["email_fallite"] += 1
                    voce["stato"] = f"ERRORE: {e}"
                    report["errori"].append(f"{iscr.get('email')}: {e}")

                report["dettaglio"].append(voce)

    return report


def genera_lista_whatsapp(evento: dict, iscritti: list[dict], tipo: str = "24h") -> list[dict]:
    """
    Prepara la lista dei messaggi WhatsApp pronti da inviare a mano.

    Ritorna una lista di dict: {nome, telefono, telefono_intl, messaggio, link_wa}
    dove link_wa è un link wa.me che apre WhatsApp con il messaggio precompilato.
    """
    from .email_eventi import _format_data_evento
    from urllib.parse import quote

    data_str = _format_data_evento(evento["data_ora"])
    titolo = evento.get("titolo", "")
    sede = evento.get("sede", "")

    risultati = []
    for iscr in iscritti:
        nome = iscr.get("nome", "").strip()
        tel = (iscr.get("telefono") or "").strip()

        if tipo == "48h":
            apertura = f"Ciao {nome}! Ti ricordo che tra 2 giorni ci sarà"
        else:
            apertura = f"Ciao {nome}! Ci vediamo domani per"

        messaggio = (
            f"{apertura} l'incontro di {titolo}. "
            f"\n\n📅 {data_str}"
        )
        if sede:
            messaggio += f"\n📍 {sede}"
        messaggio += (
            "\n\nTi aspettiamo! Se non puoi più venire avvisami così libero il posto. "
            "A presto 🌿"
        )

        # Normalizza telefono per link wa.me (rimuove spazi, +, trattini)
        tel_clean = "".join(c for c in tel if c.isdigit())
        # Se non ha prefisso internazionale, assume Italia (39)
        if tel_clean and not tel_clean.startswith("39") and len(tel_clean) <= 10:
            tel_intl = "39" + tel_clean
        else:
            tel_intl = tel_clean

        link_wa = ""
        if tel_intl:
            link_wa = f"https://wa.me/{tel_intl}?text={quote(messaggio)}"

        risultati.append({
            "nome": f"{nome} {iscr.get('cognome','')}".strip(),
            "telefono": tel or "—",
            "telefono_intl": tel_intl or "",
            "messaggio": messaggio,
            "link_wa": link_wa,
        })

    return risultati
