import streamlit as st


def render_dashboard():
    st.title("The Organism")
    st.caption("Dashboard clinica e operativa")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pazienti attivi", 0)
    col2.metric("Sedute oggi", 0)
    col3.metric("Relazioni da completare", 0)
    col4.metric("Protocolli uditivi attivi", 0)

    st.markdown("---")
    st.subheader("Accesso rapido")

    q1, q2, q3, q4 = st.columns(4)
    q1.button("Pazienti", use_container_width=True)
    q2.button("Anamnesi", use_container_width=True)
    q3.button("Stimolazione uditiva", use_container_width=True)
    q4.button("Vision Manager", use_container_width=True)

    st.info("Prima versione dashboard integrata correttamente nel gestionale.")
