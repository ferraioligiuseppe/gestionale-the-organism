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

def _config_email() -> dict:
    """Configurazione di invio, accettando ENTRAMBE le sezioni di secrets.

    Il gestionale ne ha due, nate in momenti diversi: [gmail] EMAIL +
    APP_PASSWORD (usata da email_otp, dai questionari e dai lead del sito)
    e [smtp] HOST/PORT/USERNAME/PASSWORD (usata qui e in app_core).

    Finche' qui si leggeva solo [smtp], chi aveva configurato solo [gmail]
    vedeva partire le conferme scritte a mano dal gestionale — che passano
    da email_otp — e non quelle della pagina pubblica di iscrizione, che
    passano di qui. Da fuori sembrava che le email arrivassero "per certi
    eventi si' e per altri no": in realta' dipendeva da quale strada era
    stata usata per iscrivere.

    Ritorna: host, port, ssl_diretto, mittente, username, password.
    """
    smtp = st.secrets.get("smtp", {})
    if smtp.get("HOST") and smtp.get("USERNAME") and smtp.get("PASSWORD"):
        porta = int(smtp.get("PORT") or 587)
        usa_tls = str(smtp.get("USE_TLS", "true")).lower() in ("1", "true", "yes", "y")
        return {"host": smtp["HOST"], "port": porta, "ssl_diretto": not usa_tls,
                "from": smtp.get("FROM") or smtp["USERNAME"],
                "username": smtp["USERNAME"], "password": smtp["PASSWORD"]}

    gmail = st.secrets.get("gmail", {})
    if gmail.get("EMAIL") and gmail.get("APP_PASSWORD"):
        return {"host": "smtp.gmail.com", "port": 465, "ssl_diretto": True,
                "from": gmail["EMAIL"], "username": gmail["EMAIL"],
                "password": gmail["APP_PASSWORD"]}

    raise RuntimeError(
        "Nessuna configurazione email nei Secrets: serve [smtp] HOST + PORT + "
        "USERNAME + PASSWORD oppure [gmail] EMAIL + APP_PASSWORD."
    )


def _smtp_cfg() -> dict:
    """Compatibilita' con i chiamanti storici che si aspettano il dict [smtp]."""
    c = _config_email()
    return {"HOST": c["host"], "PORT": c["port"], "USERNAME": c["username"],
            "PASSWORD": c["password"], "FROM": c["from"],
            "USE_TLS": "false" if c["ssl_diretto"] else "true"}


def _clinic_email() -> str:
    """Email dello studio per le notifiche."""
    diretta = st.secrets.get("privacy", {}).get("CLINIC_EMAIL")
    if diretta:
        return diretta
    # Ripiego sul mittente configurato, quale che sia la sezione usata:
    # prima si guardava solo [smtp] e con la sola [gmail] la notifica
    # allo studio veniva saltata in silenzio.
    try:
        return _config_email()["from"]
    except Exception:
        return ""


def _from_address() -> str:
    return _config_email()["from"]


# =============================================================================
# INVIO
# =============================================================================

