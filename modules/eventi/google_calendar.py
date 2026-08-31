# -*- coding: utf-8 -*-
"""Creazione eventi sul Google Calendar dello studio, via account di servizio.

Secrets richiesti (nell'app dove viene chiamato — pnev_pubblico):
    GOOGLE_SERVICE_ACCOUNT_JSON = '''{ ...contenuto intero del file JSON... }'''
    GOOGLE_CALENDAR_ID = "centro.oculus@gmail.com"

Il calendario indicato da GOOGLE_CALENDAR_ID deve essere condiviso con
l'email "client_email" del service account, permesso "Apportare modifiche
agli eventi".
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta

import streamlit as st

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    raw = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON non configurato nei secrets")
    info = json.loads(raw) if isinstance(raw, str) else dict(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def crea_evento_calendario(
    titolo: str,
    inizio: datetime,
    durata_minuti: int = 15,
    descrizione: str = "",
    calendar_id: str | None = None,
) -> str | None:
    """Crea un evento sul calendario dello studio. Ritorna l'id evento, o None se fallisce
    (non blocca mai il flusso di iscrizione)."""
    try:
        service = _get_service()
        cal_id = calendar_id or st.secrets.get("GOOGLE_CALENDAR_ID")
        if not cal_id:
            raise RuntimeError("GOOGLE_CALENDAR_ID non configurato")
        fine = inizio + timedelta(minutes=durata_minuti)
        body = {
            "summary": titolo,
            "description": descrizione,
            "start": {"dateTime": inizio.isoformat(), "timeZone": "Europe/Rome"},
            "end": {"dateTime": fine.isoformat(), "timeZone": "Europe/Rome"},
        }
        ev = service.events().insert(calendarId=cal_id, body=body).execute()
        return ev.get("id")
    except Exception as e:
        logger.error(f"Errore creazione evento Google Calendar: {e}")
        return None


def elimina_evento_calendario(event_id: str, calendar_id: str | None = None) -> bool:
    try:
        service = _get_service()
        cal_id = calendar_id or st.secrets.get("GOOGLE_CALENDAR_ID")
        service.events().delete(calendarId=cal_id, eventId=event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Errore eliminazione evento Google Calendar: {e}")
        return False
