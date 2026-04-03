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
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main, .block-container {
        background: #f0f4f8 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }

    /* Tutti i testi area principale */
    [data-testid="stMain"] p,
    [data-testid="stMain"] span,
    [data-testid="stMain"] label,
    [data-testid="stMain"] div,
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] small {
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
    }

    /* Input, textarea */
    input, textarea,
    [data-testid="stTextInput"] input,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea {
        background: #ffffff !important;
        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    /* Selectbox */
    [data-baseweb="select"] > div { background:#ffffff !important; border:1.5px solid #cbd5e1 !important; border-radius:8px !important; }
    [data-baseweb="select"] span,
    [data-baseweb="select"] div,
    [data-baseweb="select"] p { color:#1e293b !important; -webkit-text-fill-color:#1e293b !important; }
    [data-baseweb="popover"] *, [role="listbox"] * { background:#ffffff !important; color:#1e293b !important; -webkit-text-fill-color:#1e293b !important; }
    [role="option"]:hover { background:#eff6ff !important; }

    /* Labels */
    .stSelectbox label, [data-testid="stWidgetLabel"] {
        color: #475569 !important; -webkit-text-fill-color: #475569 !important;
        font-size: 0.85rem !important; font-weight: 500 !important;
    }

    /* Caption */
    .stCaption, small, [data-testid="stCaptionContainer"] p {
        color: #64748b !important; -webkit-text-fill-color: #64748b !important;
    }

    /* Metriche */
    [data-testid="stMetric"] { background:#ffffff !important; border:1px solid #e2e8f0 !important; border-radius:12px !important; padding:14px 16px !important; }
    [data-testid="stMetricLabel"] div, [data-testid="stMetricLabel"] p { color:#64748b !important; -webkit-text-fill-color:#64748b !important; font-size:0.8rem !important; }
    [data-testid="stMetricValue"] div, [data-testid="stMetricValue"] p { color:#1e293b !important; -webkit-text-fill-color:#1e293b !important; font-weight:600 !important; }

    /* Expander */
    [data-testid="stExpander"] { background:#ffffff !important; border:1px solid #e2e8f0 !important; border-radius:12px !important; }
    [data-testid="stExpander"] summary span, [data-testid="stExpander"] summary p { color:#334155 !important; -webkit-text-fill-color:#334155 !important; }

    hr { border-color:#e2e8f0 !important; margin:20px 0 !important; }

    /* Sidebar */
    [data-testid="stSidebar"] { background:#0f1923 !important; border-right:1px solid #1e2d3d; }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] label { color:#c8d6e5 !important; -webkit-text-fill-color:#c8d6e5 !important; }
    [data-testid="stSidebar"] h2 { color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; font-size:1rem !important; }

    /* Componenti custom */
    .vm-patient-header { background:linear-gradient(135deg,#1e3a5f 0%,#2563a8 100%); border-radius:16px; padding:20px 28px; margin-bottom:20px; }
    .vm-patient-name   { font-size:1.5rem; font-weight:600; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; }
    .vm-patient-meta   { font-size:0.85rem; color:#a8c4e0 !important; -webkit-text-fill-color:#a8c4e0 !important; margin-top:4px; font-family:'DM Mono',monospace; }
    .vm-section-title  { font-size:0.72rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#64748b !important; -webkit-text-fill-color:#64748b !important; margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid #e2e8f0; }
    .vm-card           { background:#ffffff; border-radius:14px; border:1px solid #e2e8f0; padding:18px 22px; margin-bottom:14px; box-shadow:0 1px 4px rgba(0,0,0,0.05); }
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
            WHERE COALESCE(stato_paziente, 'ATTIVO') = 'ATTIVO'
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
                WHERE paziente_id={ph} AND COALESCE(is_deleted,0)=0
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



def _fmt_val(v, fallback="-"):
    if v is None or (isinstance(v, float) and __import__("math").isnan(v)):
        return fallback
    s = str(v).strip()
    return s if s else fallback


def ui_dashboard_paziente():
    # ── CSS stesso tema di ui_visita_visiva_v2 ────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background: #f0f4f8 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] {
        background: #0f1923 !important;
        border-right: 1px solid #1e2d3d;
    }
    [data-testid="stSidebar"] * { color: #c8d6e5 !important; }
    [data-testid="stSidebar"] h2 { color: #ffffff !important; font-size:1rem !important; }

    .vm-patient-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2563a8 100%);
        border-radius: 16px;
        padding: 20px 28px;
        margin-bottom: 20px;
    }
    .vm-patient-name { font-size:1.5rem; font-weight:600; color:#ffffff !important; }
    .vm-patient-meta { font-size:0.85rem; color:#a8c4e0 !important; margin-top:4px; font-family:'DM Mono',monospace; }
    .vm-section-title {
        font-size:0.72rem; font-weight:600; letter-spacing:0.08em;
        text-transform:uppercase; color:#64748b !important;
        margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid #e2e8f0;
    }
    .vm-card {
        background:#ffffff; border-radius:14px; border:1px solid #e2e8f0;
        padding:18px 22px; margin-bottom:14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] {
        background:#ffffff !important; border:1px solid #e2e8f0 !important;
        border-radius:12px !important; padding:14px 16px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    }
    [data-testid="stMetricLabel"] { color:#64748b !important; font-size:0.8rem !important; }
    [data-testid="stMetricValue"] { color:#1e293b !important; font-weight:600 !important; }
    hr { border-color:#e2e8f0 !important; margin:20px 0 !important; }

    div[data-baseweb="select"] > div {
        background:#ffffff !important; color:#1e293b !important;
        border:1.5px solid #e2e8f0 !important; border-radius:10px !important;
    }
    div[data-baseweb="select"] span { color:#1e293b !important; }
    div[role="listbox"] { background:#ffffff !important; color:#1e293b !important; }
    div[role="option"] { background:#ffffff !important; color:#1e293b !important; }
    div[role="option"]:hover { background:#eef4fb !important; }
    </style>
    """, unsafe_allow_html=True)

    conn = get_conn()

    pazienti = _list_pazienti_dashboard(conn)
    if not pazienti:
        st.warning("Nessun paziente nel database.")
        return

    pazienti_df = pd.DataFrame(pazienti)
    pazienti_df["cognome"] = pazienti_df["cognome"].fillna("").astype(str).str.title()
    pazienti_df["nome"]    = pazienti_df["nome"].fillna("").astype(str).str.title()
    pazienti_df["label"]   = (pazienti_df["cognome"] + " " + pazienti_df["nome"]).str.strip()

    # ── Titolo ────────────────────────────────────────────────
    st.markdown("## 📊 Dashboard Paziente")

    # ── Selettore paziente ────────────────────────────────────
    paziente_label = st.selectbox("Seleziona paziente", pazienti_df["label"].tolist())
    paziente = pazienti_df[pazienti_df["label"] == paziente_label].iloc[0]
    eta = calcola_eta(paziente["data_nascita"])

    dn_fmt = ""
    if paziente["data_nascita"]:
        try:
            dn_fmt = pd.to_datetime(paziente["data_nascita"]).strftime("%d/%m/%Y")
        except Exception:
            dn_fmt = str(paziente["data_nascita"])

    # ── Header paziente ───────────────────────────────────────
    st.markdown(f"""
    <div class="vm-patient-header">
        <div class="vm-patient-name">👤 {paziente['label']}</div>
        <div class="vm-patient-meta">
            {'Nato/a il ' + dn_fmt if dn_fmt else ''}
            {'&nbsp;·&nbsp;' + str(eta) + ' anni' if eta is not None else ''}
        </div>
    </div>
    """, unsafe_allow_html=True)

    visite = _list_visite_dashboard(conn, int(paziente["id"]))
    if not visite:
        st.info("Nessuna visita registrata per questo paziente.")
        return

    records = []
    latest_payload = None
    for r in visite:
        data_json = _safe_json(r.get("dati_json"))
        if not isinstance(data_json, dict):
            continue
        latest_payload = data_json
        eo      = data_json.get("esame_obiettivo", {}) or {}
        corr    = data_json.get("correzione_finale", {}) or {}
        corr_od = corr.get("od", {}) or {}
        corr_os = corr.get("os", {}) or {}
        records.append({
            "data":    pd.to_datetime(r.get("data_visita"), errors="coerce"),
            "iop_od":  _to_float(eo.get("pressione_endoculare_od")),
            "iop_os":  _to_float(eo.get("pressione_endoculare_os")),
            "pach_od": _to_float(eo.get("pachimetria_od")),
            "pach_os": _to_float(eo.get("pachimetria_os")),
            "sf_od":   _to_float(corr_od.get("sf")),
            "sf_os":   _to_float(corr_os.get("sf")),
        })

    df = pd.DataFrame(records)
    if df.empty:
        st.info("Nessun dato clinico leggibile.")
        return

    df = df.sort_values("data").reset_index(drop=True)
    ultima = df.iloc[-1]

    # ── Ultimi valori ─────────────────────────────────────────
    st.markdown('<div class="vm-section-title">Ultimi valori</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IOP OD",         "-" if pd.isna(ultima["iop_od"])  else f'{ultima["iop_od"]:.1f} mmHg')
    c2.metric("IOP OS",         "-" if pd.isna(ultima["iop_os"])  else f'{ultima["iop_os"]:.1f} mmHg')
    c3.metric("Pachimetria OD", "-" if pd.isna(ultima["pach_od"]) else f'{ultima["pach_od"]:.0f} µm')
    c4.metric("Pachimetria OS", "-" if pd.isna(ultima["pach_os"]) else f'{ultima["pach_os"]:.0f} µm')

    st.divider()

    # ── Grafici ───────────────────────────────────────────────
    def _chart(df, ycols, title, ylabel, threshold=None):
        fig, ax = plt.subplots(figsize=(8, 3))
        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#f8fafc")
        colors = ["#2563a8", "#0ea5e9", "#7c3aed", "#0d9488"]
        for i, col in enumerate(ycols):
            if col in df.columns:
                ax.plot(df["data"], df[col], marker="o", label=col.upper().replace("_"," "),
                        color=colors[i % len(colors)], linewidth=2)
        if threshold is not None:
            ax.axhline(threshold, linestyle="--", linewidth=1, color="#ef4444", alpha=0.6,
                       label=f"Soglia {threshold}")
        ax.set_ylabel(ylabel); ax.legend(fontsize=9)
        ax.grid(True, alpha=0.15, color="#cbd5e1")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e2e8f0"); ax.spines["bottom"].set_color("#e2e8f0")
        fig.autofmt_xdate()
        return fig

    st.markdown('<div class="vm-section-title">Andamento IOP</div>', unsafe_allow_html=True)
    if df[["iop_od","iop_os"]].notna().any().any():
        st.pyplot(_chart(df, ["iop_od","iop_os"], "IOP", "mmHg", threshold=21), clear_figure=True)
    else:
        st.caption("Nessun dato IOP disponibile.")

    st.markdown('<div class="vm-section-title">Andamento Pachimetria</div>', unsafe_allow_html=True)
    if df[["pach_od","pach_os"]].notna().any().any():
        st.pyplot(_chart(df, ["pach_od","pach_os"], "Pachimetria", "µm"), clear_figure=True)
    else:
        st.caption("Nessun dato pachimetria disponibile.")

    st.markdown('<div class="vm-section-title">Refrazione finale (SF)</div>', unsafe_allow_html=True)
    if df[["sf_od","sf_os"]].notna().any().any():
        st.pyplot(_chart(df, ["sf_od","sf_os"], "Refrazione", "Diottrie"), clear_figure=True)
    else:
        st.caption("Nessun dato refrazione disponibile.")

    st.divider()

    # ── Dettaglio ultima visita ───────────────────────────────
    if isinstance(latest_payload, dict):
        st.markdown('<div class="vm-section-title">Dettaglio ultima visita</div>', unsafe_allow_html=True)
        cl, cr = st.columns(2)

        with cl:
            st.markdown('<div class="vm-card">', unsafe_allow_html=True)
            st.markdown("**🩺 Esame obiettivo**")
            st.write("**Anamnesi:**", _fmt_val(latest_payload.get("anamnesi")))
            eo = latest_payload.get("esame_obiettivo", {}) or {}
            for label, key in [
                ("Congiuntiva", "congiuntiva"), ("Cornea", "cornea"),
                ("Camera anteriore", "camera_anteriore"), ("Cristallino", "cristallino"),
                ("Vitreo", "vitreo"), ("Fondo oculare", "fondo_oculare"),
            ]:
                v = eo.get(key)
                if v not in (None, ""):
                    st.write(f"**{label}:** {v}")
            st.markdown('</div>', unsafe_allow_html=True)

        with cr:
            st.markdown('<div class="vm-card">', unsafe_allow_html=True)
            st.markdown("**👓 Correzione finale**")
            cf = latest_payload.get("correzione_finale", {}) or {}
            od  = cf.get("od", {}) or {}
            os_ = cf.get("os", {}) or {}
            if od or os_:
                sf_od  = _to_float(od.get("sf"));  cyl_od = _to_float(od.get("cyl"));  ax_od = od.get("ax",0)
                sf_os  = _to_float(os_.get("sf")); cyl_os = _to_float(os_.get("cyl")); ax_os = os_.get("ax",0)
                if sf_od is not None:
                    st.write(f"**OD:** {sf_od:+.2f} ({cyl_od:+.2f} × {ax_od}°)")
                if sf_os is not None:
                    st.write(f"**OS:** {sf_os:+.2f} ({cyl_os:+.2f} × {ax_os}°)")
                add_v = _to_float(cf.get("add_vicino"))
                add_i = _to_float(cf.get("add_intermedio"))
                if add_v and cf.get("enable_add_vicino"):
                    st.write(f"**ADD vicino:** +{add_v:.2f}")
                if add_i and cf.get("enable_add_intermedio"):
                    st.write(f"**ADD intermedio:** +{add_i:.2f}")
            else:
                st.write("-")
            acuita = latest_payload.get("acuita", {}) or {}
            nat = acuita.get("naturale", {}) or {}
            cor = acuita.get("corretta", {}) or {}
            st.markdown("**Acuità visiva**")
            st.write(f"AVN: OD {_fmt_val(nat.get('od'))} | OS {_fmt_val(nat.get('os'))}")
            st.write(f"AVC: OD {_fmt_val(cor.get('od'))} | OS {_fmt_val(cor.get('os'))}")
            st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── Storico ───────────────────────────────────────────────
    with st.expander("📚 Storico completo visite"):
        show_df = df.copy()
        if "data" in show_df.columns:
            show_df["data"] = show_df["data"].dt.strftime("%d/%m/%Y")
        st.dataframe(show_df, use_container_width=True, hide_index=True)
