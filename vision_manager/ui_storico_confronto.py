import pandas as pd
import streamlit as st
from utils import is_pg_conn, ph, json_to_dict, blob_to_bytes
from export_utils import build_export_ottico_csv

def ui_storico_confronto(conn):
    st.header("Storico visite + confronto nel tempo + export da ottico")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    pid = paz[0]

    is_pg = is_pg_conn(conn)
    p = ph(conn)

    # ---- Load visits ----
    if is_pg:
        cur.execute("SELECT id, data_visita, dati_json, pdf_bytes FROM visite_visive WHERE paziente_id = %s ORDER BY data_visita", (pid,))
    else:
        cur.execute("SELECT id, data_visita, dati_json, pdf_bytes FROM visite_visive WHERE paziente_id = ? ORDER BY data_visita", (pid,))
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna visita registrata per questo paziente.")
        return

    # Build dataframe for selection and charting
    visits = []
    for rid, d, j, b in rows:
        di = json_to_dict(j)
        visits.append({"id": rid, "data": d, "json": di, "pdf": b})

    st.subheader("Elenco visite")
    df_list = pd.DataFrame([{"ID": v["id"], "Data": v["data"]} for v in visits])
    st.dataframe(df_list, use_container_width=True, hide_index=True)

    # Download a specific PDF
    st.subheader("Scarica referto PDF")
    sel_id = st.selectbox("Seleziona visita", [v["id"] for v in visits], format_func=lambda x: f"Visita #{x}")
    vsel = next(v for v in visits if v["id"] == sel_id)
    pdf_bytes = blob_to_bytes(vsel["pdf"])
    if pdf_bytes:
        st.download_button("Download referto PDF", data=pdf_bytes, file_name=f"referto_visita_{paz[1]}_{paz[2]}_{vsel['data']}.pdf")
    else:
        st.warning("PDF non presente in DB per questa visita.")

    # ---- Comparison ----
    st.subheader("Confronto tra due visite")
    ids = [v["id"] for v in visits]
    col1, col2 = st.columns(2)
    with col1:
        id_a = st.selectbox("Visita A", ids, index=max(0, len(ids)-2))
    with col2:
        id_b = st.selectbox("Visita B", ids, index=len(ids)-1)

    A = next(v for v in visits if v["id"] == id_a)["json"]
    B = next(v for v in visits if v["id"] == id_b)["json"]

    def get_ref(d, kind, dist, eye, field):
        return (((d.get(kind, {}) or {}).get(dist, {}) or {}).get(eye, {}) or {}).get(field, "")

    def get_add(d, kind, dist):
        return (((d.get(kind, {}) or {}).get(dist, {}) or {}).get("add", ""))

    def get_av(d, key):
        return ((d.get("av", {}) or {}).get(key, ""))

    # Build comparison table (Refrazione corretta + AV Lontano)
    rows_cmp = []
    for dist in ["lontano", "intermedio", "vicino"]:
        for eye in ["odx", "osn"]:
            for field in ["sf", "cil", "ax"]:
                a = get_ref(A, "ref_corretta", dist, eye, field)
                b = get_ref(B, "ref_corretta", dist, eye, field)
                if (str(a).strip() == "" and str(b).strip() == ""):
                    continue
                rows_cmp.append({
                    "Parametro": f"Ref. corretta {dist.upper()} {eye.upper()} {field.upper()}",
                    "Visita A": a,
                    "Visita B": b
                })
        add_a = get_add(A, "ref_corretta", dist)
        add_b = get_add(B, "ref_corretta", dist)
        if (str(add_a).strip() != "" or str(add_b).strip() != ""):
            rows_cmp.append({
                "Parametro": f"Ref. corretta {dist.upper()} ADD",
                "Visita A": add_a,
                "Visita B": add_b
            })

    for avk, label in [
        ("lontano_odx","AV Lontano ODX"),
        ("lontano_osn","AV Lontano OSN"),
        ("vicino_odx","AV Vicino ODX"),
        ("vicino_osn","AV Vicino OSN"),
        ("intermedio_odx","AV Intermedio ODX"),
        ("intermedio_osn","AV Intermedio OSN"),
    ]:
        a = get_av(A, avk)
        b = get_av(B, avk)
        if (str(a).strip() == "" and str(b).strip() == ""):
            continue
        rows_cmp.append({"Parametro": label, "Visita A": a, "Visita B": b})

    df_cmp = pd.DataFrame(rows_cmp)
    if df_cmp.empty:
        st.info("Nessun dato confrontabile (ref_corretta/AV) tra queste visite.")
    else:
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)

    # ---- Trend charts ----
    st.subheader("Grafici nel tempo")
    # Build timeseries for key numeric-ish fields (SF/CIL as float when possible)
    def to_float(x):
        try:
            s = str(x).replace(",", ".").strip()
            return float(s)
        except Exception:
            return None

    series_rows = []
    for v in visits:
        j = v["json"]
        date = v["data"]
        sf_odx = to_float(get_ref(j, "ref_corretta", "lontano", "odx", "sf"))
        sf_osn = to_float(get_ref(j, "ref_corretta", "lontano", "osn", "sf"))
        cil_odx = to_float(get_ref(j, "ref_corretta", "lontano", "odx", "cil"))
        cil_osn = to_float(get_ref(j, "ref_corretta", "lontano", "osn", "cil"))
        series_rows.append({
            "Data": date,
            "SF Lontano ODX": sf_odx,
            "SF Lontano OSN": sf_osn,
            "CIL Lontano ODX": cil_odx,
            "CIL Lontano OSN": cil_osn,
        })
    df_ts = pd.DataFrame(series_rows).set_index("Data")
    # drop all-null columns
    df_ts = df_ts.dropna(axis=1, how="all")
    if df_ts.empty:
        st.info("Nessun dato numerico (SF/CIL lontano) disponibile per grafici.")
    else:
        st.line_chart(df_ts)

    st.subheader("Export da ottico (CSV)")
    # Export uses Visit B by default (latest selection)
    csv_bytes = build_export_ottico_csv(B)
    st.download_button("Scarica CSV ottico (da Visita B)", data=csv_bytes, file_name=f"export_ottico_{paz[1]}_{paz[2]}_{id_b}.csv")
