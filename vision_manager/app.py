
import os, sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from db import get_conn, init_db
from ui_pazienti import ui_pazienti
from ui_valutazioni_visive import ui_valutazioni_visive
from ui_refrazione_prescrizione import ui_refrazione_prescrizione
from ui_diagnostica import ui_diagnostica

st.set_page_config(page_title="The Organism – Vision Manager", layout="wide")

st.sidebar.title("Vision Manager")
menu = st.sidebar.radio("Menu", [
    "Pazienti",
    "Valutazioni visive",
    "Refrazione / Prescrizione",
    "Diagnostica",
])

conn = get_conn()
init_db(conn)

if menu == "Pazienti":
    ui_pazienti(conn)
elif menu == "Valutazioni visive":
    ui_valutazioni_visive(conn)
elif menu == "Refrazione / Prescrizione":
    ui_refrazione_prescrizione(conn)
elif menu == "Diagnostica":
    ui_diagnostica(conn)

st.sidebar.caption("Backend: Neon (prod) / SQLite (dev)")
