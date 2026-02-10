import json
import streamlit as st
from datetime import datetime
from vision_core.pdf_prescrizione import genera_prescrizione_occhiali_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson  # used only in Postgres path

def _diopters(min_d: float, max_d: float, step: float = 0.25):
    # returns list of strings: +0.25, 0.00, -0.25 ... within range (inclusive)
    vals = []
    v = max_d
    # go downward so 0.00 stays near top if max_d>0; we will later reorder
    while v >= min_d - 1e-9:
        vals.append(round(v, 2))
        v -= step
    # sort descending (e.g., +30 -> -30)
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

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data = st.text_input("Data prescrizione (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
    formato = st.selectbox("Formato PDF", ["A4", "A5"])

    st.subheader("Tipo occhiale")
    c1, c2 = st.columns([2,3])
    with c1:
        tipi = {
            "Monofocale": st.checkbox("Monofocale", key="t_mono"),
            "Progressivo": st.checkbox("Progressivo", key="t_prog"),
            "Bifocale": st.checkbox("Bifocale", key="t_bi"),
            "Office/Intermedio": st.checkbox("Office/Intermedio", key="t_off"),
            "Da sole": st.checkbox("Da sole", key="t_sole"),
            "Altro": st.checkbox("Altro", key="t_altro"),
        }
    with c2:
        tipo_note = st.text_area("Note lente (campo libero)", key="tipo_note")

    st.subheader("Lontano")
    c1,c2 = st.columns(2)
    with c1: odx_l = _ref_eye("presc_lont_odx")
    with c2: osn_l = _ref_eye("presc_lont_osn")

    st.subheader("Intermedio (solo se compilato)")
    c1,c2 = st.columns(2)
    with c1: odx_i = _ref_eye("presc_int_odx")
    with c2: osn_i = _ref_eye("presc_int_osn")

    st.subheader("Vicino (solo se compilato)")
    c1,c2 = st.columns(2)
    with c1: odx_v = _ref_eye("presc_vic_odx")
    with c2: osn_v = _ref_eye("presc_vic_osn")
    add = st.text_input("ADD (vicino)", key="add_vic")

    with_cirillo = st.toggle("Intestazione con Cirillo", value=True)

    if st.button("Genera PDF + salva nel DB"):
        tipi_sel = [k for k,v in tipi.items() if v]
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data": data,
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
        cur.execute(sql, (paz[0], data, formato, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Prescrizione salvata nel DB ✅")
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"prescrizione_{safe}_{data}_{formato}.pdf")