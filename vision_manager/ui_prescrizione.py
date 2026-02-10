import json
import streamlit as st
from datetime import datetime
from vision_core.pdf_prescrizione import genera_prescrizione_occhiali_bytes

def _axis_options():
    return list(range(0, 181))

def _ref_eye(prefix: str):
    sf = st.text_input(f"{prefix} SF", key=f"{prefix}_sf")
    cil = st.text_input(f"{prefix} CIL", key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", _axis_options(), key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}

def ui_prescrizione(conn):
    st.header("Prescrizione occhiali (A4/A5) – TABO semiluna + tipo occhiale")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data = st.text_input("Data prescrizione (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
    formato = st.selectbox("Formato PDF", ["A4", "A5"])

    tipo = st.selectbox("Tipo di occhiale", [
        "", "Monofocale", "Progressivo", "Bifocale", "Da sole", "Office (intermedio)", "Altro"
    ])

    st.subheader("Lontano")
    c1,c2 = st.columns(2)
    with c1: od_l = _ref_eye("presc_lont_od")
    with c2: os_l = _ref_eye("presc_lont_os")

    st.subheader("Intermedio")
    c1,c2 = st.columns(2)
    with c1: od_i = _ref_eye("presc_int_od")
    with c2: os_i = _ref_eye("presc_int_os")

    st.subheader("Vicino")
    c1,c2 = st.columns(2)
    with c1: od_v = _ref_eye("presc_vic_od")
    with c2: os_v = _ref_eye("presc_vic_os")
    add = st.text_input("ADD (vicino)")

    with_cirillo = st.toggle("Intestazione con Cirillo", value=True)

    if st.button("Genera PDF + salva nel DB"):
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data": data,
            "tipo_occhiale": tipo,
            "prescrizione": {
                "lontano": {"od": od_l, "os": os_l},
                "intermedio": {"od": od_i, "os": os_i},
                "vicino": {"od": od_v, "os": os_v, "add": add},
            }
        }
        pdf_bytes = genera_prescrizione_occhiali_bytes(formato, dati, with_cirillo=with_cirillo)

        is_pg = conn.__class__.__module__.startswith("psycopg2")
        ph = "%s" if is_pg else "?"

        if is_pg:
            import psycopg2
            from psycopg2.extras import Json
            json_val = Json(dati)
            blob = psycopg2.Binary(pdf_bytes)
        else:
            json_val = json.dumps(dati, ensure_ascii=False)
            blob = pdf_bytes

        sql = f"INSERT INTO prescrizioni_occhiali (paziente_id, data_prescrizione, formato, tipo_occhiale, dati_json, pdf_bytes) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})"
        cur = conn.cursor()
        cur.execute(sql, (paz[0], data, formato, tipo, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Prescrizione salvata nel DB ✅")
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"prescrizione_{safe}_{data}_{formato}.pdf")
