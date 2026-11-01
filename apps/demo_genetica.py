"""Demo autonoma del modulo Genetica PNEV (nessun database). Avvio: streamlit run apps/demo_genetica.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from modules.genetica.ui_genetica import render_genetica

st.set_page_config(page_title="Genetica PNEV · demo", page_icon="🧬", layout="wide")
render_genetica(None, paziente_id=0, paziente_nome="Paziente demo")
