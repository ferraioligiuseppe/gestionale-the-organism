
import streamlit as st
from db import get_conn, init_db
from ui_pazienti import ui_pazienti
from ui_refrazione_prescrizione import ui_refrazione_prescrizione

st.set_page_config(page_title="The Organism – Vision Manager", layout="wide")

st.sidebar.title("Vision Manager")
menu = st.sidebar.radio("Menu", [
    "Pazienti",
    "Refrazione / Prescrizione"
])

conn = get_conn()
init_db(conn)

if menu == "Pazienti":
    ui_pazienti(conn)
elif menu == "Refrazione / Prescrizione":
    ui_refrazione_prescrizione(conn)

st.sidebar.caption("Backend: Neon (prod) / SQLite (dev)")
