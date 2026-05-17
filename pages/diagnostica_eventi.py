# -*- coding: utf-8 -*-
# pages/diagnostica_eventi.py
#
# Pagina admin TEMPORANEA di diagnostica per il modulo eventi.
# Verifica che le tabelle ev_eventi e ev_iscrizioni siano state create
# correttamente sul Postgres OVH e che siano scrivibili.
#
# COME USARE:
#   1. Login al gestionale come admin
#   2. URL: https://testgestionale.streamlit.app/diagnostica_eventi
#   3. Controlla i risultati
#   4. Cancella il file dal repo quando hai finito le verifiche

import streamlit as st
import sys, os
import traceback

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(
    page_title="The Organism — Diagnostica Eventi",
    page_icon="🔍",
    layout="centered",
)

st.title("🔍 Diagnostica modulo Eventi")
st.caption("Pagina admin temporanea — verifica setup DB modulo eventi.")

# Protezione minima: utente loggato
user = st.session_state.get("user")
if not user or not user.get("username"):
    st.error("⚠️ Devi essere loggato nel gestionale.")
    st.info("Vai su https://testgestionale.streamlit.app/ e fai login, poi torna qui.")
    st.stop()

st.success(f"Login rilevato: **{user['username']}**")
st.divider()

# Connessione DB
try:
    from modules.app_core import get_connection
    conn = get_connection()
    st.success("✅ Connessione al database OK")
except Exception as e:
    st.error(f"❌ Connessione DB fallita: {e}")
    st.code(traceback.format_exc())
    st.stop()

st.divider()

# =============================================================================
# CHECK 1: ESISTENZA TABELLE
# =============================================================================

st.markdown("## Check 1 — Esistenza tabelle del modulo")

TABELLE_ATTESE = ["ev_eventi", "ev_iscrizioni"]

try:
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
        ORDER BY table_name;
    """, (TABELLE_ATTESE,))
    rows = cur.fetchall()
    cur.close()

    tabelle_trovate = [r[0] for r in rows]

    col1, col2 = st.columns(2)
    for t in TABELLE_ATTESE:
        if t in tabelle_trovate:
            col1.success(f"✅ `{t}` esiste")
        else:
            col2.error(f"❌ `{t}` NON trovata")

    if set(tabelle_trovate) != set(TABELLE_ATTESE):
        st.warning(
            "Alcune tabelle mancano. Verifica che lo schema sia stato applicato "
            "(controlla i log Streamlit del primo avvio dopo il deploy)."
        )
        st.stop()
except Exception as e:
    st.error(f"Errore controllo tabelle: {e}")
    st.code(traceback.format_exc())
    st.stop()

st.divider()

# =============================================================================
# CHECK 2: STRUTTURA COLONNE
# =============================================================================

st.markdown("## Check 2 — Struttura delle tabelle")

for tabella in TABELLE_ATTESE:
    with st.expander(f"📋 Colonne di `{tabella}`"):
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position;
            """, (tabella,))
            cols = cur.fetchall()
            cur.close()

            if cols:
                st.dataframe(
                    {
                        "Colonna": [c[0] for c in cols],
                        "Tipo": [c[1] for c in cols],
                        "Nullable": [c[2] for c in cols],
                        "Default": [c[3] or "" for c in cols],
                    },
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(f"Totale: {len(cols)} colonne")
            else:
                st.warning("Nessuna colonna trovata.")
        except Exception as e:
            st.error(f"Errore: {e}")

st.divider()

# =============================================================================
# CHECK 3: CONTEGGIO RIGHE
# =============================================================================

st.markdown("## Check 3 — Contenuto attuale")

try:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ev_eventi;")
    n_eventi = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ev_iscrizioni;")
    n_iscrizioni = cur.fetchone()[0]
    cur.close()

    col1, col2 = st.columns(2)
    col1.metric("Eventi", n_eventi)
    col2.metric("Iscrizioni", n_iscrizioni)
except Exception as e:
    st.error(f"Errore conteggio: {e}")

st.divider()

# =============================================================================
# CHECK 4: TEST DI SCRITTURA/LETTURA
# =============================================================================

st.markdown("## Check 4 — Test scrittura/lettura")
st.caption(
    "Inserisce un evento di prova, poi lo cancella. Serve a confermare "
    "che il modulo può scrivere effettivamente sul DB."
)

if st.button("🧪 Esegui test di scrittura", type="primary"):
    try:
        cur = conn.cursor()
        # INSERT
        cur.execute("""
            INSERT INTO ev_eventi (slug, titolo, tipo, data_ora, descrizione)
            VALUES (%s, %s, %s, NOW() + INTERVAL '7 days', %s)
            RETURNING id;
        """, (
            f"test-diagnostica-{os.urandom(4).hex()}",
            "Evento di test (cancellabile)",
            "altro",
            "Inserito dalla pagina di diagnostica. Verrà cancellato subito.",
        ))
        new_id = cur.fetchone()[0]
        st.success(f"✅ INSERT riuscito — id assegnato: {new_id}")

        # SELECT
        cur.execute("SELECT slug, titolo, tipo, data_ora FROM ev_eventi WHERE id = %s;", (new_id,))
        row = cur.fetchone()
        st.success(f"✅ SELECT riuscito — record letto:")
        st.json({
            "id": new_id,
            "slug": row[0],
            "titolo": row[1],
            "tipo": row[2],
            "data_ora": str(row[3]),
        })

        # DELETE
        cur.execute("DELETE FROM ev_eventi WHERE id = %s;", (new_id,))
        st.success(f"✅ DELETE riuscito — record di test rimosso")

        conn.commit()
        cur.close()

        st.balloons()
        st.success("🎉 Tutti i check superati: il modulo eventi è pronto.")
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"❌ Test fallito: {e}")
        st.code(traceback.format_exc())

st.divider()

# =============================================================================
# CHECK 5: TABELLA PAZIENTI ESISTE (per la futura FK)
# =============================================================================

st.markdown("## Check 5 — Aggancio Pazienti")
st.caption("Verifica che la tabella Pazienti esista e sia raggiungibile.")

try:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND lower(table_name) = 'pazienti';
    """)
    exists = cur.fetchone()[0] > 0
    if exists:
        cur.execute('SELECT COUNT(*) FROM "Pazienti";')
        n_pazienti = cur.fetchone()[0]
        st.success(f"✅ Tabella `Pazienti` trovata — contiene {n_pazienti} record")
    else:
        st.error("❌ Tabella `Pazienti` non trovata")
    cur.close()
except Exception as e:
    st.warning(f"Controllo pazienti non riuscito: {e}")

st.divider()
st.caption(
    "✅ Quando tutti i check sono verdi, puoi cancellare questo file "
    "(`pages/diagnostica_eventi.py`) dal repo e procedere con lo sviluppo del modulo."
)
