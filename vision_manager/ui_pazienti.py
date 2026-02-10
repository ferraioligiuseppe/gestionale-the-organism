
import streamlit as st

def ui_pazienti(conn):
    st.header("Pazienti (Modulo Visivo)")

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        nome = st.text_input("Nome")
    with c2:
        cognome = st.text_input("Cognome")
    with c3:
        data_nascita = st.text_input("Data di nascita (YYYY-MM-DD)")
    note = st.text_area("Note")

    if st.button("Salva paziente"):
        cur = conn.cursor()
        ph = "%s" if conn.__class__.__module__.startswith("psycopg2") else "?"
        sql = f"INSERT INTO pazienti_visivi (nome, cognome, data_nascita, note) VALUES ({ph},{ph},{ph},{ph})"
        cur.execute(sql, (nome, cognome, data_nascita, note))
        conn.commit()
        st.success("Paziente salvato")

    st.subheader("Elenco pazienti")
    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti_visivi ORDER BY cognome, nome")
    rows = cur.fetchall()
    if not rows:
        st.info("Nessun paziente presente.")
    else:
        for r in rows:
            st.write(f"{r[0]} – {r[1]} {r[2]} ({r[3] or ''})")
