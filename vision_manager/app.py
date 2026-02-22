import os
import subprocess
import traceback
import py_compile
import streamlit as st

st.set_page_config(page_title="Vision Manager — DEBUG", layout="wide")
st.title("Vision Manager — DEBUG deploy")

# commit realmente deployato
try:
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
except Exception as e:
    sha = f"git non disponibile: {e}"
st.write("Commit deployato:", sha)

st.write("File in vision_manager/:")
st.code("\n".join(sorted(os.listdir("vision_manager"))))

p = os.path.join("vision_manager", "ui_visita_visiva.py")
st.write("Compilo ui_visita_visiva.py (per trovare riga IndentationError)...")

try:
    py_compile.compile(p, doraise=True)
    st.success("OK ✅ Nessun IndentationError: il file compila correttamente su Streamlit Cloud.")
except Exception as e:
    st.error("ERRORE durante compile:")
    st.code(traceback.format_exc())

# Mostra un pezzo ampio del file per ispezione (prime 250 righe)
st.write("Prime 250 righe del file (deploy):")
try:
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    st.code("".join(lines[:250]))
except Exception as e:
    st.error(e)
