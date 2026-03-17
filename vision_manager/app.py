import os
import sys
import streamlit as st

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from vision_manager.ui_visita_visiva_v2 import ui_visita_visiva
    from vision_manager.ui_dashboard_paziente import ui_dashboard_paziente
    from vision_manager.db import get_conn, init_db
except ModuleNotFoundError:
    from ui_visita_visiva_v2 import ui_visita_visiva
    from ui_dashboard_paziente import ui_dashboard_paziente
    from db import get_conn, init_db

st.set_page_config(page_title="Vision Manager — Dr. Cirillo", layout="wide")

st.sidebar.title("Vision Manager")
pagina = st.sidebar.radio("Navigazione", ["Dashboard paziente", "Visita visiva"])

try:
    conn = get_conn()
    init_db(conn)
except Exception as e:
    st.error(f"Errore inizializzazione database Vision Manager: {e}")
    st.stop()
finally:
    try:
        conn.close()
    except Exception:
        pass

st.title("👁️ Vision Manager — Dr. Cirillo")

if pagina == "Dashboard paziente":
    ui_dashboard_paziente()
elif pagina == "Visita visiva":
    ui_visita_visiva()
