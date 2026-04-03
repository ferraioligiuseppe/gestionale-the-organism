import json
from datetime import date
from collections.abc import Mapping

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from vision_manager.db import get_conn



def _css():
    """
    CSS unico e definitivo — usa :root e * per battere qualsiasi override di Streamlit.
    -webkit-text-fill-color è la chiave su Chrome/Windows.
    """
    st.markdown("""
<style>
/* Font di sistema */

/* 1. SFONDO GLOBALE */
html, body { background: #f0f4f8 !important; }
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container, section.main {
    background: #f0f4f8 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* 2. TESTO — regola base su tutto il documento */
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
    box-sizing: border-box;
}

/* 3. TUTTI I TESTI VISIBILI — selettori molto specifici */
p, span, div, label, li, td, th, h1, h2, h3, h4, h5, h6, small, strong, em, a {
    color: #1e293b;
    -webkit-text-fill-color: #1e293b;
}

/* 4. INPUT / TEXTAREA / NUMBER INPUT */
input, textarea, select {
    background: #ffffff !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-size: 0.93rem !important;
}
input:focus, textarea:focus {
    border-color: #2563a8 !important;
    box-shadow: 0 0 0 3px rgba(37,99,168,0.12) !important;
    outline: none !important;
}
input::placeholder, textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
}

/* 5. SELECTBOX STREAMLIT */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] *,
[data-baseweb="popover"] *,
[role="listbox"],
[role="listbox"] *,
[role="option"] {
    background: #ffffff !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: #eff6ff !important;
}

/* 6. METRICHE — selettori specifici v1.x e v2.x */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
[data-testid="stMetric"] * {
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] * {
    font-size: 0.8rem !important;
}

/* 7. LABELS WIDGET */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] * {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* 8. CAPTION */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.82rem !important;
}

/* 9. EXPANDER */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] details summary * {
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
}

/* 10. BOTTONI */
.stButton > button {
    background: #f1f5f9 !important;
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.15s;
}
.stButton > button:hover { background: #e2e8f0 !important; }
.stButton > button[kind="primary"] {
    background: #2563a8 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover { background: #1d4ed8 !important; }

/* 11. ALERT / INFO / WARNING */
[data-testid="stAlert"] * {
    -webkit-text-fill-color: inherit !important;
}

/* 12. DIVIDER */
hr { border-color: #e2e8f0 !important; margin: 20px 0 !important; }

/* 13. SIDEBAR */
[data-testid="stSidebar"] {
    background: #0f1923 !important;
    border-right: 1px solid #1e2d3d;
}
[data-testid="stSidebar"] * {
    color: #c8d6e5 !important;
    -webkit-text-fill-color: #c8d6e5 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-size: 1rem !important;
}
[data-testid="stSidebar"] input {
    background: #1a2a3a !important;
    border: 1px solid #2a3d52 !important;
    color: #e2eaf2 !important;
    -webkit-text-fill-color: #e2eaf2 !important;
    border-radius: 8px !important;
}

/* 14. CLASSI CUSTOM */
.vm-patient-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563a8 100%);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 20px;
}
.vm-patient-header * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.vm-patient-name { font-size: 1.5rem !important; font-weight: 600 !important; }
.vm-patient-meta {
    font-size: 0.85rem !important;
    color: #a8c4e0 !important;
    -webkit-text-fill-color: #a8c4e0 !important;
    margin-top: 4px;
    font-family: 'Consolas', 'Courier New', monospace !important;
}
.vm-section-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    margin: 20px 0 10px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}
.vm-card {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #e2e8f0;
    padding: 18px 22px;
    margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.vm-card * {
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
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
    from collections.abc import Mapping
    if isinstance(row, Mapping):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _list_pazienti_dashboard(conn):
    """Pazienti ATTIVI, deduplicati."""
    try:
        conn.rollback()
    except Exception:
        pass
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute("""
                SELECT DISTINCT ON (LOWER(TRIM(cognome)), LOWER(TRIM(nome)), COALESCE(TRIM(data_nascita),''))
                    id, cognome, nome, data_nascita
                FROM pazienti
                WHERE COALESCE(stato_paziente,'ATTIVO') = 'ATTIVO'
                ORDER BY LOWER(TRIM(cognome)), LOWER(TRIM(nome)), COALESCE(TRIM(data_nascita),''), id DESC
            """)
        else:
            cur.execute("""
                SELECT ID AS id, Cognome AS cognome, Nome AS nome, Data_Nascita AS data_nascita
                FROM Pazienti
                WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO'
                  AND ID IN (
                      SELECT MAX(ID) FROM Pazienti
                      WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO'
                      GROUP BY LOWER(TRIM(Cognome)), LOWER(TRIM(Nome)), COALESCE(TRIM(Data_Nascita),'')
                  )
                ORDER BY LOWER(TRIM(Cognome)), LOWER(TRIM(Nome))
            """)
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
        cur.execute(
            f"""
            SELECT id, data_visita, dati_json, is_deleted
            FROM visite_visive
            WHERE paziente_id={ph} AND COALESCE(is_deleted,0)=0
            ORDER BY data_visita ASC, id ASC
            """,
            (paziente_id,),
        )
        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    except Exception:
        try:
            if _is_pg(conn):
                conn.rollback()
        except Exception:
            pass
        cur2 = conn.cursor()
        cur2.execute(
            f"SELECT id, data_visita, dati_json FROM visite_visive WHERE paziente_id={ph} ORDER BY data_visita ASC, id ASC",
            (paziente_id,),
        )
        rows = cur2.fetchall()
        return [_dict_row(cur2, r) for r in rows]
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


def _fmt_val(v, fallback="-"):
    if v is None:
        return fallback
    try:
        import math
        if isinstance(v, float) and math.isnan(v):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    return s if s else fallback


def _chart(df, ycols, ylabel, threshold=None):
    """Grafico matplotlib con tema chiaro e date pulite."""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # Filtra solo righe con almeno un valore non-NaN tra le colonne richieste
    df_plot = df[df[ycols].notna().any(axis=1)].copy()
    if df_plot.empty:
        return None

    # Filtra date anomale: solo tra 2000 e oggi+1anno
    import datetime
    today = datetime.date.today()
    cutoff_min = pd.Timestamp("2000-01-01")
    cutoff_max = pd.Timestamp(today.replace(year=today.year + 1))
    df_plot = df_plot[(df_plot["data"] >= cutoff_min) & (df_plot["data"] <= cutoff_max)]
    if df_plot.empty:
        return None

    colors = ["#2563a8", "#0ea5e9", "#7c3aed", "#0d9488"]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    for i, col in enumerate(ycols):
        mask = df_plot[col].notna()
        if mask.sum() == 0:
            continue
        ax.plot(
            df_plot.loc[mask, "data"],
            df_plot.loc[mask, col],
            marker="o", markersize=5,
            label=col.replace("_", " ").upper(),
            color=colors[i % len(colors)],
            linewidth=2,
        )

    if threshold is not None:
        ax.axhline(threshold, linestyle="--", linewidth=1,
                   color="#ef4444", alpha=0.7, label=f"Soglia {threshold}")

    ax.set_ylabel(ylabel, color="#475569", fontsize=9)
    ax.tick_params(colors="#64748b", labelsize=8)
    ax.legend(fontsize=8, framealpha=0)
    ax.grid(True, alpha=0.12, color="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#e2e8f0")

    # Formato date asse X leggibile
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
    fig.autofmt_xdate(rotation=30, ha="right")
    fig.tight_layout()
    return fig


def ui_dashboard_paziente():
    _css()

    conn = get_conn()

    pazienti = _list_pazienti_dashboard(conn)
    if not pazienti:
        st.warning("Nessun paziente nel database.")
        return

    pazienti_df = pd.DataFrame(pazienti)
    pazienti_df["cognome"] = pazienti_df["cognome"].fillna("").astype(str).str.title()
    pazienti_df["nome"]    = pazienti_df["nome"].fillna("").astype(str).str.title()

    def _fmt_dn(dn):
        if not dn or pd.isna(dn):
            return ""
        try:
            return pd.to_datetime(str(dn)).strftime("%d/%m/%Y")
        except Exception:
            return str(dn)[:10]

    pazienti_df["dn_fmt"] = pazienti_df["data_nascita"].apply(_fmt_dn)
    pazienti_df["label"]  = pazienti_df.apply(
        lambda r: f"{r['cognome']} {r['nome']} ({r['dn_fmt']})" if r["dn_fmt"]
                  else f"{r['cognome']} {r['nome']}",
        axis=1
    )

    st.markdown("## 📊 Dashboard Paziente")

    col_sel, _ = st.columns([2, 1])
    with col_sel:
        paziente_label = st.selectbox("Seleziona paziente", pazienti_df["label"].tolist(),
                                      label_visibility="collapsed")

    paziente = pazienti_df[pazienti_df["label"] == paziente_label].iloc[0]
    eta = calcola_eta(paziente["data_nascita"])

    dn_fmt = ""
    if paziente["data_nascita"]:
        try:
            dn_fmt = pd.to_datetime(paziente["data_nascita"]).strftime("%d/%m/%Y")
        except Exception:
            dn_fmt = str(paziente["data_nascita"])

    # Header paziente
    st.markdown(f"""
    <div class="vm-patient-header">
        <div class="vm-patient-name">{paziente['label']}</div>
        <div class="vm-patient-meta">
            {"Nato/a il " + dn_fmt if dn_fmt else ""}
            {"&nbsp;&nbsp;·&nbsp;&nbsp;" + str(eta) + " anni" if eta is not None else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)

    visite = _list_visite_dashboard(conn, int(paziente["id"]))
    if not visite:
        st.info("Nessuna visita registrata.")
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

    # ── Metriche ──────────────────────────────────────────────
    st.markdown('<div class="vm-section-title">Ultimi valori misurati</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("IOP OD",         _fmt_val(ultima["iop_od"],  "-") if pd.isna(ultima["iop_od"])  else f'{ultima["iop_od"]:.1f} mmHg')
    c2.metric("IOP OS",         _fmt_val(ultima["iop_os"],  "-") if pd.isna(ultima["iop_os"])  else f'{ultima["iop_os"]:.1f} mmHg')
    c3.metric("Pachimetria OD", _fmt_val(ultima["pach_od"], "-") if pd.isna(ultima["pach_od"]) else f'{ultima["pach_od"]:.0f} µm')
    c4.metric("Pachimetria OS", _fmt_val(ultima["pach_os"], "-") if pd.isna(ultima["pach_os"]) else f'{ultima["pach_os"]:.0f} µm')

    st.divider()

    # ── Grafici ───────────────────────────────────────────────
    for title, cols, ylabel, threshold in [
        ("Andamento IOP",         ["iop_od",  "iop_os"],  "mmHg",     21),
        ("Andamento Pachimetria", ["pach_od", "pach_os"], "µm",       None),
        ("Refrazione finale SF",  ["sf_od",   "sf_os"],   "Diottrie", None),
    ]:
        if df[cols].notna().any().any():
            st.markdown(f'<div class="vm-section-title">{title}</div>', unsafe_allow_html=True)
            fig = _chart(df, cols, ylabel, threshold)
            if fig:
                st.pyplot(fig, clear_figure=True)
            else:
                st.caption("Dati non sufficienti per il grafico.")

    st.divider()

    # ── Dettaglio ultima visita ───────────────────────────────
    if isinstance(latest_payload, dict):
        st.markdown('<div class="vm-section-title">Dettaglio ultima visita</div>', unsafe_allow_html=True)
        cl, cr = st.columns(2)

        with cl:
            st.markdown("**🩺 Esame obiettivo**")
            anamnesi = latest_payload.get("anamnesi","")
            if anamnesi:
                st.write("**Anamnesi:**", anamnesi)
            eo = latest_payload.get("esame_obiettivo", {}) or {}
            campi = [
                ("Congiuntiva",      "congiuntiva"),
                ("Cornea",           "cornea"),
                ("Camera anteriore", "camera_anteriore"),
                ("Cristallino",      "cristallino"),
                ("Vitreo",           "vitreo"),
                ("Fondo oculare",    "fondo_oculare"),
            ]
            shown = False
            for label, key in campi:
                v = eo.get(key)
                if v not in (None, ""):
                    st.write(f"**{label}:** {v}")
                    shown = True
            if not shown:
                st.caption("Nessun dato esame obiettivo.")

            acuita = latest_payload.get("acuita", {}) or {}
            nat = acuita.get("naturale", {}) or {}
            cor = acuita.get("corretta", {}) or {}
            if any(v for v in [nat.get("od"), nat.get("os"), cor.get("od"), cor.get("os")]):
                st.markdown("**Acuità visiva**")
                st.write(f"Naturale — OD: {_fmt_val(nat.get('od'))} | OS: {_fmt_val(nat.get('os'))}")
                st.write(f"Corretta — OD: {_fmt_val(cor.get('od'))} | OS: {_fmt_val(cor.get('os'))}")

        with cr:
            st.markdown("**👓 Correzione finale**")
            cf = latest_payload.get("correzione_finale", {}) or {}
            od  = cf.get("od",  {}) or {}
            os_ = cf.get("os",  {}) or {}
            sf_od  = _to_float(od.get("sf"));  cyl_od = _to_float(od.get("cyl")); ax_od  = od.get("ax", 0)
            sf_os  = _to_float(os_.get("sf")); cyl_os = _to_float(os_.get("cyl")); ax_os = os_.get("ax", 0)
            if sf_od is not None:
                st.write(f"**OD:** {sf_od:+.2f} ({cyl_od:+.2f} × {ax_od}°)")
            if sf_os is not None:
                st.write(f"**OS:** {sf_os:+.2f} ({cyl_os:+.2f} × {ax_os}°)")
            add_v = _to_float(cf.get("add_vicino"))
            add_i = _to_float(cf.get("add_intermedio"))
            if add_v and cf.get("enable_add_vicino"):
                st.write(f"**ADD vicino:** +{add_v:.2f} D")
            if add_i and cf.get("enable_add_intermedio"):
                st.write(f"**ADD intermedio:** +{add_i:.2f} D")

    st.divider()

    with st.expander("📚 Storico completo visite"):
        show_df = df.copy()
        if "data" in show_df.columns:
            show_df["data"] = show_df["data"].dt.strftime("%d/%m/%Y")
        st.dataframe(show_df, use_container_width=True, hide_index=True)
