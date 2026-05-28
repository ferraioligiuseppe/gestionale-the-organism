# -*- coding: utf-8 -*-
"""
Modulo Esercizi Wordwall
=========================
Permette di associare alla scheda di un paziente delle attività Wordwall
(create dal professionista sul proprio account Wordwall) e di renderle
giocabili direttamente dentro il gestionale.

PASSO 1 (questo file): creazione della tabella `wordwall_esercizi`.
I passi successivi aggiungeranno: form di inserimento + lista, e il player.

Convenzioni rispettate dal resto dell'app:
- connessione via get_connection() -> wrapper _PgConn con .cursor()/.commit()
- placeholder %s
- tabella pazienti = Pazienti (id), colonna di collegamento = paziente_id
- paziente attivo in st.session_state["paziente_attivo_id"]
"""

import streamlit as st


# ---------------------------------------------------------------------------
# PASSO 1 — schema
# ---------------------------------------------------------------------------
def init_wordwall_table(conn) -> None:
    """Crea la tabella degli esercizi Wordwall se non esiste ancora.

    Idempotente: usa IF NOT EXISTS, quindi può essere chiamata a ogni avvio
    senza effetti collaterali.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wordwall_esercizi (
                id              SERIAL PRIMARY KEY,
                paziente_id     INTEGER NOT NULL,
                titolo          TEXT NOT NULL,
                area            TEXT,
                wordwall_url    TEXT NOT NULL,
                note            TEXT,
                attivo          BOOLEAN DEFAULT TRUE,
                data_creazione  TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wordwall_paziente
            ON wordwall_esercizi (paziente_id)
            """
        )
        conn.commit()
    finally:
        cur.close()


def _ensure_schema(conn) -> None:
    """Esegue init_wordwall_table una sola volta per sessione Streamlit."""
    if not st.session_state.get("_wordwall_schema_ok"):
        init_wordwall_table(conn)
        st.session_state["_wordwall_schema_ok"] = True


# ---------------------------------------------------------------------------
# Render (scheletro — verrà completato nei passi 2 e 3)
# ---------------------------------------------------------------------------
def render_wordwall(conn, paziente_id: int) -> None:
    """Pagina Esercizi Wordwall per il paziente attivo."""
    _ensure_schema(conn)

    st.subheader("🎮 Esercizi Wordwall")
    st.caption(
        "Modulo in costruzione. Passo 1 completato: tabella pronta."
    )
