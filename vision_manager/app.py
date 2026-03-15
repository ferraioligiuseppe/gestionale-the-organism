import os
import sys
import streamlit as st

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from vision_manager.ui_visita_visiva_v2 import ui_visita_visiva
from vision_manager.ui_dashboard_paziente import ui_dashboard_paziente

st.set_page_config(page_title="Vision Manager — Dr. Cirillo", layout="wide")

st.sidebar.title("Vision Manager")

pagina = st.sidebar.radio(
    "Navigazione",
    ["Visita visiva", "Dashboard paziente"]
)

st.title("👁️ Vision Manager — Dr. Cirillo")

if pagina == "Visita visiva":
    ui_visita_visiva()
elif pagina == "Dashboard paziente":
    ui_dashboard_paziente()
