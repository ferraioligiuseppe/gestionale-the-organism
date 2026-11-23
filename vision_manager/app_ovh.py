# -*- coding: utf-8 -*-
"""
vision_manager/app_ovh.py - Ingresso del gestionale oculistica sul server OVH.

Non cambia niente dell'app: chiede una password e poi avvia vision_manager/app.py
cosi' com'e'. Su Streamlit Cloud si continua a usare app.py, che resta intatto.

La password arriva dalla variabile d'ambiente OCULISTICA_PASSWORD (segreto GitHub
con lo stesso nome). Se manca, l'app non si apre: meglio chiusa che aperta a tutti.
"""
import hmac
import os
import runpy
import time

import streamlit as st

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
_CHIAVE = "ocu_accesso_ok"
MAX_ERRORI = 8            # tentativi sbagliati, in tutto, prima della pausa
PAUSA_SECONDI = 300


@st.cache_resource
def _registro():
    """Conteggio degli errori comune a tutte le sessioni (frena chi prova a indovinare)."""
    return {"errori": 0, "fino_a": 0.0}


def _password_attesa():
    return os.environ.get("OCULISTICA_PASSWORD", "")


def _cancello():
    st.set_page_config(page_title="Vision Manager — accesso", layout="centered")
    st.title("Vision Manager")
    attesa = _password_attesa()
    if not attesa:
        st.error("Accesso non configurato su questo server. Avvisa lo Studio The Organism.")
        st.stop()
    reg = _registro()
    resta = int(reg["fino_a"] - time.time())
    if resta > 0:
        st.error("Troppi tentativi sbagliati. Riprova tra %s minuti." % (resta // 60 + 1))
        st.stop()
    with st.form("ocu_accesso"):
        data = st.text_input("Password", type="password")
        entra = st.form_submit_button("Entra", type="primary")
    if entra:
        if hmac.compare_digest(data.encode("utf-8"), attesa.encode("utf-8")):
            reg["errori"] = 0
            st.session_state[_CHIAVE] = True
            st.rerun()
        reg["errori"] += 1
        time.sleep(1.5)
        if reg["errori"] >= MAX_ERRORI:
            reg["errori"] = 0
            reg["fino_a"] = time.time() + PAUSA_SECONDI
        st.error("Password non corretta.")
    st.stop()


if not st.session_state.get(_CHIAVE):
    _cancello()

# Da qui in poi e' l'app di sempre: nessun comando Streamlit prima, perche'
# app.py imposta da sola la pagina (st.set_page_config deve restare il primo).
runpy.run_path(_APP, run_name="__main__")
