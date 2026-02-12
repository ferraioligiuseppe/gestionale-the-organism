import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import hmac
from db import get_conn, init_db
from ui_pazienti import ui_pazienti
from ui_visita_visiva import ui_visita_visiva
from ui_prescrizione import ui_prescrizione
from ui_storico_confronto import ui_storico_confronto
from ui_diagnostica import ui_diagnostica

st.set_page_config(page_title="The Organism – Vision Manager", layout="wide")

def require_basic_login():
    auth = st.secrets.get("auth_basic", None)
    if not auth:
        st.error("Auth non configurata nei Secrets (auth_basic).")
        st.stop()

    # Se già autenticato
    if st.session_state.get("is_auth", False):
        return

    st.title("Login")

    u = st.text_input("Username", key="login_username")
    p = st.text_input("Password", type="password", key="login_password")

    if st.button("Accedi", key="login_btn"):
        ok_user = hmac.compare_digest((u or "").strip(), str(auth.get("username", "")).strip())
        ok_pass = hmac.compare_digest(p or "", str(auth.get("password", "")))
        if ok_user and ok_pass:
            st.session_state["is_auth"] = True
            st.session_state["auth_user"] = (u or "").strip()
            st.rerun()
        else:
            st.error("Credenziali non valide")

    st.stop()

require_basic_login()

# Logout (visibile solo se loggato)
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()


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
