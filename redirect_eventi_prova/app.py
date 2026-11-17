"""Vecchio indirizzo pnev-eventi-prova.streamlit.app: porta al nuovo pnev-iscrizioni.streamlit.app
mantenendo tutto quello che c'è dopo il «?», così i link già mandati continuano a funzionare.
Cartella a parte con il suo requirements.txt: non installa le librerie del gestionale."""
import html
import json
import urllib.parse

import streamlit as st

NUOVO = "https://pnev-iscrizioni.streamlit.app/"

st.set_page_config(page_title="Studio The Organism · PNEV", page_icon="➡️")
parametri = st.query_params.to_dict()
destinazione = NUOVO + ("?" + urllib.parse.urlencode(parametri) if parametri else "")

# reindirizzamento automatico (dove il browser lo consente) …
st.markdown(f'<meta http-equiv="refresh" content="0; url={html.escape(destinazione, quote=True)}">',
            unsafe_allow_html=True)
try:  # non tutte le versioni di Streamlit lo hanno: se manca, resta il pulsante
    import streamlit.components.v1 as components
    components.html(f"<script>try{{window.top.location.replace({json.dumps(destinazione)});}}catch(e){{}}</script>",
                    height=0)
except Exception:
    pass
# … e comunque un pulsante
st.title("La pagina si è spostata")
st.write("Ti stiamo portando al nuovo indirizzo. Se non succede, tocca il pulsante.")
st.link_button("Apri la pagina", destinazione, type="primary")
