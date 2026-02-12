import os, sys, time, hmac

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

# Page config MUST be set before any Streamlit UI output
st.set_page_config(page_title="The Organism – Vision Manager", layout="wide")


def require_basic_login():
    """Multi-user username/password gate with inactivity timeout.

    Secrets format (TOML):

    [auth_basic]
    timeout_minutes = 30
    debug = false  # optional

    [auth_basic.users.admin]
    password = "..."

    [auth_basic.users.segreteria]
    password = "..."
    """
    auth = st.secrets.get("auth_basic", None)
    if not auth:
        st.error("Auth non configurata nei Secrets (auth_basic).")
        st.stop()

    timeout_minutes = int(auth.get("timeout_minutes", 30))
    timeout_seconds = max(60, timeout_minutes * 60)
    debug = bool(auth.get("debug", False))

    users_raw = auth.get("users", {}) or {}
    # normalize usernames to lowercase for matching
    users = {str(k).strip().lower(): (v or {}) for k, v in users_raw.items()}

    if debug:
        st.sidebar.info(f"DEBUG auth: utenti configurati = {', '.join(sorted(users.keys())) or '(nessuno)'}")

    now = time.time()
    last = st.session_state.get("last_activity_ts")

    # If already authenticated, enforce inactivity timeout
    if st.session_state.get("is_auth", False):
        if last is not None and (now - last) > timeout_seconds:
            st.session_state.clear()
            st.warning(f"Sessione scaduta per inattività ({timeout_minutes} minuti).")
            st.stop()

        st.session_state["last_activity_ts"] = now
        return

    # Login screen
    st.title("Login")

    username_in = st.text_input("Username", key="login_username")
    password_in = st.text_input("Password", type="password", key="login_password")

    if st.button("Accedi", key="login_btn"):
        u = (username_in or "").strip().lower()
        p = password_in or ""

        rec = users.get(u)
        if not rec:
            st.error("Credenziali non valide")
            st.stop()

        expected = str(rec.get("password", ""))
        if hmac.compare_digest(p, expected):
            st.session_state["is_auth"] = True
            st.session_state["auth_user"] = u
            st.session_state["last_activity_ts"] = now
            st.rerun()
        else:
            st.error("Credenziali non valide")

    st.stop()


# Enforce authentication before running the app
require_basic_login()

# Logout button
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()


# -------------------------
# Main App (unchanged logic)
# -------------------------
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
