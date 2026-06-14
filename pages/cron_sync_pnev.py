# -*- coding: utf-8 -*-
"""
pages/cron_sync_pnev.py

Endpoint trigger per la sincronizzazione automatica dei pazienti MAPS da pnev.it.
Viene chiamato da GitHub Actions (o cron-job.org), p.es. ogni mattina.

Protezione: stesso token dei promemoria, st.secrets["cron"]["TOKEN"], via ?token=XXX.

URL di chiamata:
    https://testgestionale.streamlit.app/cron_sync_pnev?token=IL_TUO_TOKEN

Prova senza scrivere nulla (dry run):
    https://testgestionale.streamlit.app/cron_sync_pnev?token=IL_TUO_TOKEN&dry=1
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Cron Sync pnev.it", layout="centered")


def _check_token() -> bool:
    try:
        token_atteso = st.secrets.get("cron", {}).get("TOKEN")
    except Exception:
        token_atteso = None
    if not token_atteso:
        st.error("⚠️ Token cron non configurato in secrets ([cron].TOKEN)")
        return False
    if st.query_params.get("token") != token_atteso:
        st.error("🔒 Token non valido o mancante")
        return False
    return True


st.title("🔗 Cron Sync pazienti pnev.it")

if not _check_token():
    st.stop()

st.success("✅ Token valido — eseguo la sincronizzazione")

dry_run = st.query_params.get("dry") == "1"
if dry_run:
    st.info("🧪 Modalità DRY RUN: non importo davvero, mostro solo cosa farei")

try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Errore connessione DB: {e}")
    st.stop()

try:
    from modules.ui_sync_pnev import processa_sync_pnev
    report = processa_sync_pnev(conn, dry_run=dry_run)
except Exception as e:
    st.error(f"Errore esecuzione sync: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

st.subheader("Report")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Letti da MAPS", report["letti"])
c2.metric("Già presenti", report["gia_presenti"])
c3.metric("Esclusi (test)", report["esclusi_test"])
c4.metric("Importati", report["importati"])

if report["dettaglio"]:
    st.write("**Dettaglio:**")
    st.dataframe(report["dettaglio"], use_container_width=True)
else:
    st.info("Nessun nuovo paziente da importare in questo momento.")

if report["errori"]:
    st.error("Errori:")
    for err in report["errori"]:
        st.code(err)

# Riga machine-readable per il cron
st.text(
    f"CRON_RESULT letti={report['letti']} gia_presenti={report['gia_presenti']} "
    f"esclusi_test={report['esclusi_test']} importati={report['importati']}"
)
