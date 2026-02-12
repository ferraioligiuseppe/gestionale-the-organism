import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from db import get_conn, init_db
from ui_pazienti import ui_pazienti
from ui_visita_visiva import ui_visita_visiva
from ui_prescrizione import ui_prescrizione
from ui_storico_confronto import ui_storico_confronto
from ui_diagnostica import ui_diagnostica
import streamlit as st
import streamlit_authenticator as stauth

def require_login():
    cookie = st.secrets["auth"]["cookie"]

    u = st.secrets["auth_temp"]["username"]
    n = st.secrets["auth_temp"]["name"]
    pw_plain = st.secrets["auth_temp"]["password_plain"]

    # HASH al volo (temporaneo)
    pw_hash = stauth.Hasher([pw_plain]).generate()[0]

    credentials = {"usernames": {u: {"name": n, "password": pw_hash}}}

    authenticator = stauth.Authenticate(
        credentials,
        cookie["name"],
        cookie["key"],
        cookie["expiry_days"],
    )

    name, auth_status, username = authenticator.login("Login", "main")

    if auth_status is True:
        authenticator.logout("Logout", "sidebar")
        st.session_state["auth_user"] = username
        return

    if auth_status is False:
        st.error("Username o password non corretti")
        st.stop()

    st.info("Inserisci username e password")
    st.stop()

require_login()

st.set_page_config(page_title="The Organism – Vision Manager", layout="wide")

st.sidebar.title("Vision Manager")
menu = st.sidebar.radio("Menu", [
    "Pazienti",
    "Visita visiva (Referto A4)",
    "Prescrizione occhiali (A4/A5)",
    "Storico + Confronto + Export",
    "Diagnostica",
])

conn = get_conn()
init_db(conn)

if menu == "Pazienti":
    ui_pazienti(conn)
elif menu == "Visita visiva (Referto A4)":
    ui_visita_visiva(conn)
elif menu == "Prescrizione occhiali (A4/A5)":
    ui_prescrizione(conn)
elif menu == "Storico + Confronto + Export":
    ui_storico_confronto(conn)
else:
    ui_diagnostica(conn)

st.sidebar.caption("Backend: Neon (prod) / SQLite (dev)")
