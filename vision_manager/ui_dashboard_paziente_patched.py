import json
from datetime import date
from collections.abc import Mapping

import matplotlib.pyplot as plt
import pandas as pd
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
        color: #111827 !important;
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
        color: #6b7280 !important;
        font-size: 0.95rem;
    }

    .dashboard-patient {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a !important;
        margin-bottom: 4px;
    }

    /* Selectbox chiaro */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #dbe3ee !important;
        border-radius: 12px !important;
    }

    div[data-baseweb="select"] span {
        color: #111827 !important;
    }

    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
        color: #111827 !important;
    }

    div[role="listbox"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #dbe3ee !important;
    }

    div[role="option"] {
        background-color: #ffffff !important;
        color: #111827 !important;
    }

    div[role="option"]:hover {
        background-color: #eef4fb !important;
        color: #111827 !important;
    }

    /* Input chiari */
    input, textarea {
        background-color: #ffffff !important;
        color: #111827 !important;
    }

    .stTextInput > div > div > input,
    .stDateInput input,
    .stNumberInput input {
        background-color: #ffffff !important;
        color: #111827 !important;
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


def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def _ph(conn) -> str:
    return "%s" if _is_pg(conn) else "?"


def _dict_row(cur, row):
    if isinstance(row, Mapping):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _list_pazienti_dashboard(conn):
    # Se una query precedente ha mandato la transazione in errore,
    # su PostgreSQL bisogna fare rollback prima di eseguire nuove query.
    if _is_pg(conn):
        try:
            conn.rollback()
        except Exception:
            pass

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, cognome, nome, data_nascita
            FROM pazienti
            ORDER BY cognome, nome
            """
        )
        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _list_visite_dashboard(conn, paziente_id: int):
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        try:
            cur.execute(
                f"""
                SELECT id, data_visita, dati_json, is_deleted, deleted_at
                FROM visite_visive
                WHERE paziente_id={ph} AND COALESCE(is_deleted, FALSE) = FALSE
                ORDER BY data_visita ASC, id ASC
                """,
                (paziente_id,),
            )
        except Exception:
            if _is_pg(conn):
                try:
                    conn.rollback()
                except Exception:
                    pass

            cur.execute(
                f"""
                SELECT id, data_visita, dati_json
                FROM visite_visive
                WHERE paziente_id={ph}
                ORDER BY data_visita ASC, id ASC
                """,
                (paziente_id,),
            )

        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _safe_json(raw):
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None


def _make_line_chart(df, xcol, ycols, title, ylabel, threshold=None):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for col in ycols:
        if col in df.columns:
            ax.plot(df[xcol], df[col], marker="o", label=col.replace("_", " ").upper())
    if threshold is not None:
        ax.axhline(threshold, linestyle="--", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel("Data visita")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    return fig


def ui_dashboard_paziente():
    _inject_dashboard_css()

    conn = get_conn()

    st.header("📊 Dashboard Paziente")

    pazienti = _list_pazienti_dashboard(conn)

    if not pazienti:
        st.warning("Nessun paziente nel database.")
        return

    pazienti_df = pd.DataFrame(pazienti)
    pazienti_df["cognome"] = pazienti_df["cognome"].fillna("").astype(str)
    pazienti_df["nome"] = pazienti_df["nome"].fillna("").astype(str)
    pazienti_df["label"] = (pazienti_df["cognome"] + " " + pazienti_df["nome"]).str.strip()

    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    paziente_label = st.selectbox("Seleziona paziente", pazienti_df["label"].tolist())
    st.markdown('</div>', unsafe_allow_html=True)

    paziente = pazienti_df[pazienti_df["label"] == paziente_label].iloc[0]
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

    visite = _list_visite_dashboard(conn, int(paziente["id"]))

    if not visite:
        st.info("Nessuna visita disponibile.")
        return

    records = []
    latest_payload = None

    for r in visite:
        data_json = _safe_json(r.get("dati_json"))
        if not isinstance(data_json, dict):
            continue

        latest_payload = data_json
        eo = data_json.get("esame_obiettivo", {}) or {}
        corr = data_json.get("correzione_finale", {}) or {}
        corr_od = corr.get("od", {}) or {}
        corr_os = corr.get("os", {}) or {}

        records.append(
            {
                "data": pd.to_datetime(r.get("data_visita"), errors="coerce"),
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

    df = df.sort_values("data").reset_index(drop=True)
    ultima = df.iloc[-1]

    st.subheader("📌 Ultimi valori")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IOP OD", "-" if pd.isna(ultima["iop_od"]) else f'{ultima["iop_od"]:.1f} mmHg')
    c2.metric("IOP OS", "-" if pd.isna(ultima["iop_os"]) else f'{ultima["iop_os"]:.1f} mmHg')
    c3.metric("Pachimetria OD", "-" if pd.isna(ultima["pach_od"]) else f'{ultima["pach_od"]:.0f} µm')
    c4.metric("Pachimetria OS", "-" if pd.isna(ultima["pach_os"]) else f'{ultima["pach_os"]:.0f} µm')

    st.divider()

    st.subheader("📈 Andamento IOP")
    fig_iop = _make_line_chart(df, "data", ["iop_od", "iop_os"], "Andamento IOP", "mmHg", threshold=21)
    st.pyplot(fig_iop, clear_figure=True)

    st.subheader("📈 Andamento pachimetria")
    fig_pach = _make_line_chart(df, "data", ["pach_od", "pach_os"], "Andamento pachimetria", "µm")
    st.pyplot(fig_pach, clear_figure=True)

    st.subheader("📈 Refrazione finale")
    fig_ref = _make_line_chart(df, "data", ["sf_od", "sf_os"], "Refrazione finale", "Diottrie")
    st.pyplot(fig_ref, clear_figure=True)

    if isinstance(latest_payload, dict):
        st.divider()
        c_left, c_right = st.columns(2)

        with c_left:
            st.subheader("🩺 Ultima visita")
            st.write("**Anamnesi:**", latest_payload.get("anamnesi", "") or "-")
            eo = latest_payload.get("esame_obiettivo", {}) or {}
            fields = {
                "Congiuntiva": eo.get("congiuntiva"),
                "Cornea": eo.get("cornea"),
                "Camera anteriore": eo.get("camera_anteriore"),
                "Cristallino": eo.get("cristallino"),
                "Vitreo": eo.get("vitreo"),
                "Fondo oculare": eo.get("fondo_oculare"),
            }
            shown = False
            for k, v in fields.items():
                if v not in (None, ""):
                    shown = True
                    st.write(f"**{k}:** {v}")
            if not shown:
                st.write("-")

        with c_right:
            st.subheader("👓 Ultima prescrizione")
            prescr = latest_payload.get("prescrizione", {}) or {}
            if prescr:
                for dist in ["lontano", "intermedio", "vicino"]:
                    blocco = prescr.get(dist, {}) or {}
                    if blocco:
                        st.write(f"**{dist.capitalize()}**")
                        st.write(
                            f"OD: {blocco.get('od', {})}  |  OS: {blocco.get('os', {})}"
                        )
                lenti = prescr.get("lenti", []) or []
                if lenti:
                    st.write("**Lenti:**", ", ".join(map(str, lenti)))
            else:
                st.write("-")

    st.divider()

    with st.expander("📚 Storico visite"):
        show_df = df.copy()
        if "data" in show_df.columns:
            show_df["data"] = show_df["data"].dt.strftime("%Y-%m-%d")
        st.dataframe(show_df, use_container_width=True)
