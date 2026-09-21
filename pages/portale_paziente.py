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
            inviata, motivo = email_otp.invia_codice(email.strip(), codice, dettaglio=True)
            st.session_state.portale_email_pendente = email.strip()
            st.session_state.portale_pid_pendente = pid
            st.session_state.portale_step = "otp"
            # Il codice NON si mostra a schermo quando l'invio fallisce.
            # Prima si faceva "per non bloccare", ma stampare il secondo
            # fattore accanto al primo lo annulla: chi ha la password
            # vedeva anche il codice. Meglio una porta chiusa che una
            # porta che sembra chiusa.
            st.session_state.portale_otp_errore = "" if inviata else motivo
            st.rerun()
        else:
            st.error("Email o password non corretti.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com — se non hai ancora le credenziali, contatta lo studio.")
    st.stop()

if not st.session_state.portale_paziente_id and st.session_state.portale_step == "otp":
    st.caption(f"Abbiamo inviato un codice a **{st.session_state.portale_email_pendente}**. Inseriscilo qui sotto (valido 10 minuti).")
    if st.session_state.get("portale_otp_errore"):
        st.error("Non siamo riusciti a inviare il codice. Chiama lo studio allo "
                 "0815152334 e ti facciamo entrare noi.")
        with st.expander("Dettaglio tecnico (per lo studio)"):
            st.caption(st.session_state["portale_otp_errore"])
    with st.form("otp_form"):
        codice_inserito = st.text_input("Codice ricevuto via email", max_chars=6)
        ok2 = st.form_submit_button("Verifica", type="primary", use_container_width=True)
    if ok2:
        valido, motivo = db.verifica_otp(conn, st.session_state.portale_email_pendente,
                                         codice_inserito)
        if valido:
            st.session_state.portale_paziente_id = st.session_state.portale_pid_pendente
            st.session_state.portale_step = "password"
            st.session_state.pop("portale_otp_errore", None)
            st.rerun()
        else:
            st.error(motivo)

    c1, c2 = st.columns(2)
    if c1.button("✉️ Invia un nuovo codice", use_container_width=True):
        nuovo = db.genera_otp(conn, st.session_state.portale_email_pendente)
        inviata, motivo = email_otp.invia_codice(
            st.session_state.portale_email_pendente, nuovo, dettaglio=True)
        st.session_state.portale_otp_errore = "" if inviata else motivo
        st.rerun()
    if c2.button("↩ Torna indietro", use_container_width=True):
        st.session_state.portale_step = "password"
        st.session_state.portale_email_pendente = None
        st.session_state.portale_pid_pendente = None
        st.session_state.pop("portale_otp_errore", None)
        st.rerun()
    st.stop()

paziente_id = st.session_state.portale_paziente_id

c1, c2 = st.columns([4, 1])
c1.success("Accesso effettuato ✅")
if c2.button("Esci"):
    # Ripulire tutto, non solo l'id: restavano in sessione l'email e il
    # paziente in attesa del codice, e il "torna indietro" della
    # schermata OTP riportava dentro l'accesso precedente.
    for _k in ("portale_paziente_id", "portale_email_pendente",
               "portale_pid_pendente", "portale_otp_errore",
               "portale_otp_fallback"):
        st.session_state.pop(_k, None)
    st.session_state.portale_step = "password"
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
        video_file = st.file_uploader("🎥 Registra/carica un video del bambino che lo esegue (facoltativo)",
                                      type=["mp4", "mov", "webm"], key=f"video_{nome}_{data_sel}")
        if st.button("💾 Salva", key=f"save_{nome}_{data_sel}"):
            video_url = None
            if video_file is not None:
                try:
                    from modules.dropbox_upload import upload_audio_bytes
                    ext = video_file.name.rsplit(".", 1)[-1] if "." in video_file.name else "mp4"
                    path = f"/portale-famiglia/{paziente_id}/{nome.replace(' ','_')}_{data_sel}.{ext}"
                    video_url = upload_audio_bytes(video_file.getvalue(), path)
                except Exception:
                    video_url = None
            db.salva_feedback(conn, paziente_id, nome, data_sel, fatto, valutazione, video_url)
            st.success("Salvato ✅" + (" — video caricato" if video_url else ""))

st.markdown("---")
riep = db.get_aderenza_riepilogo(conn, paziente_id, giorni=30)
if riep["totali"]:
    st.caption(f"Ultimi 30 giorni: {riep['pct']}% delle procedure fatte "
               f"({riep['fatti']}/{riep['totali']}) · valutazione media {riep['media_valutazione'] or '—'}/5")
