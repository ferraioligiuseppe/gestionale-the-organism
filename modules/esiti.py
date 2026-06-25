# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  ESITI / FOLLOW-UP — imparare dagli errori (Mattone B)              ║
║                                                                      ║
║  Per ogni intervento si registra l'ESITO: migliorato, fermo,        ║
║  peggiorato, non valutabile — con note. Questi esiti entrano nello   ║
║  storico letto dall'AI: così l'Assistente e la Diagnosi tengono     ║
║  conto di ciò che ha funzionato o NO per quel paziente, e correggono ║
║  il tiro. È la base concreta dell'"imparare dagli errori".          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

ESITI = ["🟢 Migliorato", "🟡 Stabile / fermo", "🔴 Peggiorato", "⚪ Non valutabile"]

try:
    from .quadro_storico import carica_paziente, _fmt
except Exception:
    def carica_paziente(conn, paz_id):
        return None
    def _fmt(dt):
        try:
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return str(dt) if dt else ""


def _assicura_tabella(conn):
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS esiti_pnev(
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT,
            data TIMESTAMP DEFAULT NOW(),
            intervento TEXT, esito TEXT, note TEXT);""")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def render_esiti(conn=None, paz_id=None, paziente=None):
    st.header("📈 Esiti / Follow-up")
    st.caption("Registra com'è andato ogni intervento. Questi esiti entrano nello "
               "storico: l'AI ne tiene conto per non ripetere ciò che non ha funzionato.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    _assicura_tabella(conn)

    with st.expander("➕ Registra un esito", expanded=True):
        with st.form("esito_form", clear_on_submit=True):
            intervento = st.text_input("Intervento / terapia valutata",
                                       placeholder="es. Vision Therapy 8 sedute, MAPS, osteopatia…")
            esito = st.radio("Esito", ESITI, horizontal=True)
            note = st.text_area("Note (cosa è migliorato/peggiorato, perché)", height=90)
            if st.form_submit_button("💾 Salva esito", type="primary"):
                if intervento.strip():
                    if _salva(conn, paz_id, intervento, esito, note):
                        st.success("Esito registrato.")
                        st.rerun()
                    else:
                        st.error("Salvataggio non riuscito.")
                else:
                    st.warning("Indica almeno l'intervento.")

    st.markdown("#### Storico esiti")
    _elenco(conn, paz_id)


def _salva(conn, paz_id, intervento, esito, note) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO esiti_pnev(paziente_id, intervento, esito, note) "
                    "VALUES(%s,%s,%s,%s)", (paz_id, intervento, esito, note or ""))
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _elenco(conn, paz_id):
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, data, intervento, esito, note FROM esiti_pnev "
                    "WHERE paziente_id=%s ORDER BY data DESC", (paz_id,))
        righe = cur.fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        righe = []
    if not righe:
        st.caption("Nessun esito registrato per ora.")
        return
    for rid, data, interv, esito, note in righe:
        st.markdown(f"**{esito}** — {interv}  ·  _{_fmt(data)}_")
        if note:
            st.caption(note)
        if st.button("🗑 Elimina", key=f"esito_del_{rid}"):
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM esiti_pnev WHERE id=%s", (rid,))
                conn.commit()
                st.rerun()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #eee'>",
                    unsafe_allow_html=True)
