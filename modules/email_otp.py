# -*- coding: utf-8 -*-
"""
modules/email_otp.py
Invio email semplice via Gmail SMTP (richiede una "password per le app"
generata su myaccount.google.com/apppasswords, salvata nei Secrets:
[gmail] EMAIL = "..." / APP_PASSWORD = "...").
"""
import smtplib
from email.mime.text import MIMEText


def diagnostica_email() -> tuple[bool, str]:
    """Verifica se la configurazione Gmail è presente e funzionante."""
    try:
        import streamlit as st
        try:
            cfg = st.secrets.get("gmail", {})
        except Exception:
            return False, "Secrets non disponibili (secrets.toml assente)."
        mittente = cfg.get("EMAIL")
        app_password = cfg.get("APP_PASSWORD")
        if not mittente:
            return False, "Manca [gmail] EMAIL nei Secrets."
        if not app_password:
            return False, "Manca [gmail] APP_PASSWORD nei Secrets."
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(mittente, app_password)
        return True, f"Configurazione OK — mittente: {mittente}"
    except Exception as e:
        return False, f"Errore login SMTP: {e}"


def invia_email(to_email: str, oggetto: str, corpo: str) -> bool:
    """Invio email generico (conferme, notifiche) via lo stesso Gmail SMTP
    usato per i codici OTP."""
    try:
        import streamlit as st
        cfg = st.secrets.get("gmail", {})
        mittente = cfg.get("EMAIL")
        app_password = cfg.get("APP_PASSWORD")
        if not mittente or not app_password:
            return False
        msg = MIMEText(corpo)
        msg["Subject"] = oggetto
        msg["From"] = mittente
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(mittente, app_password)
            server.sendmail(mittente, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def invia_codice(to_email: str, codice: str) -> bool:
    try:
        import streamlit as st
        cfg = st.secrets.get("gmail", {})
        mittente = cfg.get("EMAIL")
        app_password = cfg.get("APP_PASSWORD")
        if not mittente or not app_password:
            return False
        msg = MIMEText(
            f"Il tuo codice di accesso al Portale famiglia — Studio The Organism è:\n\n"
            f"{codice}\n\nValido per 10 minuti. Se non hai richiesto l'accesso, ignora questa email."
        )
        msg["Subject"] = "Codice di accesso — Portale famiglia The Organism"
        msg["From"] = mittente
        msg["To"] = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(mittente, app_password)
            server.sendmail(mittente, [to_email], msg.as_string())
        return True
    except Exception:
        return False
