import json
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from vision_manager.db import get_conn


def _inject_dashboard_css():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: #f6f8fb;
    }

    [data-testid="stHeader"] {
        background: rgba(0, 0, 0, 0);
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
        color: #1f2937 !important;
    }

    p, div, label, span {
        color: #111827;
    }

    .dashboard-card {
        background: white;
        border: 1px solid #e6ebf2;
        border-radius: 18px;
        padding: 18px 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        margin-bottom: 14px;
    }

    .dashboard-muted {
        color: #6b7280;
        font-size: 0.95rem;
    }

    .dashboard-patient {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)


def calcola_eta(data_nascita):
    if pd.isna(data_nascita) or not data_nascita:
        return None

    if isinstance(data_nascita, str):
        try:
            data_nascita = pd.to_datetime(data_nascita).date()
        except Exception:
            return None
    elif hasattr(data_nascita, "date"):
        try:
            data_nascita = data_nascita.date()
        except Exception:
            pass

    if not isinstance(data_nascita, date):
        return None

    oggi = date.today()
    return oggi.year - data_nascita.year - (
        (oggi.month, oggi.day) < (data_nascita.month, data_nascita.day)
    )


def _to_float(v):
    try:
        if v in (None, ""):
            return None
        return float(str(v).replace(",", "."))
    except Exception:
        return None


def ui_dashboard_paziente():
    _inject_dashboard_css()

    conn = get_conn()

    st.header("📊 Dashboard Paziente")

    query = """
    SELECT id, cognome, nome, data_nascita
    FROM pazienti
    ORDER BY cognome, nome
    """

    pazienti = pd.read_sql(query, conn)

    if pazienti.empty:
        st.warning("Nessun paziente nel database.")
        return

    pazienti["cognome"] = pazienti["cognome"].fillna("").astype(str)
    pazienti["nome"] = pazienti["nome"].fillna("").astype(str)
    pazienti["label"] = (pazienti["cognome"] + " " + pazienti["nome"]).str.strip()

    paziente_label = st.selectbox("Seleziona paziente", pazienti["label"])

    paziente = pazienti[pazienti["label"] == paziente_label].iloc[0]
    eta = calcola_eta(paziente["data_nascita"])

    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="dashboard-patient">👤 {paziente['label']}</div>
            <div class="dashboard-muted">
                Data nascita: {paziente['data_nascita']} &nbsp;&nbsp;|&nbsp;&nbsp; Età: {eta if eta is not None else "-"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    visite_query = """
    SELECT data_visita, dati_json
    FROM visite_visive
    WHERE paziente_id = %s
      AND COALESCE(is_deleted, 0) <> 1
    ORDER BY data_visita
    """

    visite = pd.read_sql(visite_query, conn, params=[paziente["id"]])

    if visite.empty:
        st.info("Nessuna visita disponibile.")
        return

    records = []

    for _, r in visite.iterrows():
        try:
            data_json = json.loads(r["dati_json"]) if isinstance(r["dati_json"], str) else r["dati_json"]
        except Exception:
            continue

        if not isinstance(data_json, dict):
            continue

        eo = data_json.get("esame_obiettivo", {}) or {}
        corr = data_json.get("correzione_finale", {}) or {}
        corr_od = corr.get("od", {}) or {}
        corr_os = corr.get("os", {}) or {}

        records.append(
            {
                "data": r["data_visita"],
                "iop_od": _to_float(eo.get("pressione_endoculare_od")),
                "iop_os": _to_float(eo.get("pressione_endoculare_os")),
                "pach_od": _to_float(eo.get("pachimetria_od")),
                "pach_os": _to_float(eo.get("pachimetria_os")),
                "sf_od": _to_float(corr_od.get("sf")),
                "sf_os": _to_float(corr_os.get("sf")),
            }
        )

    df = pd.DataFrame(records)

    if df.empty:
        st.info("Nessun dato clinico leggibile nelle visite.")
        return

    ultima = df.iloc[-1]

    st.subheader("📌 Ultimi valori")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IOP OD", "-" if pd.isna(ultima["iop_od"]) else f'{ultima["iop_od"]:.1f} mmHg')
    c2.metric("IOP OS", "-" if pd.isna(ultima["iop_os"]) else f'{ultima["iop_os"]:.1f} mmHg')
    c3.metric("Pachimetria OD", "-" if pd.isna(ultima["pach_od"]) else f'{ultima["pach_od"]:.0f} µm')
    c4.metric("Pachimetria OS", "-" if pd.isna(ultima["pach_os"]) else f'{ultima["pach_os"]:.0f} µm')

    st.divider()

    st.subheader("📈 Andamento IOP")
    fig = px.line(
        df,
        x="data",
        y=["iop_od", "iop_os"],
        markers=True,
        template="plotly_white",
        labels={"value": "mmHg", "data": "Data visita", "variable": "Parametro"},
    )
    fig.update_layout(
        legend_title_text="",
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.add_hline(y=21, line_dash="dash", line_width=1)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 Andamento pachimetria")
    fig2 = px.line(
        df,
        x="data",
        y=["pach_od", "pach_os"],
        markers=True,
        template="plotly_white",
        labels={"value": "µm", "data": "Data visita", "variable": "Parametro"},
    )
    fig2.update_layout(
        legend_title_text="",
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 Refrazione finale")
    fig3 = px.line(
        df,
        x="data",
        y=["sf_od", "sf_os"],
        markers=True,
        template="plotly_white",
        labels={"value": "Diottrie", "data": "Data visita", "variable": "Parametro"},
    )
    fig3.update_layout(
        legend_title_text="",
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    with st.expander("📚 Storico visite"):
        st.dataframe(df, use_container_width=True)
