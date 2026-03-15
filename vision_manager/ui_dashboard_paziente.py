import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from vision_manager.db import get_conn
import streamlit as st

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: #f6f8fb;
}
[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
}
[data-testid="stSidebar"] {
    background: #ffffff;
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e6ebf2;
    border-radius: 16px;
    padding: 14px 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
h1, h2, h3 {
    color: #1f2937;
}
p, div, label, span {
    color: #111827;
}
</style>
""", unsafe_allow_html=True)

def calcola_eta(data_nascita):
    if not data_nascita:
        return None
    oggi = date.today()
    return oggi.year - data_nascita.year - (
        (oggi.month, oggi.day) < (data_nascita.month, data_nascita.day)
    )


def ui_dashboard_paziente():

    conn = get_conn()

    st.header("📊 Dashboard Paziente")

    # -----------------------------
    # SELEZIONE PAZIENTE
    # -----------------------------

    query = """
    SELECT id, cognome, nome, data_nascita
    FROM pazienti
    ORDER BY cognome, nome
    """

    pazienti = pd.read_sql(query, conn)

    if pazienti.empty:
        st.warning("Nessun paziente nel database.")
        return

    pazienti["label"] = pazienti["cognome"] + " " + pazienti["nome"]

    paziente_label = st.selectbox(
        "Seleziona paziente",
        pazienti["label"]
    )

    paziente = pazienti[pazienti["label"] == paziente_label].iloc[0]

    eta = calcola_eta(paziente["data_nascita"])

    # -----------------------------
    # HEADER PAZIENTE
    # -----------------------------

    st.subheader(f"👤 {paziente['label']}")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Data nascita:**", paziente["data_nascita"])

    with col2:
        st.write("**Età:**", eta)

    st.divider()

    # -----------------------------
    # RECUPERO VISITE
    # -----------------------------

    visite_query = """
    SELECT data_visita, dati_json
    FROM visite_visive
    WHERE paziente_id = %s
    ORDER BY data_visita
    """

    visite = pd.read_sql(visite_query, conn, params=[paziente["id"]])

    if visite.empty:
        st.info("Nessuna visita disponibile.")
        return

    # parsing json
    import json

    records = []

    for _, r in visite.iterrows():

        try:
            data = json.loads(r["dati_json"])
        except:
            continue

        eo = data.get("esame_obiettivo", {})
        corr = data.get("correzione_finale", {})

        records.append(
            {
                "data": r["data_visita"],
                "iop_od": eo.get("pressione_endoculare_od"),
                "iop_os": eo.get("pressione_endoculare_os"),
                "pach_od": eo.get("pachimetria_od"),
                "pach_os": eo.get("pachimetria_os"),
                "sf_od": corr.get("od", {}).get("sf"),
                "sf_os": corr.get("os", {}).get("sf"),
            }
        )

    df = pd.DataFrame(records)

    # -----------------------------
    # CARD CLINICHE
    # -----------------------------

    ultima = df.iloc[-1]

    st.subheader("📌 Ultimi valori")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("IOP OD", ultima["iop_od"])
    c2.metric("IOP OS", ultima["iop_os"])
    c3.metric("Pachimetria OD", ultima["pach_od"])
    c4.metric("Pachimetria OS", ultima["pach_os"])

    st.divider()

    # -----------------------------
    # GRAFICO IOP
    # -----------------------------

    st.subheader("📈 Andamento IOP")

    fig = px.line(
        df,
        x="data",
        y=["iop_od", "iop_os"],
        markers=True,
    )

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # GRAFICO PACHIMETRIA
    # -----------------------------

    st.subheader("📈 Andamento pachimetria")

    fig2 = px.line(
        df,
        x="data",
        y=["pach_od", "pach_os"],
        markers=True,
    )

    st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------
    # GRAFICO REFRAZIONE
    # -----------------------------

    st.subheader("📈 Refrazione finale")

    fig3 = px.line(
        df,
        x="data",
        y=["sf_od", "sf_os"],
        markers=True,
    )

    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # -----------------------------
    # STORICO VISITE
    # -----------------------------

    with st.expander("📚 Storico visite"):

        st.dataframe(df)
