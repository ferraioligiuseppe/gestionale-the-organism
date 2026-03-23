
import streamlit as st

def ui_lenti_contatto():
    st.title("👁️ Lenti a contatto")
    st.markdown("### Sistema unico LAC – The Organism (PNEV)")

    # --- Paziente (placeholder: integra con il tuo selector) ---
    st.subheader("Paziente")
    st.info("Collega qui il selector paziente del gestionale")

    tab_base, tab_toriche, tab_presb, tab_rgp, tab_orthok, tab_avanz, tab_storico = st.tabs([
        "Base (sferiche)",
        "Toriche",
        "Presbiopia",
        "RGP",
        "Ortho-K",
        "Avanzate",
        "Storico"
    ])

    # --- BASE ---
    with tab_base:
        st.markdown("### LAC morbide sferiche")
        sf = st.number_input("Sfera (D)", step=0.25, value=0.0)
        if st.button("Calcola lente base"):
            st.success(f"Lente suggerita: {sf:+.2f} D")

    # --- TORICHE ---
    with tab_toriche:
        st.markdown("### LAC toriche")
        sf = st.number_input("Sfera", key="t_sf")
        cyl = st.number_input("Cilindro", key="t_cyl")
        ax = st.number_input("Asse", min_value=0, max_value=180, key="t_ax")
        if st.button("Calcola torica"):
            st.success(f"SF {sf:+.2f} / CIL {cyl:+.2f} AX {ax}")

    # --- PRESBIOPIA ---
    with tab_presb:
        st.markdown("### Multifocale / Presbiopia")
        add = st.number_input("ADD", step=0.25)
        if st.button("Calcola multifocale"):
            st.success(f"ADD consigliata: {add:+.2f}")

    # --- RGP ---
    with tab_rgp:
        st.markdown("### Lenti RGP")
        k = st.number_input("K medio (mm)", value=7.8)
        if st.button("Calcola RGP"):
            st.success(f"Raggio base suggerito: {k:.2f} mm")

    # --- ORTHO-K ---
    with tab_orthok:
        st.markdown("### Ortho-K / Inverse")
        myo = st.number_input("Miopia da ridurre", step=0.25)
        if st.button("Calcola Ortho-K"):
            st.success(f"Riduzione target: {myo:+.2f} D")

    # --- AVANZATE ---
    with tab_avanz:
        st.markdown("### LAC su misura (avanzate)")
        st.info("Qui integreremo Toffoli / Calossi / ESA in modo unificato")

    # --- STORICO ---
    with tab_storico:
        st.markdown("### Storico LAC")
        st.info("Collega qui il database unificato")
