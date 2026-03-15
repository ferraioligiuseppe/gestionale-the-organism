import os
import sys
import streamlit as st

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from vision_manager.ui_visita_visiva_v2 import ui_visita_visiva

try:
    from vision_manager.ui_dashboard_paziente import ui_dashboard_paziente
    DASHBOARD_AVAILABLE = True
except Exception:
    DASHBOARD_AVAILABLE = False


st.set_page_config(page_title="Vision Manager — Dr. Cirillo", layout="wide")

st.sidebar.title("Vision Manager")

pages = ["Visita visiva"]
if DASHBOARD_AVAILABLE:
    pages.append("Dashboard paziente")

pagina = st.sidebar.radio("Navigazione", pages)

st.title("👁️ Vision Manager — Dr. Cirillo")

if pagina == "Visita visiva":
    ui_visita_visiva()

elif pagina == "Dashboard paziente" and DASHBOARD_AVAILABLE:
    ui_dashboard_paziente()
