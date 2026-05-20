"""
Pagina DEBUG temporanea: mostra il contenuto raw di data_ora degli eventi
per capire dove sta il bug timezone.
"""
from __future__ import annotations

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Debug Timezone Eventi", layout="wide")

ROME_TZ = ZoneInfo("Europe/Rome")

user = st.session_state.get("user")
if not user or "admin" not in (user.get("roles") or []):
    st.error("🔒 Solo admin")
    st.stop()

st.title("🐛 Debug Timezone Eventi")

try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Errore connessione: {e}")
    st.stop()

is_postgres = hasattr(conn, "_conn") or "psycopg" in str(type(conn)).lower()
placeholder = "%s" if is_postgres else "?"

st.info(f"Backend: {'PostgreSQL' if is_postgres else 'SQLite'}")

# Query raw degli eventi futuri
try:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, titolo, data_ora, created_at, updated_at FROM ev_eventi "
            f"WHERE data_ora >= {placeholder} ORDER BY data_ora ASC",
            (datetime.now(ROME_TZ),)
        )
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        eventi = [dict(zip(cols, r)) for r in rows]
except Exception as e:
    st.error(f"Errore query: {e}")
    st.stop()

st.write(f"**Trovati {len(eventi)} eventi futuri**")

for ev in eventi:
    st.divider()
    st.subheader(f"#{ev['id']} — {ev['titolo']}")

    dt = ev["data_ora"]

    st.markdown("**🔬 Analisi data_ora:**")
    col1, col2 = st.columns(2)
    with col1:
        st.code(f"""
Type:           {type(dt).__name__}
repr():         {repr(dt)}
str():          {str(dt)}
tzinfo:         {dt.tzinfo}
utcoffset:      {dt.utcoffset()}
""")
    with col2:
        # Test di formattazione
        st.markdown("**Test formattazioni:**")

        # Scenario 1: dt così com'è
        st.code(f"dt.strftime():           {dt.strftime('%d/%m/%Y %H:%M %Z')}")

        # Scenario 2: se ha tzinfo, convertito a Rome
        if dt.tzinfo is not None:
            dt_rome = dt.astimezone(ROME_TZ)
            st.code(f"astimezone(ROME):       {dt_rome.strftime('%d/%m/%Y %H:%M %Z')}")
        else:
            st.code("dt è NAIVE (no tzinfo)")
            # Test: se assumessimo che il naive sia UTC
            dt_assumed_utc = dt.replace(tzinfo=ZoneInfo("UTC"))
            dt_rome = dt_assumed_utc.astimezone(ROME_TZ)
            st.code(f"se naive→UTC→Rome:       {dt_rome.strftime('%d/%m/%Y %H:%M %Z')}")
            # Test: se assumessimo che il naive sia già Rome
            dt_assumed_rome = dt.replace(tzinfo=ROME_TZ)
            st.code(f"se naive→Rome:           {dt_assumed_rome.strftime('%d/%m/%Y %H:%M %Z')}")

    # Verifica anche come arriverebbe alla funzione _format_data_evento
    st.markdown("**🧪 Simulazione _format_data_evento:**")
    try:
        from modules.eventi.email_eventi import _format_data_evento
        formatted = _format_data_evento(dt)
        st.code(f"_format_data_evento() → {formatted}")
    except Exception as e:
        st.error(f"Errore import: {e}")

st.divider()
st.caption("💡 Cancella questa pagina dopo aver finito il debug.")
