import os, sys
import streamlit as st

def ui_diagnostica(conn):
    st.header("Diagnostica – Vision Manager")
    st.write(("✅" if os.getenv("DATABASE_URL") else "❌") + " DATABASE_URL")
    st.write("Conn type:", conn.__class__.__module__)
