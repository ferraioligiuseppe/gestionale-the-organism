# -*- coding: utf-8 -*-
"""
modules/eventi/email_eventi.py

Helper invio email per il modulo eventi.

Funzioni:
- invia_conferma_iscritto(...)    → email con PDF allegato all'iscritto
- invia_notifica_studio(...)      → email di notifica allo studio (CLINIC_EMAIL)

Riusa la configurazione SMTP da st.secrets.smtp.* già configurata nel gestionale.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Optional
from zoneinfo import ZoneInfo

import streamlit as st

logger = logging.getLogger(__name__)

ROME_TZ = ZoneInfo("Europe/Rome")


# =============================================================================
# CONFIG
# =============================================================================

def _smtp_cfg() -> dict:
    cfg = st.secrets.get("smtp", {})
    missing = [k for k in ("HOST", "PORT", "USERNAME", "PASSWORD") if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            f"Configurazione SMTP incompleta. Mancano: {missing}. "
            f"Configurare [smtp] in secrets.toml"
        )
    return cfg


def _clinic_email() -> str:
    """Email dello studio per le notifiche."""
    return (
        st.secrets.get("privacy", {}).get("CLINIC_EMAIL")
        or st.secrets.get("smtp", {}).get("FROM")
        or st.secrets.get("smtp", {}).get("USERNAME")
        or ""
    )


def _from_address() -> str:
    cfg = _smtp_cfg()
    return cfg.get("FROM") or cfg.get("USERNAME")


# =============================================================================
# INVIO
# =============================================================================

def _send(msg: EmailMessage) -> None:
    """Spedisce il messaggio usando SMTP con TLS (compat con resto del gestionale)."""
    cfg = _smtp_cfg()
    host = cfg["HOST"]
    port = int(cfg["PORT"])
    use_tls = str(cfg.get("USE_TLS", "true")).lower() in ("1", "true", "yes", "y")

    if use_tls:
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port) as s:
            s.login(cfg["USERNAME"], cfg["PASSWORD"])
            s.send_message(msg)


# =============================================================================
# TEMPLATE
# =============================================================================

def _format_data_evento(dt: datetime) -> str:
    GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    MESI = [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
    ]
    if dt.tzinfo is not None:
        dt = dt.astimezone(ROME_TZ)
    g = GIORNI[dt.weekday()]
    return f"{g} {dt.day} {MESI[dt.month - 1]} {dt.year} alle ore {dt.strftime('%H:%M')}"


def _testo_conferma_iscritto(evento: dict, iscrizione: dict) -> str:
    """Testo plain-text dell'email di conferma all'iscritto."""
    stato = iscrizione.get("stato", "confermata")
    nome = iscrizione.get("nome", "").strip()
    data_str = _format_data_evento(evento["data_ora"])

    if stato == "confermata":
        intro = (
            f"Ciao {nome},\n\n"
            f"ti confermiamo la tua iscrizione all'evento:\n\n"
            f"  {evento.get('titolo', '')}\n"
            f"  📅 {data_str}\n"
        )
    elif stato == "lista_attesa":
        intro = (
            f"Ciao {nome},\n\n"
            f"abbiamo ricevuto la tua iscrizione all'evento:\n\n"
            f"  {evento.get('titolo', '')}\n"
            f"  📅 {data_str}\n\n"
            f"⚠️ Al momento i posti disponibili sono esauriti, quindi sei in LISTA D'ATTESA. "
            f"Ti contatteremo non appena si libera un posto.\n"
        )
    else:
        intro = (
            f"Ciao {nome},\n\n"
            f"la tua iscrizione all'evento '{evento.get('titolo', '')}' è stata registrata.\n"
        )

    if evento.get("sede"):
        intro += f"  📍 {evento['sede']}\n"
    if evento.get("conduttore"):
        intro += f"  👤 Conduttore: {evento['conduttore']}\n"
    if evento.get("prezzo") is not None and float(evento["prezzo"]) > 0:
        intro += f"  💶 Contributo: € {float(evento['prezzo']):.2f}\n"

    note = (
        "\n"
        "In allegato trovi il PDF della conferma con tutti i dettagli. "
        "Conservalo come ricevuta.\n\n"
        "Se non puoi più partecipare, ti chiediamo cortesemente di avvisarci rispondendo "
        "a questa email, così possiamo liberare il posto a chi è in lista d'attesa.\n\n"
        "A presto,\n"
        "Studio The Organism\n"
        "Via De Rosa 46, Pagani (SA)\n"
        "www.theorganism.com\n"
    )
    return intro + note


def _testo_notifica_studio(evento: dict, iscrizione: dict) -> str:
    """Testo plain-text per la notifica allo studio."""
    stato = iscrizione.get("stato", "confermata")
    return (
        f"Nuova iscrizione all'evento:\n\n"
        f"  Evento: {evento.get('titolo', '')}\n"
        f"  Data:   {_format_data_evento(evento['data_ora'])}\n"
        f"  Slug:   {evento.get('slug', '')}\n\n"
        f"Iscritto:\n"
        f"  Nome:     {iscrizione.get('cognome', '')} {iscrizione.get('nome', '')}\n"
        f"  Email:    {iscrizione.get('email', '')}\n"
        f"  Telefono: {iscrizione.get('telefono', '') or '—'}\n"
        f"  Stato:    {stato.upper()}\n"
        f"  ID:       #{iscrizione.get('id', '—')}\n\n"
        f"Note:\n  {iscrizione.get('note', '') or '—'}\n\n"
        f"Marketing OK: {'sì' if iscrizione.get('consenso_marketing') else 'no'}\n"
        f"IP: {iscrizione.get('ip_address', '—')}\n\n"
        f"Apri il gestionale → Marketing → Eventi e iscrizioni per la gestione completa."
    )


# =============================================================================
# API PUBBLICA
# =============================================================================

def invia_conferma_iscritto(
    evento: dict,
    iscrizione: dict,
    pdf_bytes: Optional[bytes] = None,
) -> None:
    """
    Invia email di conferma all'iscritto con PDF in allegato.

    Solleva eccezione se l'invio fallisce.
    """
    to_email = iscrizione.get("email")
    if not to_email:
        raise ValueError("Email dell'iscritto mancante")

    msg = EmailMessage()
    titolo_ev = evento.get("titolo", "Evento")
    stato = iscrizione.get("stato", "confermata")
    prefisso = "[Lista d'attesa] " if stato == "lista_attesa" else ""

    msg["Subject"] = f"{prefisso}Conferma iscrizione: {titolo_ev}"
    msg["From"] = _from_address()
    msg["To"] = to_email
    # Bcc allo studio per archiviazione
    clinic = _clinic_email()
    if clinic and clinic != to_email:
        msg["Bcc"] = clinic

    msg.set_content(_testo_conferma_iscritto(evento, iscrizione))

    if pdf_bytes:
        filename = f"conferma_iscrizione_{evento.get('slug', 'evento')}.pdf"
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )

    _send(msg)
    logger.info(
        f"Email conferma inviata a {to_email} per evento "
        f"{evento.get('id')} (iscrizione {iscrizione.get('id')})"
    )


def invia_notifica_studio(evento: dict, iscrizione: dict) -> None:
    """
    Invia notifica di nuova iscrizione allo studio (CLINIC_EMAIL).
    Silenziosa: logga eventuali errori ma non li solleva (l'iscrizione resta valida).
    """
    to_email = _clinic_email()
    if not to_email:
        logger.warning("CLINIC_EMAIL non configurata: notifica studio saltata")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = f"🆕 Nuova iscrizione: {evento.get('titolo', 'Evento')}"
        msg["From"] = _from_address()
        msg["To"] = to_email
        # Reply-to → email dell'iscritto, così si può rispondere direttamente
        if iscrizione.get("email"):
            msg["Reply-To"] = iscrizione["email"]
        msg.set_content(_testo_notifica_studio(evento, iscrizione))
        _send(msg)
        logger.info(f"Notifica studio inviata a {to_email}")
    except Exception as e:
        logger.error(f"Notifica studio FALLITA: {e}", exc_info=True)
