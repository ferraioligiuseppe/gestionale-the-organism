import os
import streamlit as st
from utils import is_pg_conn

def ui_diagnostica(conn):
    st.header("Diagnostica – Vision Manager")
    st.write(("✅" if os.getenv("DATABASE_URL") else "❌") + " DATABASE_URL")
    st.write("Conn type:", conn.__class__.__module__)
    st.write("Postgres:", "✅" if is_pg_conn(conn) else "❌ (SQLite)")
