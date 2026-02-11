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
