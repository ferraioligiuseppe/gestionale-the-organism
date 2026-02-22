import streamlit as st

st.set_page_config(page_title="Vision Manager", layout="wide")

# Wrapper: avvia l'app principale (gestionale) dal root (app.py).
try:
    import app  # app.py in root del repo
except Exception as e:
    st.error("Impossibile importare app.py (gestionale).")
    st.exception(e)
    st.stop()

# Se nel tuo app.py esiste una funzione main(), la chiamiamo.
if hasattr(app, "main") and callable(app.main):
    app.main()
else:
    st.error("Nel file app.py non trovo una funzione main().")
    st.info("Dimmi come si chiama la funzione entrypoint (es. run(), start(), ecc.).")
