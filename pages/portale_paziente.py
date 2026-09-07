# -*- coding: utf-8 -*-
# pages/portale_paziente.py
#
# Portale famiglia: login con email + password, vede le procedure da fare
# a casa questa settimana (con video how-to), spunta "fatto" e dà un
# giudizio 1-5 su come è andata. Lo studio vede l'aderenza nel gestionale.

import streamlit as st
import sys, os, datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.app_core import get_connection
from modules import db_portale_famiglia as db
from modules import email_otp

st.set_page_config(
    page_title="The Organism — Portale famiglia",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { max-width:600px !important; padding:1.5rem 1rem 3rem 1rem !important; }
</style>
""", unsafe_allow_html=True)

conn = get_connection()
db.init_db(conn)

st.markdown("### 🏠 Portale famiglia — Studio The Organism")

if "portale_paziente_id" not in st.session_state:
    st.session_state.portale_paziente_id = None
if "portale_step" not in st.session_state:
    st.session_state.portale_step = "password"  # password -> otp
if "portale_email_pendente" not in st.session_state:
    st.session_state.portale_email_pendente = None
if "portale_pid_pendente" not in st.session_state:
    st.session_state.portale_pid_pendente = None

if not st.session_state.portale_paziente_id and st.session_state.portale_step == "password":
    st.caption("Accedi con le credenziali fornite dallo studio per vedere le procedure da fare a casa.")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        ok = st.form_submit_button("Accedi", type="primary", use_container_width=True)
    if ok:
        pid = db.login(conn, email, password)
        if pid:
            codice = db.genera_otp(conn, email)
            inviata = email_otp.invia_codice(email.strip(), codice)
            st.session_state.portale_email_pendente = email.strip()
            st.session_state.portale_pid_pendente = pid
            st.session_state.portale_step = "otp"
            if not inviata:
                st.session_state.portale_otp_fallback = codice  # invio non riuscito: mostra comunque per non bloccare lo studio
            st.rerun()
        else:
            st.error("Email o password non corretti.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com — se non hai ancora le credenziali, contatta lo studio.")
    st.stop()

if not st.session_state.portale_paziente_id and st.session_state.portale_step == "otp":
    st.caption(f"Abbiamo inviato un codice a **{st.session_state.portale_email_pendente}**. Inseriscilo qui sotto (valido 10 minuti).")
    if st.session_state.get("portale_otp_fallback"):
        st.warning(f"Invio email non riuscito — codice di emergenza: {st.session_state.portale_otp_fallback}")
    with st.form("otp_form"):
        codice_inserito = st.text_input("Codice ricevuto via email", max_chars=6)
        ok2 = st.form_submit_button("Verifica", type="primary", use_container_width=True)
    if ok2:
        if db.verifica_otp(conn, st.session_state.portale_email_pendente, codice_inserito):
            st.session_state.portale_paziente_id = st.session_state.portale_pid_pendente
            st.session_state.portale_step = "password"
            st.rerun()
        else:
            st.error("Codice non valido o scaduto.")
    if st.button("↩ Torna indietro"):
        st.session_state.portale_step = "password"
        st.rerun()
    st.stop()

paziente_id = st.session_state.portale_paziente_id

c1, c2 = st.columns([4, 1])
c1.success("Accesso effettuato ✅")
if c2.button("Esci"):
    st.session_state.portale_paziente_id = None
    st.rerun()

programma = db.get_programma_corrente(conn, paziente_id)
if not programma:
    st.info("Non ci sono ancora procedure assegnate per casa. Verranno mostrate qui appena lo studio le invia.")
    st.stop()

st.markdown(f"#### 📋 Programma — {programma['protocollo']} · settimana {programma['settimana']}")
st.caption(f"Assegnato il {programma['data_assegnazione']:%d/%m/%Y}")

oggi = datetime.date.today()
data_sel = st.date_input("Giorno", value=oggi, max_value=oggi)

for proc in programma["procedure"]:
    nome = proc if isinstance(proc, str) else proc.get("nome", str(proc))
    with st.container(border=True):
        st.markdown(f"**{nome}**")
        video_url = db.get_video_url(conn, nome)
        if video_url:
            st.video(video_url)
        else:
            st.caption("Video non ancora disponibile per questa procedura.")
        cc1, cc2 = st.columns([1, 2])
        fatto = cc1.checkbox("✅ Fatto oggi", key=f"fatto_{nome}_{data_sel}")
        valutazione = cc2.select_slider("Com'è andata?", options=[1, 2, 3, 4, 5], value=3,
                                         key=f"val_{nome}_{data_sel}",
                                         format_func=lambda v: "😣😕😐🙂😄"[v-1])
        if st.button("💾 Salva", key=f"save_{nome}_{data_sel}"):
            db.salva_feedback(conn, paziente_id, nome, data_sel, fatto, valutazione)
            st.success("Salvato ✅")

st.markdown("---")
riep = db.get_aderenza_riepilogo(conn, paziente_id, giorni=30)
if riep["totali"]:
    st.caption(f"Ultimi 30 giorni: {riep['pct']}% delle procedure fatte "
               f"({riep['fatti']}/{riep['totali']}) · valutazione media {riep['media_valutazione'] or '—'}/5")
