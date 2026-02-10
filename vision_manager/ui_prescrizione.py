import json
import streamlit as st
from datetime import date
from vision_core.pdf_prescrizione import genera_prescrizione_occhiali_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson  # used only in Postgres path

def _date_to_iso(d):
    return d.isoformat() if d else ""

def _date_to_eu(d):
    return d.strftime("%d/%m/%Y") if d else ""

def _diopters(min_d: float, max_d: float, step: float = 0.25):
    vals = []
    v = max_d
    while v >= min_d - 1e-9:
        vals.append(round(v, 2))
        v -= step
    vals = sorted(vals, reverse=True)
    return [""] + [f"{x:+.2f}".replace("+0.00","0.00") for x in vals]

SF_OPTS = _diopters(-30.0, 30.0, 0.25)
CIL_OPTS = _diopters(-15.0, 15.0, 0.25)
AX_OPTS = [""] + list(range(0, 181))

def _ref_eye(prefix: str):
    sf = st.selectbox(f"{prefix} SF", SF_OPTS, key=f"{prefix}_sf")
    cil = st.selectbox(f"{prefix} CIL", CIL_OPTS, key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", AX_OPTS, key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}

def ui_prescrizione(conn):
    st.header("Prescrizione occhiali (A4/A5) – TABO solo OSN + stampa solo compilati")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}", key="pr_paz")
    d = st.date_input("Data prescrizione", value=date.today(), key="pr_date")
    data_iso = _date_to_iso(d)
    data_eu = _date_to_eu(d)

    formato = st.selectbox("Formato PDF", ["A4", "A5"], key="pr_fmt")

    st.subheader("Tipo occhiale")
    c1, c2 = st.columns([2,3])
    with c1:
        tipi = {
            "Monofocale": st.checkbox("Monofocale", key="pr_mono"),
            "Progressivo": st.checkbox("Progressivo", key="pr_prog"),
            "Bifocale": st.checkbox("Bifocale", key="pr_bi"),
            "Office/Intermedio": st.checkbox("Office/Intermedio", key="pr_off"),
            "Da sole": st.checkbox("Da sole", key="pr_sole"),
            "Altro": st.checkbox("Altro", key="pr_altro"),
        }
    with c2:
        tipo_note = st.text_area("Note lente (campo libero)", key="pr_note_lente")

    st.subheader("Lontano")
    c1,c2 = st.columns(2)
    with c1: odx_l = _ref_eye("Lontano ODX")
    with c2: osn_l = _ref_eye("Lontano OSN")

    st.subheader("Intermedio (solo se compilato)")
    c1,c2 = st.columns(2)
    with c1: odx_i = _ref_eye("Intermedio ODX")
    with c2: osn_i = _ref_eye("Intermedio OSN")

    st.subheader("Vicino (solo se compilato)")
    c1,c2 = st.columns(2)
    with c1: odx_v = _ref_eye("Vicino ODX")
    with c2: osn_v = _ref_eye("Vicino OSN")
    add = st.selectbox("ADD (vicino)", [""] + [f"{x:+.2f}".replace("+0.00","0.00") for x in [round(i*0.25,2) for i in range(0, 41)]], key="pr_add")

    with_cirillo = st.toggle("Intestazione con Cirillo", value=True, key="pr_cirillo")

    if st.button("Genera PDF + salva nel DB", key="pr_save"):
        tipi_sel = [k for k,v in tipi.items() if v]
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data": data_eu,
            "data_iso": data_iso,
            "tipi_selezionati": tipi_sel,
            "tipo_note": tipo_note,
            "prescrizione": {
                "lontano": {"odx": odx_l, "osn": osn_l},
                "intermedio": {"odx": odx_i, "osn": osn_i},
                "vicino": {"odx": odx_v, "osn": osn_v, "add": add},
            }
        }
        pdf_bytes = genera_prescrizione_occhiali_bytes(formato, dati, with_cirillo=with_cirillo)

        is_pg = is_pg_conn(conn)
        p = ph(conn)

        if is_pg:
            import psycopg2
            json_val = PgJson(dati)
            blob = psycopg2.Binary(pdf_bytes)
        else:
            json_val = json.dumps(dati, ensure_ascii=False)
            blob = pdf_bytes

        sql = f"INSERT INTO prescrizioni_occhiali (paziente_id, data_prescrizione, formato, dati_json, pdf_bytes) VALUES ({p},{p},{p},{p},{p})"
        cur = conn.cursor()
        cur.execute(sql, (paz[0], data_iso, formato, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Prescrizione salvata nel DB ✅")
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"prescrizione_{safe}_{data_iso}_{formato}.pdf")
