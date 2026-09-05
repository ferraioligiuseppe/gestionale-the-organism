# -*- coding: utf-8 -*-
"""Trascrizione audio → testo, stessa chiave AI usata per Assistente PNEV / OCR."""

import streamlit as st


def trascrizione_disponibile():
    a = st.secrets.get("ai", {})
    if not a.get("ENABLED", False):
        return False
    return bool(a.get("OPENAI_API_KEY")) or bool(a.get("GEMINI_API_KEY"))


def trascrivi_audio(dati: bytes, mime: str = "audio/wav") -> str:
    """Ritorna il testo trascritto, o una stringa che inizia con '⚠️' in caso di errore."""
    a = st.secrets.get("ai", {})
    if not a.get("ENABLED", False):
        return "⚠️ AI non configurata nei Secrets (sezione [ai])."
    if a.get("OPENAI_API_KEY"):
        return _trascrivi_openai(dati, mime, a)
    if a.get("GEMINI_API_KEY"):
        return _trascrivi_gemini(dati, mime, a)
    return "⚠️ Nessuna chiave AI configurata (OPENAI_API_KEY o GEMINI_API_KEY)."


def _trascrivi_openai(dati, mime, a):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=a.get("OPENAI_API_KEY", ""))
        ext = "wav" if "wav" in (mime or "") else "webm" if "webm" in (mime or "") else "mp3"
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=(f"seduta.{ext}", dati, mime or "audio/wav"),
            language="it",
        )
        return (resp.text or "").strip()
    except Exception as e:
        return f"⚠️ Errore trascrizione (OpenAI): {e}"


def _trascrivi_gemini(dati, mime, a):
    try:
        import google.generativeai as genai
        genai.configure(api_key=a.get("GEMINI_API_KEY", ""))
        modello = genai.GenerativeModel(str(a.get("GEMINI_MODEL", "gemini-1.5-flash")))
        resp = modello.generate_content([
            "Trascrivi integralmente e letteralmente questo audio in italiano. "
            "Restituisci solo il testo trascritto, senza commenti.",
            {"mime_type": mime or "audio/wav", "data": dati},
        ])
        return (resp.text or "").strip()
    except Exception as e:
        return f"⚠️ Errore trascrizione (Gemini): {e}"
