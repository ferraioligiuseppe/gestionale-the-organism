import os
import sys
import streamlit as st

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from vision_manager.ui_visita_visiva import ui_visita_visiva  # ✅ NOME GIUSTO

st.set_page_config(page_title="Vision Manager — Dr. Cirillo", layout="wide")
st.title("👁️ Vision Manager — Dr. Cirillo")
ui_visita_visiva()
