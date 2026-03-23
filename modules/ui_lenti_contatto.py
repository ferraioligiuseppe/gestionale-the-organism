
import streamlit as st

def ui_lenti_contatto():
    st.title("👁️ Lenti a contatto")
    st.markdown("### Modulo unico LAC – PNEV")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Ortho-K / Inverse",
        "Calcolo Toffoli",
        "ESA Ortho-6",
        "Morbide / Toriche / Presbiopia",
        "Avanzate (Calossi)",
        "Fluoresceina"
    ])

    with tab1:
        from modules.ui_lenti_inverse import ui_lenti_inverse
        ui_lenti_inverse()

    with tab2:
        from modules.ui_calcolatore_lac import ui_calcolatore_lac
        ui_calcolatore_lac()

    with tab3:
        from modules.ui_esa_ortho6 import ui_esa_ortho6
        ui_esa_ortho6()

    with tab4:
        from modules.ui_lac_ametropie import ui_lac_ametropie
        ui_lac_ametropie()

    with tab5:
        from modules.ui_calcolatore_lac_plus import ui_calcolatore_lac_plus
        ui_calcolatore_lac_plus()

    with tab6:
        from modules.ui_fluorescein import ui_fluorescein_simulator
        ui_fluorescein_simulator()
