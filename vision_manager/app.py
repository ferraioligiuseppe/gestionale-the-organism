import os
import sys
import streamlit as st

# Assicura che il root del repo sia nel PYTHONPATH (Streamlit Cloud spesso parte da /vision_manager)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from vision_manager.ui_visita_visiva import ui_visita_visiva

st.set_page_config(page_title="Vision Manager — Cirillo", layout="wide")
st.title("👁️ Vision Manager — Dr. Cirillo")
ui_visita_visiva()
PY
