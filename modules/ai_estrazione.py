# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  AI ESTRAZIONE — lettura dei documenti clinici (Mattone 2)           ║
║  Motore: Google Gemini (piano gratuito, legge testo, foto e PDF).    ║
║                                                                      ║
║  Legge un documento caricato (PDF o foto/scansione) e ne estrae in   ║
║  chiaro i dati clinici utili: valori, diagnosi precedente, terapie,  ║
║  note — SENZA inventare nulla. Il risultato va sempre rivisto e      ║
║  confermato dal clinico prima di entrare in cartella.                ║
║                                                                      ║
║  Chiave API GRATUITA: aistudio.google.com → Get API key.            ║
║  Poi nei Secrets dell'app →                                          ║
║     [ai]                                                             ║
║     ENABLED = true                                                   ║
║     GEMINI_API_KEY = "..."                                           ║
║     MODEL = "gemini-1.5-flash"   # facoltativo                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

_PROMPT = (
    "Sei un assistente clinico per uno studio di optometria comportamentale "
    "e psicologia (metodo PNEV). Ti viene fornito un documento clinico di un "
    "paziente (referto, esame visivo/funzionale, diagnosi precedente). "
    "Estrai in modo fedele e SENZA inventare nulla le informazioni utili, "
    "organizzandole così:\n\n"
    "• TIPO DI DOCUMENTO:\n"
    "• DATA (se presente):\n"
    "• AUTORE / STRUTTURA (se presente):\n"
    "• VALORI E MISURE rilevati (elenco):\n"
    "• DIAGNOSI / CONCLUSIONI:\n"
    "• TERAPIE / INDICAZIONI:\n"
    "• NOTE UTILI per la prossima visita:\n\n"
    "Se un campo non è presente nel documento, scrivi «non indicato». "
    "Rispondi in italiano, in modo sintetico e clinico."
)


def ai_disponibile() -> bool:
    try:
        a = st.secrets.get("ai", {})
        if not a.get("ENABLED", False):
            return False
        return bool(a.get("GEMINI_API_KEY")) or bool(a.get("OPENAI_API_KEY"))
    except Exception:
        return False


def _provider() -> str:
    """Sceglie il motore: Gemini se c'è la sua chiave, altrimenti OpenAI."""
    a = st.secrets.get("ai", {})
    if a.get("GEMINI_API_KEY"):
        return "gemini"
    if a.get("OPENAI_API_KEY"):
        return "openai"
    return ""


def _modello() -> str:
    return str(st.secrets.get("ai", {}).get("MODEL", "gemini-2.0-flash"))


# Nomi modello provati in ordine (il primo è quello dei Secrets, se presente).
# Robusto ai cambi di nome lato Google: prova i candidati finché uno risponde.
_CANDIDATI = [
    "gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest",
    "gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash-001",
]


def _genera(genai, parts):
    """Chiama generate_content provando più nomi di modello (gestisce i 404)."""
    nomi = []
    scelto = _modello()
    if scelto:
        nomi.append(scelto)
    for n in _CANDIDATI:
        if n not in nomi:
            nomi.append(n)
    ultimo_err = None
    for nome in nomi:
        try:
            model = genai.GenerativeModel(nome)
            resp = model.generate_content(parts)
            return (resp.text or "").strip()
        except Exception as e:
            ultimo_err = e
            if "404" in str(e) or "not found" in str(e).lower() \
                    or "not supported" in str(e).lower():
                continue
            raise
    raise ultimo_err or RuntimeError("Nessun modello Gemini disponibile.")


def _configura():
    import google.generativeai as genai
    key = st.secrets.get("ai", {}).get("GEMINI_API_KEY", "")
    genai.configure(api_key=key)
    return genai


def _testo_da_pdf(dati: bytes) -> str:
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(dati))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:15]).strip()
    except Exception:
        return ""


def estrai_da_documento(dati: bytes, mime: str, nome: str = "") -> str:
    """Ritorna il testo estratto/strutturato dal documento, o un messaggio
    d'errore leggibile (prefissato con '⚠️')."""
    if not ai_disponibile():
        return ("⚠️ AI non configurata. Aggiungi nei Secrets dell'app, sotto [ai], "
                "una chiave: GEMINI_API_KEY (gratuita, aistudio.google.com) "
                "oppure OPENAI_API_KEY (platform.openai.com).")
    prov = _provider()
    try:
        if prov == "openai":
            return _estrai_openai(dati, mime, nome)
        return _estrai_gemini(dati, mime, nome)
    except Exception as e:
        return f"⚠️ Errore durante l'analisi AI: {e}"


def _estrai_gemini(dati: bytes, mime: str, nome: str) -> str:
    mime = (mime or "").lower()
    genai = _configura()
    if mime.startswith("image/") or "pdf" in mime or nome.lower().endswith(".pdf"):
        tipo_mime = mime if mime else ("application/pdf"
                                       if nome.lower().endswith(".pdf") else "image/jpeg")
        if "pdf" in tipo_mime and len(dati) > 15 * 1024 * 1024:
            testo = _testo_da_pdf(dati)
            if len(testo) < 40:
                return ("⚠️ PDF troppo grande e senza testo leggibile. "
                        "Ricaricalo come foto della pagina.")
            return _genera(genai, [_PROMPT, testo[:12000]])
        return _genera(genai, [_PROMPT, {"mime_type": tipo_mime, "data": dati}])
    return "⚠️ Formato non supportato per l'analisi AI (usa PDF o foto)."


def _estrai_openai(dati: bytes, mime: str, nome: str) -> str:
    import base64
    from openai import OpenAI
    a = st.secrets.get("ai", {})
    client = OpenAI(api_key=a.get("OPENAI_API_KEY", ""))
    modello = str(a.get("OPENAI_MODEL", "gpt-4o-mini"))
    mime = (mime or "").lower()
    if mime.startswith("image/"):
        b64 = base64.b64encode(dati).decode()
        resp = client.chat.completions.create(
            model=modello,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": _PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{b64}"}}]}],
            max_tokens=900)
        return (resp.choices[0].message.content or "").strip()
    if "pdf" in mime or nome.lower().endswith(".pdf"):
        testo = _testo_da_pdf(dati)
        if len(testo) < 40:
            return ("⚠️ Questo PDF sembra una scansione (nessun testo leggibile). "
                    "Ricaricalo come foto/immagine della pagina.")
        resp = client.chat.completions.create(
            model=modello,
            messages=[{"role": "system", "content": _PROMPT},
                      {"role": "user", "content": testo[:12000]}],
            max_tokens=900)
        return (resp.choices[0].message.content or "").strip()
    return "⚠️ Formato non supportato per l'analisi AI (usa PDF o foto)."
