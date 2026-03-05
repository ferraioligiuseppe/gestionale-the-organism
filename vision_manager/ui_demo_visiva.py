from __future__ import annotations
import streamlit as st
import pandas as pd
from vision_manager.ui_kit import inject_ui, topbar, card_open, card_close, badge, callout, cta_button

def ui_demo_visiva():
    st.set_page_config(page_title="Vision Manager • UI demo", layout="wide")
    inject_ui("assets/ui.css")

    with st.sidebar:
        st.markdown("### The Organism")
        st.caption("Navigation (demo)")
        st.button("👤 Pazienti")
        st.button("👁️ Visione")
        st.button("👂 Udito")
        st.button("🧠 Sviluppo")
        st.markdown("---")
        cta_button("＋ Nuova Visita", key="new_visit", use_container_width=True)

    topbar("Vision Manager", "Visita visiva • UI The Organism", right="Dr. Cirillo")

    badge("Paziente: Mario Rossi • 48 anni")

    t1, t2 = st.tabs(["Visita attuale", "Storico visite"])

    with t1:
        card_open("Acuità visiva", "Naturale / Abituale / Corretta", icon="👁️")
        a1, a2, a3 = st.columns(3)
        a1.selectbox("OD (corretta)", ["10/10","9/10","8/10"], index=0)
        a2.selectbox("OS (corretta)", ["10/10","9/10","8/10"], index=0)
        a3.selectbox("OO (corretta)", ["10/10","9/10","8/10"], index=0)
        card_close()

        card_open("Pressione endoculare (IOP)", "OD/OS e metodo tonometria", icon="🧿")
        c1, c2 = st.columns(2)
        c1.number_input("IOP OD (mmHg)", min_value=0.0, max_value=60.0, step=0.5, value=16.0)
        c2.number_input("IOP OS (mmHg)", min_value=0.0, max_value=60.0, step=0.5, value=15.0)
        st.radio("Metodo tonometria", ["Goldmann","Air Puff","Icare","Perkins"], horizontal=True, index=0)
        card_close()

        card_open("Pachimetria corneale", "Spessore corneale (µm)", icon="📏")
        c1, c2 = st.columns(2)
        c1.number_input("Pachimetria OD (µm)", min_value=300, max_value=800, step=1, value=520)
        c2.number_input("Pachimetria OS (µm)", min_value=300, max_value=800, step=1, value=505)
        card_close()

        callout("Screening clinico indicativo (non diagnostico).", variant="warn")

        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            cta_button("💾 Salva visita", key="save", use_container_width=True)
        with c2:
            st.button("🧾 PDF Referto", use_container_width=True)
        with c3:
            st.button("👓 PDF Prescrizione", use_container_width=True)

    with t2:
        card_open("Andamento IOP (OD/OS) nel tempo", "Linea tratteggiata: soglia 21 mmHg", icon="📈")
        df = pd.DataFrame({
            "Data": pd.to_datetime(["2024-04-03","2024-04-20","2024-04-25"]),
            "IOP_OD":[16,18,21],
            "IOP_OS":[15,17,19],
        }).set_index("Data")
        st.line_chart(df)
        card_close()

        card_open("Visite", "Elenco visite con azioni rapide", icon="🗓️")
        st.dataframe(
            pd.DataFrame([
                {"Data":"2024-04-25","IOP":"21/19","CCT":"520/505","Stato":"Completa"},
                {"Data":"2024-04-20","IOP":"18/17","CCT":"520/505","Stato":"Completa"},
                {"Data":"2024-04-03","IOP":"16/15","CCT":"520/505","Stato":"Completa"},
            ]),
            use_container_width=True,
            hide_index=True,
        )
        card_close()
