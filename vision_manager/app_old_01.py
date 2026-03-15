import os
import sys
import streamlit as st

# assicura che il repo root sia nel path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# moduli Vision Manager
from vision_manager.ui_visita_visiva_v2 import ui_visita_visiva
from vision_manager.ui_dashboard_paziente import ui_dashboard_paziente


# configurazione pagina
st.set_page_config(
    page_title="Vision Manager — Dr. Cirillo",
    layout="wide",
)

# sidebar
st.sidebar.title("Vision Manager")

pagina = st.sidebar.radio(
    "Navigazione",
    [
        "Dashboard paziente",
        "Visita visiva",
    ],
)

# header principale
st.title("👁️ Vision Manager — Dr. Cirillo")

# routing pagine
if pagina == "Dashboard paziente":
    ui_dashboard_paziente()

elif pagina == "Visita visiva":
    ui_visita_visiva()
