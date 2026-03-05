from __future__ import annotations
import streamlit as st
from vision_manager.ui_kit import inject_ui, topbar, card_open, card_close, badge, callout

def ui_demo_visiva():
    inject_ui("assets/ui.css")
    topbar("Vision Manager", "Visita visiva • UI The Organism", right="Dr. Cirillo")
    badge("Paziente: Mario Rossi • 48 anni")

    card_open("Pressione Endoculare (IOP)", "Inserisci OD/OS e metodo tonometria", icon="👁️")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("IOP OD (mmHg)", min_value=0.0, max_value=60.0, step=0.5, key="iop_od")
    with c2:
        st.number_input("IOP OS (mmHg)", min_value=0.0, max_value=60.0, step=0.5, key="iop_os")
    st.radio("Metodo tonometria", ["Goldmann", "Air Puff", "Icare", "Perkins"], horizontal=True, key="tono_metodo")
    card_close()

    card_open("Pachimetria corneale", "Spessore corneale (µm)", icon="📏")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input("Pachimetria OD (µm)", min_value=300, max_value=800, step=1, key="cct_od")
    with c2:
        st.number_input("Pachimetria OS (µm)", min_value=300, max_value=800, step=1, key="cct_os")
    card_close()

    callout("Screening clinico indicativo (non diagnostico).", variant="warn")
