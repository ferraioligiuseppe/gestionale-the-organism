# -*- coding: utf-8 -*-
"""
pages/migra_promemoria.py

Pagina admin TEMPORANEA: applica la migrazione che aggiunge le colonne
per i promemoria (48h/24h) alla tabella ev_iscrizioni nel database.

Da usare UNA volta dopo il deploy del sistema promemoria.
Dopo che mostra "tutte le colonne presenti", puoi cancellare questo file.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Migrazione Promemoria", layout="centered")

# Auth minima
user = st.session_state.get("user")
if not user or "admin" not in (user.get("roles") or []):
    st.error("🔒 Pagina riservata agli amministratori")
    st.stop()

st.title("🔧 Migrazione colonne Promemoria")
st.caption("Aggiunge le colonne promemoria_48h/24h alla tabella ev_iscrizioni.")

# Connessione
try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Errore connessione: {e}")
    st.stop()

# Detect backend
is_postgres = hasattr(conn, "_conn") or "psycopg" in str(type(conn)).lower()
st.info(f"Backend rilevato: {'PostgreSQL' if is_postgres else 'SQLite'}")

# === STEP 1: mostra colonne attuali ===
st.header("Step 1 — Colonne attuali")

def get_colonne():
    cur = conn.cursor()
    try:
        if is_postgres:
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ev_iscrizioni'
                ORDER BY ordinal_position
            """)
            cols = [r[0] for r in cur.fetchall()]
        else:
            cur.execute("PRAGMA table_info(ev_iscrizioni)")
            cols = [r[1] for r in cur.fetchall()]
        return cols
    finally:
        try:
            cur.close()
        except Exception:
            pass

colonne_attuali = get_colonne()
colonne_promemoria = [
    "promemoria_48h_inviato", "promemoria_48h_ts",
    "promemoria_24h_inviato", "promemoria_24h_ts",
]

st.write("**Colonne promemoria necessarie:**")
for col in colonne_promemoria:
    if col in colonne_attuali:
        st.markdown(f"- ✅ `{col}` (presente)")
    else:
        st.markdown(f"- ❌ `{col}` (MANCANTE)")

mancanti = [c for c in colonne_promemoria if c not in colonne_attuali]

st.divider()

# === STEP 2: applica migrazione ===
st.header("Step 2 — Applica migrazione")

if not mancanti:
    st.success("🎉 Tutte le colonne promemoria sono già presenti! Niente da fare.")
    st.caption("Puoi cancellare questa pagina dal repo: pages/migra_promemoria.py")
else:
    st.warning(f"Colonne da aggiungere: {', '.join(mancanti)}")

    if st.button("🔧 Applica migrazione ora", type="primary"):
        try:
            from modules.eventi.db_schema import _ensure_promemoria_columns
            backend = "postgres" if is_postgres else "sqlite"
            _ensure_promemoria_columns(conn, backend)
            st.success("✅ Migrazione applicata!")

            # Verifica
            colonne_dopo = get_colonne()
            ancora_mancanti = [c for c in colonne_promemoria if c not in colonne_dopo]
            if not ancora_mancanti:
                st.success("🎉 Tutte le colonne sono ora presenti!")
                st.balloons()
            else:
                st.error(f"Ancora mancanti: {ancora_mancanti}")
        except Exception as e:
            st.error(f"Errore migrazione: {e}")
            import traceback
            st.code(traceback.format_exc())
