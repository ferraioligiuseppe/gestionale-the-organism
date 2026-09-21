# -*- coding: utf-8 -*-
"""
modules/email_otp.py
Invio email semplice via Gmail SMTP (richiede una "password per le app"
generata su myaccount.google.com/apppasswords, salvata nei Secrets:
[gmail] EMAIL = "..." / APP_PASSWORD = "...").
"""
import smtplib
from email.mime.text import MIMEText


def _config_invio():
    """Restituisce (host, porta, ssl_diretto, mittente, password) o (None, motivo).

    Il gestionale ha due sezioni di secrets nate in momenti diversi:
    [gmail] EMAIL/APP_PASSWORD, usata qui, e [smtp] HOST/PORT/USERNAME/
    PASSWORD, usata da ui_questionari e dal pacchetto eventi. Se ne e'
    configurata una sola, meta' delle email del gestionale non parte e
    non e' ovvio il perche'. Qui si accettano entrambe."""
    try:
        import streamlit as st
        try:
            gmail = st.secrets.get("gmail", {})
        except Exception:
            return None, "Secrets non disponibili (secrets.toml assente)."
        if gmail.get("EMAIL") and gmail.get("APP_PASSWORD"):
            return ("smtp.gmail.com", 465, True,
                    gmail["EMAIL"], gmail["APP_PASSWORD"]), ""
        smtp = st.secrets.get("smtp", {})
        if smtp.get("HOST") and smtp.get("USERNAME") and smtp.get("PASSWORD"):
            porta = int(smtp.get("PORT") or 587)
            usa_tls = str(smtp.get("USE_TLS", "true")).lower() in ("1", "true", "yes", "y")
            return (smtp["HOST"], porta, not usa_tls,
                    smtp.get("FROM") or smtp["USERNAME"], smtp["PASSWORD"]), ""
        return None, ("Nessuna configurazione email nei Secrets: serve "
                      "[gmail] EMAIL + APP_PASSWORD oppure [smtp] HOST + USERNAME + PASSWORD.")
    except Exception as e:
        return None, f"Configurazione email illeggibile: {e}"


def _spedisci(mittente, password, host, porta, ssl_diretto, to_email, msg):
    if ssl_diretto:
        with smtplib.SMTP_SSL(host, porta) as server:
            server.login(mittente, password)
            server.sendmail(mittente, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(host, porta) as server:
            server.ehlo()
            server.starttls()
            server.login(mittente, password)
            server.sendmail(mittente, [to_email], msg.as_string())


def diagnostica_email() -> tuple[bool, str]:
    """Verifica che la configurazione email sia presente e che il server
    accetti il login."""
    conf, motivo = _config_invio()
    if not conf:
        return False, motivo
    host, porta, ssl_diretto, mittente, password = conf
    try:
        if ssl_diretto:
            with smtplib.SMTP_SSL(host, porta) as server:
                server.login(mittente, password)
        else:
            with smtplib.SMTP(host, porta) as server:
                server.ehlo()
                server.starttls()
                server.login(mittente, password)
        return True, f"Configurazione OK — mittente: {mittente} via {host}:{porta}"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Login rifiutato da {host} (password per le app da rigenerare?): {e}"
    except Exception as e:
        return False, f"Errore login SMTP su {host}:{porta} — {e}"


def invia_email(to_email: str, oggetto: str, corpo: str, dettaglio: bool = False):
    """Invio email generico (conferme, notifiche) via lo stesso Gmail SMTP
    usato per i codici OTP.

    dettaglio=False → ritorna solo True/False (come prima: tutti i
    chiamanti storici continuano a funzionare senza modifiche).
    dettaglio=True  → ritorna (ok, motivo). La pagina pubblica delle
    iscrizioni lo chiamava gia' cosi', ma il parametro non esisteva:
    ogni invio sollevava TypeError, veniva inghiottito dal try/except
    del chiamante e l'iscritto non riceveva nulla. Da qui nasceva
    l'assenza delle email di conferma agli eventi.

    Il motivo dell'errore viene restituito invece di essere perso: senza
    non c'e' modo di distinguere una password scaduta da un indirizzo
    sbagliato."""
    def _esito(ok, motivo=""):
        return (ok, motivo) if dettaglio else ok

    try:
        conf, motivo = _config_invio()
        if not conf:
            return _esito(False, motivo)
        host, porta, ssl_diretto, mittente, password = conf
        if not to_email or "@" not in to_email:
            return _esito(False, f"Indirizzo destinatario non valido: {to_email!r}")
        msg = MIMEText(corpo)
        msg["Subject"] = oggetto
        msg["From"] = mittente
        msg["To"] = to_email
        _spedisci(mittente, password, host, porta, ssl_diretto, to_email, msg)
        return _esito(True, f"Inviata a {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        return _esito(False, f"Login Gmail rifiutato (password per le app da rigenerare?): {e}")
    except smtplib.SMTPRecipientsRefused as e:
        return _esito(False, f"Destinatario rifiutato dal server: {e}")
    except Exception as e:
        return _esito(False, f"{type(e).__name__}: {e}")


def invia_codice(to_email: str, codice: str, dettaglio: bool = False):
    """Manda il codice di accesso al portale.

    dettaglio=True ritorna (ok, motivo). Prima l'esito era un solo
    True/False: quando il codice non arrivava non c'era modo di sapere
    se fosse la password per le app scaduta, l'indirizzo sbagliato o il
    server irraggiungibile, e la schermata di login non poteva dire
    niente di utile a chi stava aspettando."""
    def _esito(ok, motivo=""):
        return (ok, motivo) if dettaglio else ok

    try:
        conf, motivo = _config_invio()
        if not conf:
            return _esito(False, motivo)
        host, porta, ssl_diretto, mittente, password = conf
        if not to_email or "@" not in to_email:
            return _esito(False, f"Indirizzo non valido: {to_email!r}")
        msg = MIMEText(
            f"Il tuo codice di accesso al Portale famiglia — Studio The Organism è:\n\n"
            f"{codice}\n\nValido per 10 minuti. Se non hai richiesto l'accesso, ignora questa email."
        )
        msg["Subject"] = "Codice di accesso — Portale famiglia The Organism"
        msg["From"] = mittente
        msg["To"] = to_email
        _spedisci(mittente, password, host, porta, ssl_diretto, to_email, msg)
        return _esito(True, f"Inviata a {to_email}")
    except smtplib.SMTPAuthenticationError as exc:
        return _esito(False, f"Login rifiutato (password per le app da rigenerare?): {exc}")
    except smtplib.SMTPRecipientsRefused as exc:
        return _esito(False, f"Destinatario rifiutato dal server: {exc}")
    except Exception as exc:
        return _esito(False, f"{type(exc).__name__}: {exc}")
