
import os, sys
import streamlit as st

def ui_diagnostica(conn):
    st.header("Diagnostica – Vision Manager")

    st.subheader("Path & import")
    st.write("cwd:", os.getcwd())
    st.write("sys.path (prime 5):", sys.path[:5])

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    st.write("ROOT_DIR:", root_dir)
    st.write("vision_core exists:", os.path.exists(os.path.join(root_dir, "vision_core")))
    st.write("vision_core/pdf_prescrizione.py exists:", os.path.exists(os.path.join(root_dir, "vision_core", "pdf_prescrizione.py")))

    st.subheader("Secrets / Environment")
    st.write(("✅" if os.getenv("DATABASE_URL") else "❌") + " DATABASE_URL")

    st.subheader("Database")
    st.write("Conn type:", conn.__class__.__module__)
    cur = conn.cursor()
    expected = ["pazienti_visivi", "valutazioni_visive", "prescrizioni_occhiali"]
    is_pg = conn.__class__.__module__.startswith("psycopg2")

    try:
        if is_pg:
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
            existing = {r[0] for r in cur.fetchall()}
        else:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing = {r[0] for r in cur.fetchall()}

        st.write("Tabelle trovate:", sorted(existing))
        missing = [t for t in expected if t not in existing]
        if missing:
            st.error(f"Mancano tabelle: {missing}")
        else:
            st.success("Tabelle OK ✅")

        cur.execute("SELECT COUNT(*) FROM pazienti_visivi")
        st.write("COUNT pazienti_visivi:", cur.fetchone()[0])
        st.success("Query OK ✅")
    except Exception as e:
        st.error(f"Errore DB: {e}")

    st.subheader("Storage")
    st.info("Modalità scelta: PDF salvati nel database (Neon). Nessun S3 richiesto.")
