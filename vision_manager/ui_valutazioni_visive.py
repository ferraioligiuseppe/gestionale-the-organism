
import streamlit as st

def ui_valutazioni_visive(conn):
    st.header("Valutazioni visive")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paziente = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data = st.text_input("Data valutazione (YYYY-MM-DD)")

    col1, col2 = st.columns(2)
    with col1:
        acuita = st.text_area("Acuità visiva (es. Visus / AV / note)")
        stereopsi = st.text_area("Stereopsi")
    with col2:
        motilita = st.text_area("Motilità oculare / Cover test / PPC")
        conclusioni = st.text_area("Conclusioni e indicazioni")

    if st.button("Salva valutazione"):
        cur = conn.cursor()
        ph = "%s" if conn.__class__.__module__.startswith("psycopg2") else "?"
        sql = (
            "INSERT INTO valutazioni_visive (paziente_id, data_valutazione, acuita_visiva, motilita_oculare, stereopsi, conclusioni) "
            f"VALUES ({ph},{ph},{ph},{ph},{ph},{ph})"
        )
        cur.execute(sql, (paziente[0], data, acuita, motilita, stereopsi, conclusioni))
        conn.commit()
        st.success("Valutazione salvata ✅")
