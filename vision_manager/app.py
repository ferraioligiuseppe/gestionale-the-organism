import os
import subprocess
import streamlit as st

st.set_page_config(page_title="Vision Manager — DEBUG", layout="wide")
st.title("Vision Manager — DEBUG deploy")

# mostra commit realmente deployato
try:
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
except Exception as e:
    sha = f"git non disponibile: {e}"
st.write("Commit deployato:", sha)

# lista file nella cartella vision_manager
st.write("File in vision_manager/:")
try:
    st.code("\n".join(sorted(os.listdir("vision_manager"))))
except Exception as e:
    st.error(e)

# mostra le prime 60 righe del file incriminato (SENZA importarlo)
p = os.path.join("vision_manager", "ui_visita_visiva.py")
st.write("Prime righe di vision_manager/ui_visita_visiva.py (deploy):")
try:
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    st.code("".join(lines[:60]))
except Exception as e:
    st.error(e)
