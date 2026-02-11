import streamlit as st
from utils import ph

def _date_to_iso(d):
    return d.isoformat() if d else ""

def ui_pazienti(conn):
    st.header("Pazienti (Modulo Visivo)")

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        nome = st.text_input("Nome", key="pz_nome")
    with c2:
        cognome = st.text_input("Cognome", key="pz_cognome")
    with c3:
        dn = st.date_input("Data di nascita", value=None, key="pz_dn")
        data_nascita = _date_to_iso(dn)

    note = st.text_area("Note", key="pz_note")

    if st.button("Salva paziente", key="pz_save"):
        cur = conn.cursor()
        p = ph(conn)
        sql = f"INSERT INTO pazienti_visivi (nome, cognome, data_nascita, note) VALUES ({p},{p},{p},{p})"
        cur.execute(sql, (nome, cognome, data_nascita, note))
        conn.commit()
        st.success("Paziente salvato ✅")

    st.subheader("Elenco pazienti")
    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti_visivi ORDER BY cognome, nome")
    rows = cur.fetchall()
    if not rows:
        st.info("Nessun paziente presente.")
    else:
        for r in rows:
            st.write(f"{r[0]} – {r[1]} {r[2]} ({r[3] or ''})")
