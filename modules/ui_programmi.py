# -*- coding: utf-8 -*-
"""
MAPS — Costruttore di programmi di ascolto.

Definisce e salva nel database i programmi (lo "scaffale"): ogni programma ha
nome, livello, condizione, durata e una sequenza di passi (modalita + brano).
Stesso stile di creazione tabella degli altri moduli (PostgreSQL / SQLite).
"""
import json
import datetime
import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None

LIVELLI = ["Potential", "Boost", "High Performance"]
CONDIZIONI = ["Generico", "Dislessia", "Disprassia", "ADHD", "Deficit attentivo", "Autismo"]
MODALITA = ["Potential", "Focus", "Motor", "Ricarica"]


def _get_conn():
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import get_connection
        return get_connection()
    except Exception:
        pass
    import sqlite3
    c = sqlite3.connect("organism.db")
    c.row_factory = sqlite3.Row
    return c


def _is_postgres(conn):
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception:
        pass
    return False


def _ensure_table(conn):
    cur = conn.cursor()
    pg = _is_postgres(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS programmi_ascolto (
            id BIGSERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            livello TEXT,
            condizione TEXT,
            durata_giorni INTEGER,
            durata_brano_min INTEGER,
            sequenza_json TEXT,
            note TEXT,
            created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS programmi_ascolto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            livello TEXT,
            condizione TEXT,
            durata_giorni INTEGER,
            durata_brano_min INTEGER,
            sequenza_json TEXT,
            note TEXT,
            created_at TEXT
        )""")
    try:
        conn.commit()
    except Exception:
        pass


def _salva(conn, dati):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    cur.execute(
        f"""INSERT INTO programmi_ascolto
            (nome, livello, condizione, durata_giorni, durata_brano_min, sequenza_json, note, created_at)
            VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})""",
        (dati["nome"], dati["livello"], dati["condizione"], dati["durata_giorni"],
         dati["durata_brano_min"], dati["sequenza_json"], dati.get("note", ""),
         datetime.datetime.now().isoformat(timespec="seconds")))
    try:
        conn.commit()
    except Exception:
        pass


def _lista(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nome, livello, condizione, durata_giorni, durata_brano_min, created_at "
                    "FROM programmi_ascolto ORDER BY id DESC")
        return cur.fetchall()
    except Exception:
        return []


def _elimina(conn, pid):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM programmi_ascolto WHERE id = {ph}", (pid,))
        conn.commit()
    except Exception:
        pass


def ui_programmi(conn=None):
    st.header("🗂 Programmi MAPS — costruttore")
    st.caption("Crea e salva i percorsi di ascolto. Ogni programma è una sequenza di passi (modalità + brano).")

    if conn is None:
        conn = _get_conn()
    _ensure_table(conn)

    if pd is None:
        st.error("Manca la libreria pandas: non posso mostrare l'editor della sequenza.")
        return

    st.subheader("Nuovo programma")
    c1, c2, c3 = st.columns(3)
    nome = c1.text_input("Nome del programma", value="Potential generico")
    livello = c2.selectbox("Livello", LIVELLI, index=0)
    condizione = c3.selectbox("Condizione", CONDIZIONI, index=0)
    c4, c5 = st.columns(2)
    durata_giorni = c4.number_input("Durata (giorni)", min_value=1, max_value=365, value=84)
    durata_brano = c5.number_input("Durata di ogni brano (minuti)", min_value=1, max_value=180, value=30)

    st.markdown("**Sequenza dei passi** — modalità e brano per ciascun passo (puoi aggiungere o togliere righe):")
    n_default = 21
    df = pd.DataFrame({
        "ordine": list(range(1, n_default + 1)),
        "modalità": ["Potential"] * n_default,
        "brano": [""] * n_default,
    })
    try:
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "ordine": st.column_config.NumberColumn("Passo", disabled=True),
                "modalità": st.column_config.SelectboxColumn("Modalità", options=MODALITA, required=True),
                "brano": st.column_config.TextColumn("Brano"),
            },
            key="seq_editor",
        )
    except Exception:
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="seq_editor_fallback")

    note = st.text_area("Note (facoltative)", value="")

    if st.button("💾 Salva programma", type="primary"):
        if not nome.strip():
            st.warning("Dai un nome al programma.")
        else:
            try:
                righe = edited.to_dict("records")
            except Exception:
                righe = []
            sequenza = []
            for i, r in enumerate(righe, start=1):
                sequenza.append({
                    "ordine": i,
                    "modalita": str(r.get("modalità", "Potential")),
                    "brano": str(r.get("brano", "") or ""),
                })
            _salva(conn, {
                "nome": nome.strip(), "livello": livello, "condizione": condizione,
                "durata_giorni": int(durata_giorni), "durata_brano_min": int(durata_brano),
                "sequenza_json": json.dumps(sequenza, ensure_ascii=False), "note": note.strip(),
            })
            st.success(f"Programma «{nome.strip()}» salvato ({len(sequenza)} passi).")
            st.rerun()

    st.divider()
    st.subheader("Programmi salvati")
    righe = _lista(conn)
    if not righe:
        st.info("Nessun programma salvato. Creane uno qui sopra.")
        return
    for r in righe:
        rid = r[0] if not hasattr(r, "keys") else r["id"]
        nome_p = r[1] if not hasattr(r, "keys") else r["nome"]
        liv = r[2] if not hasattr(r, "keys") else r["livello"]
        cond = r[3] if not hasattr(r, "keys") else r["condizione"]
        gg = r[4] if not hasattr(r, "keys") else r["durata_giorni"]
        bm = r[5] if not hasattr(r, "keys") else r["durata_brano_min"]
        cc1, cc2 = st.columns([6, 1])
        cc1.markdown(f"**{nome_p}** — {liv} · {cond} · {gg} giorni · brani da {bm} min")
        if cc2.button("Elimina", key=f"del_{rid}"):
            _elimina(conn, rid)
            st.rerun()
