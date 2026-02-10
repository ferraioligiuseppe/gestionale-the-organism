
import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
from datetime import datetime
from vision_core.pdf_prescrizione import genera_prescrizione_occhiali_bytes

def ui_refrazione_prescrizione(conn):
    st.header("Refrazione completa / Prescrizione occhiali (salvataggio in DB)")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paziente = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data = st.text_input("Data prescrizione (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
    formato = st.selectbox("Formato PDF", ["A4", "A5"])
    with_cirillo = st.toggle("Intestazione con Cirillo", value=True)

    st.subheader("Refrazione")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**OD**")
        od_sfera = st.text_input("OD Sfera")
        od_cil = st.text_input("OD Cilindro")
        od_asse = st.text_input("OD Asse")
    with c2:
        st.markdown("**OS**")
        os_sfera = st.text_input("OS Sfera")
        os_cil = st.text_input("OS Cilindro")
        os_asse = st.text_input("OS Asse")

    if st.button("Genera PDF + salva nel DB"):
        dati = {
            "od_sfera": od_sfera, "od_cil": od_cil, "od_asse": od_asse,
            "os_sfera": os_sfera, "os_cil": os_cil, "os_asse": os_asse,
            "data": data,
            "cognome": paziente[1],
            "nome": paziente[2],
        }
        pdf_bytes = genera_prescrizione_occhiali_bytes(formato, dati, with_cirillo=with_cirillo)

        is_pg = conn.__class__.__module__.startswith("psycopg2")
        ph = "%s" if is_pg else "?"

        sql = (
            "INSERT INTO prescrizioni_occhiali "
            "(paziente_id, data_prescrizione, formato, with_cirillo, od_sfera, od_cil, od_asse, os_sfera, os_cil, os_asse, pdf_bytes) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})"
        )

        if is_pg:
            import psycopg2
            blob = psycopg2.Binary(pdf_bytes)
        else:
            blob = pdf_bytes

        cur = conn.cursor()
        cur.execute(sql, (paziente[0], data, formato, int(with_cirillo), od_sfera, od_cil, od_asse, os_sfera, os_cil, os_asse, blob))
        conn.commit()

        safe = f"{paziente[1]}_{paziente[2]}".replace(" ", "_")
        st.success("Prescrizione salvata nel DB ✅")
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"prescrizione_{safe}_{data}_{formato}.pdf")

    st.subheader("Storico (ultimo 20) – download")
    is_pg = conn.__class__.__module__.startswith("psycopg2")
    cur = conn.cursor()
    if is_pg:
        cur.execute(
            "SELECT id, data_prescrizione, formato, with_cirillo FROM prescrizioni_occhiali WHERE paziente_id = %s ORDER BY id DESC LIMIT 20",
            (paziente[0],)
        )
    else:
        cur.execute(
            "SELECT id, data_prescrizione, formato, with_cirillo FROM prescrizioni_occhiali WHERE paziente_id = ? ORDER BY id DESC LIMIT 20",
            (paziente[0],)
        )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna prescrizione salvata per questo paziente.")
        return

    scelta = st.selectbox("Seleziona prescrizione", rows, format_func=lambda r: f"#{r[0]} – {r[1]} – {r[2]} – {'Cirillo' if r[3] else 'Solo Ferraioli'}")
    if st.button("Carica PDF selezionato"):
        pid = scelta[0]
        if is_pg:
            cur.execute("SELECT pdf_bytes FROM prescrizioni_occhiali WHERE id = %s", (pid,))
        else:
            cur.execute("SELECT pdf_bytes FROM prescrizioni_occhiali WHERE id = ?", (pid,))
        blob = cur.fetchone()[0]
        if blob is None:
            st.error("PDF non presente in DB (pdf_bytes NULL).")
            return
        pdf_b = bytes(blob) if isinstance(blob, (memoryview, bytearray)) else blob
        safe = f"{paziente[1]}_{paziente[2]}".replace(" ", "_")
        st.download_button("Scarica PDF dallo storico", data=pdf_b, file_name=f"prescrizione_{safe}_{scelta[1]}_{scelta[2]}.pdf")
