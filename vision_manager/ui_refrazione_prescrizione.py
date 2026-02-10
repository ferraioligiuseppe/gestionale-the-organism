
import streamlit as st
from datetime import datetime
from vision_core.pdf_prescrizione import genera_prescrizione_occhiali_bytes
from s3_utils import upload_bytes, presign_get

def ui_refrazione_prescrizione(conn):
    st.header("Refrazione completa / Prescrizione occhiali")

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

    if st.button("Genera PDF + carica su S3"):
        dati = {
            "od_sfera": od_sfera, "od_cil": od_cil, "od_asse": od_asse,
            "os_sfera": os_sfera, "os_cil": os_cil, "os_asse": os_asse,
            "data": data,
            "cognome": paziente[1],
            "nome": paziente[2],
        }
        pdf_bytes = genera_prescrizione_occhiali_bytes(formato, dati, with_cirillo=with_cirillo)

        safe = f"{paziente[1]}_{paziente[2]}".replace(" ", "_")
        key = f"vision/prescrizioni/{safe}/{data}_prescrizione_{formato}{'_cirillo' if with_cirillo else ''}.pdf"
        upload_bytes(pdf_bytes, key)
        url = presign_get(key)

        ph = "%s" if conn.__class__.__module__.startswith("psycopg2") else "?"
        sql = (
            "INSERT INTO prescrizioni_occhiali "
            "(paziente_id, data_prescrizione, formato, with_cirillo, od_sfera, od_cil, od_asse, os_sfera, os_cil, os_asse, s3_key) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})"
        )
        cur = conn.cursor()
        cur.execute(sql, (paziente[0], data, formato, int(with_cirillo), od_sfera, od_cil, od_asse, os_sfera, os_cil, os_asse, key))
        conn.commit()

        st.success("Prescrizione salvata su S3.")
        st.download_button("Scarica PDF", data=pdf_bytes, file_name=f"prescrizione_{safe}_{data}_{formato}.pdf")
        st.markdown(f"Link temporaneo: {url}")

    st.subheader("Storico (ultimo 20)")
    cur = conn.cursor()
    if conn.__class__.__module__.startswith("psycopg2"):
        cur.execute("SELECT data_prescrizione, formato, s3_key FROM prescrizioni_occhiali WHERE paziente_id = %s ORDER BY id DESC LIMIT 20", (paziente[0],))
    else:
        cur.execute("SELECT data_prescrizione, formato, s3_key FROM prescrizioni_occhiali WHERE paziente_id = ? ORDER BY id DESC LIMIT 20", (paziente[0],))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            st.write(f"• {r[0]} – {r[1]} – {r[2]}")
