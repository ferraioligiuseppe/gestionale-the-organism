import streamlit as st
from vision_manager.ui_visita_visiva import ui_visita_visiva

st.set_page_config(page_title="Vision Manager — Cirillo", layout="wide")
st.title("👁️ Vision Manager — Dr. Cirillo")
ui_visita_visiva()