def _send(msg: EmailMessage) -> None:
    """Spedisce il messaggio con la configurazione disponibile.

    ssl_diretto = porta 465 (Gmail), altrimenti STARTTLS sulla 587."""
    c = _config_email()
    if c["ssl_diretto"]:
        with smtplib.SMTP_SSL(c["host"], c["port"]) as s:
            s.login(c["username"], c["password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(c["host"], c["port"]) as s:
            s.ehlo()
            s.starttls()
            s.login(c["username"], c["password"])
            s.send_message(msg)


def diagnostica_invio() -> tuple[bool, str]:
    """Verifica che una configurazione esista e che il server accetti il
    login. Serve a distinguere «configurazione assente» da «password
    scaduta» senza dover fare una iscrizione di prova."""
    try:
        c = _config_email()
    except Exception as exc:
        return False, str(exc)
    try:
        if c["ssl_diretto"]:
            with smtplib.SMTP_SSL(c["host"], c["port"]) as s:
                s.login(c["username"], c["password"])
        else:
            with smtplib.SMTP(c["host"], c["port"]) as s:
                s.ehlo()
                s.starttls()
                s.login(c["username"], c["password"])
        sezione = "[smtp]" if c["host"] != "smtp.gmail.com" else "[gmail]"
        return True, (f"Invio eventi OK — mittente {c['from']} "
                      f"via {c['host']}:{c['port']} (sezione {sezione})")
    except smtplib.SMTPAuthenticationError as exc:
        return False, f"Login rifiutato da {c['host']} (password per le app da rigenerare?): {exc}"
    except Exception as exc:
        return False, f"Errore su {c['host']}:{c['port']} — {exc}"


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


FIRMA = (
    "A presto,\n"
    "Associazione The Organism\n"
    "www.pnev.it · apstheorganism@gmail.com\n"
)


def _data_iscritto(evento: dict, iscrizione: dict) -> str:
    """Data e ora dell'appuntamento DI QUESTO iscritto.

    Negli eventi a turni (screening) ognuno ha il suo orario in slot_orario;
    l'email usava sempre l'ora di inizio dell'evento, quindi a tutti arrivava
    lo stesso orario. Se lo slot c'e', vale lo slot."""
    slot = iscrizione.get("slot_orario")
    if isinstance(slot, datetime):
        return _format_data_evento(slot)
    return _format_data_evento(evento["data_ora"])


def _sede(evento: dict) -> str:
    return evento.get("sede") or ""


def _testo_conferma_iscritto(evento: dict, iscrizione: dict) -> str:
    """Testo plain-text dell'email di conferma all'iscritto."""
    stato = iscrizione.get("stato", "confermata")
    nome = iscrizione.get("nome", "").strip()
    data_str = _data_iscritto(evento, iscrizione)

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
        + FIRMA
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


def _testo_promemoria_iscritto(evento: dict, iscrizione: dict, tipo: str = "24h") -> str:
    """
    Testo plain-text del promemoria pre-evento.
    tipo: '48h' (mancano 2 giorni) o '24h' (manca 1 giorno / domani)
    """
    nome = iscrizione.get("nome", "").strip()
    data_str = _data_iscritto(evento, iscrizione)

    if tipo == "48h":
        apertura = (
            f"Ciao {nome},\n\n"
            f"ti ricordiamo che tra due giorni ci sarà l'incontro a cui sei iscritto/a:\n\n"
        )
    else:  # 24h
        apertura = (
            f"Ciao {nome},\n\n"
            f"ci vediamo domani! Ti ricordiamo l'appuntamento a cui sei iscritto/a:\n\n"
        )

    corpo = (
        f"  {evento.get('titolo', '')}\n"
        f"  📅 {data_str}\n"
    )
    if evento.get("sede"):
        corpo += f"  📍 {evento['sede']}\n"
    if evento.get("conduttore"):
        corpo += f"  👤 Conduttore: {evento['conduttore']}\n"
    if evento.get("prezzo") is not None and float(evento["prezzo"]) > 0:
        corpo += f"  💶 Contributo: € {float(evento['prezzo']):.2f}\n"

    chiusura = (
        "\n"
        "Ti aspettiamo. Se per qualsiasi motivo non potrai più esserci, "
        "ti chiediamo gentilmente di avvisarci rispondendo a questa email, "
        "così possiamo liberare il posto per chi è in lista d'attesa.\n\n"
        + FIRMA
    )
    return apertura + corpo + chiusura


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


def invia_promemoria_iscritto(
    evento: dict,
    iscrizione: dict,
    tipo: str = "24h",
) -> None:
    """
    Invia email di promemoria pre-evento all'iscritto.

    Args:
        evento: dict con i dati dell'evento
        iscrizione: dict con i dati dell'iscritto
        tipo: '48h' o '24h'

    Solleva eccezione se l'invio fallisce.
    """
    to_email = iscrizione.get("email")
    if not to_email:
        raise ValueError("Email dell'iscritto mancante")

    msg = EmailMessage()
    titolo_ev = evento.get("titolo", "Evento")

    if tipo == "48h":
        msg["Subject"] = f"Tra 2 giorni: {titolo_ev}"
    else:
        msg["Subject"] = f"Ci vediamo domani: {titolo_ev}"

    msg["From"] = _from_address()
    msg["To"] = to_email
    msg.set_content(_testo_promemoria_iscritto(evento, iscrizione, tipo))

    _send(msg)
    logger.info(
        f"Promemoria {tipo} inviato a {to_email} per evento "
        f"{evento.get('id')} (iscrizione {iscrizione.get('id')})"
    )
