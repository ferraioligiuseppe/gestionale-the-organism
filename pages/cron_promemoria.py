# -*- coding: utf-8 -*-
"""
pages/cron_promemoria.py

Endpoint trigger per i promemoria automatici pre-evento.
Viene chiamato da GitHub Actions (o cron-job.org) ogni notte.

Protezione: richiede un token segreto passato via query param ?token=XXX
che deve coincidere con st.secrets["cron"]["TOKEN"].

URL di chiamata:
    https://testgestionale.streamlit.app/cron_promemoria?token=IL_TUO_TOKEN

Se chiamata senza token valido, non fa nulla e mostra errore.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Cron Promemoria", layout="centered")

# === AUTENTICAZIONE VIA TOKEN ===
def _check_token() -> bool:
    """Verifica il token passato via query param contro st.secrets."""
    try:
        token_atteso = st.secrets.get("cron", {}).get("TOKEN")
    except Exception:
        token_atteso = None

    if not token_atteso:
        st.error("⚠️ Token cron non configurato in secrets ([cron].TOKEN)")
        return False

    # Leggi token dalla query string
    token_ricevuto = st.query_params.get("token")

    if token_ricevuto != token_atteso:
        st.error("🔒 Token non valido o mancante")
        return False

    return True


st.title("⏰ Cron Promemoria Eventi")

if not _check_token():
    st.stop()

st.success("✅ Token valido — eseguo i promemoria")

# Modalità dry-run opzionale: ?token=XXX&dry=1
dry_run = st.query_params.get("dry") == "1"
if dry_run:
    st.info("🧪 Modalità DRY RUN: non invio realmente, mostro solo cosa farei")

# === CONNESSIONE E PROCESSO ===
try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Errore connessione DB: {e}")
    st.stop()

try:
    from modules.eventi.promemoria_eventi import processa_promemoria_automatici
    report = processa_promemoria_automatici(conn, dry_run=dry_run)
except Exception as e:
    st.error(f"Errore esecuzione promemoria: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# === REPORT ===
st.subheader("Report")
col1, col2, col3 = st.columns(3)
col1.metric("Eventi processati", report["eventi_processati"])
col2.metric("Email inviate", report["email_inviate"])
col3.metric("Email fallite", report["email_fallite"])

if report["dettaglio"]:
    st.write("**Dettaglio:**")
    st.dataframe(report["dettaglio"], use_container_width=True)
else:
    st.info("Nessun promemoria da inviare in questo momento.")

if report["errori"]:
    st.error("Errori:")
    for err in report["errori"]:
        st.code(err)

# Output machine-readable per il cron (testo semplice in fondo)
st.text(
    f"CRON_RESULT eventi={report['eventi_processati']} "
    f"inviate={report['email_inviate']} fallite={report['email_fallite']}"
)
