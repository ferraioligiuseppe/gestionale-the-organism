"""
Pagina admin TEMPORANEA per correggere eventi creati con il bug timezone.

Eventi creati con il vecchio codice (datetime naive) sono stati salvati su
TIMESTAMPTZ con offset UTC. Quando vengono letti+formattati in Europe/Rome,
mostrano +2 ore (in ora legale) rispetto all'orario inserito.

Questa pagina:
1. Mostra tutti gli eventi che POTREBBERO avere il bug (data_ora futura)
2. Permette di selezionare quali correggere
3. Sottrae 2 ore (CEST) o 1 ora (CET) dal data_ora salvato
4. NON cambia le iscrizioni associate

Dopo aver corretto gli eventi esistenti, cancella questa pagina dal repo.
"""
from __future__ import annotations

import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Fix Timezone Eventi", layout="wide")

ROME_TZ = ZoneInfo("Europe/Rome")

# Auth check minimo
user = st.session_state.get("user")
if not user or "admin" not in (user.get("roles") or []):
    st.error("🔒 Pagina riservata agli amministratori")
    st.stop()

st.title("🕒 Fix Timezone Eventi")
st.caption("Pagina temporanea — corregge eventi salvati con orario sbagliato di 2 ore.")

st.info(
    "**Cosa fa questa pagina:**\n\n"
    "Prima del fix del codice, ogni evento creato veniva salvato come UTC, "
    "quindi un evento inserito alle 20:00 ora italiana viene mostrato alle 22:00.\n\n"
    "Questa pagina sottrae 2 ore (durante l'ora legale) o 1 ora (ora solare) "
    "ai data_ora degli eventi selezionati, riportandoli all'orario reale."
)

# Connessione DB
try:
    from modules.app_core import get_connection
    conn = get_connection()
except Exception as e:
    st.error(f"Errore connessione: {e}")
    st.stop()

# Backend detection
is_postgres = hasattr(conn, "_conn") or "psycopg" in str(type(conn)).lower()
placeholder = "%s" if is_postgres else "?"

# === STEP 1: lista eventi futuri ===
st.header("Step 1 — Eventi da controllare")
st.caption("Vengono mostrati gli eventi futuri (data_ora >= oggi).")

try:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, titolo, data_ora, sede, slug FROM ev_eventi "
        f"WHERE data_ora >= {placeholder} ORDER BY data_ora ASC",
        (datetime.now(ROME_TZ),)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    eventi = [dict(zip(cols, r)) for r in rows]
    try:
        cur.close()
    except Exception:
        pass
except Exception as e:
    st.error(f"Errore query: {e}")
    st.stop()

if not eventi:
    st.success("✅ Nessun evento futuro trovato. Niente da correggere.")
    st.stop()

st.write(f"Trovati **{len(eventi)} eventi** futuri:")

# Tabella con orari attuali (Rome) e proposti
for ev in eventi:
    dt = ev["data_ora"]
    if dt.tzinfo is not None:
        dt_rome = dt.astimezone(ROME_TZ)
    else:
        # Datetime naive: lo trattiamo come UTC (è probabilmente cosi che è stato salvato)
        dt_rome = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ROME_TZ)

    # Calcola offset attuale (DST?): in maggio è +2, in inverno +1
    dst_offset = dt_rome.utcoffset().total_seconds() / 3600
    dt_corretto = dt_rome - timedelta(hours=int(dst_offset))

    ev["dt_attuale_str"] = dt_rome.strftime("%d/%m/%Y %H:%M")
    ev["dt_corretto_str"] = dt_corretto.strftime("%d/%m/%Y %H:%M")
    ev["dst_offset"] = int(dst_offset)
    ev["dt_corretto"] = dt_corretto

st.divider()

# === STEP 2: selezione e correzione ===
st.header("Step 2 — Seleziona eventi da correggere")

st.warning(
    "⚠️ **Attenzione:** la correzione **sottrae l'offset orario** (es: -2h in ora legale, "
    "-1h in ora solare) dal data_ora memorizzato. Fallo SOLO se l'orario mostrato attualmente "
    "è effettivamente sbagliato (+2h rispetto a quello inserito originariamente)."
)

selezionati = []
for ev in eventi:
    cols_view = st.columns([0.1, 0.35, 0.25, 0.25, 0.05])
    with cols_view[0]:
        checked = st.checkbox("", key=f"chk_{ev['id']}", label_visibility="collapsed")
    with cols_view[1]:
        st.markdown(f"**{ev['titolo']}**")
        st.caption(f"id #{ev['id']} · {ev.get('sede', '—')}")
    with cols_view[2]:
        st.markdown(f"🕐 Attuale: **{ev['dt_attuale_str']}**")
        st.caption(f"(con offset +{ev['dst_offset']}h)")
    with cols_view[3]:
        st.markdown(f"🕐 Corretto: **{ev['dt_corretto_str']}**")
        st.caption(f"(sottratto -{ev['dst_offset']}h)")
    with cols_view[4]:
        st.write("")

    if checked:
        selezionati.append(ev)

st.divider()

if not selezionati:
    st.info("Spunta gli eventi da correggere per procedere.")
    st.stop()

st.subheader(f"Stai per correggere {len(selezionati)} evento/i:")
for ev in selezionati:
    st.markdown(f"- **{ev['titolo']}**: {ev['dt_attuale_str']} → **{ev['dt_corretto_str']}**")

st.markdown("")
conferma = st.checkbox("✋ Confermo: voglio applicare la correzione agli eventi selezionati")

if conferma and st.button("🔧 Applica correzione", type="primary"):
    successi = 0
    errori = []
    for ev in selezionati:
        try:
            cur = conn.cursor()
            # Aggiorno data_ora sottraendo offset
            # Il datetime corretto è già aware in ROME_TZ
            cur.execute(
                f"UPDATE ev_eventi SET data_ora = {placeholder}, "
                f"updated_at = {placeholder} WHERE id = {placeholder}",
                (ev["dt_corretto"], datetime.now(ROME_TZ), ev["id"])
            )
            try:
                cur.close()
            except Exception:
                pass
            conn.commit()
            successi += 1
        except Exception as e:
            errori.append(f"#{ev['id']} {ev['titolo']}: {e}")

    if successi:
        st.success(f"✅ {successi} evento/i corretto/i con successo!")
        st.balloons()
    if errori:
        st.error("Errori:")
        for err in errori:
            st.code(err)

    st.info("Ricarica la pagina per vedere gli orari aggiornati.")

st.divider()
st.caption(
    "💡 Dopo che tutti gli eventi sono stati corretti e il fix nel codice è in produzione, "
    "puoi cancellare questo file (`pages/fix_timezone_eventi.py`) dal repo."
)
