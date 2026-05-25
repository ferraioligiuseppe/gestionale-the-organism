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
MODALITA = ["Potential", "Focus", "Motor", "Ricarica", "Growth"]
# Bande binaurali (frequenza del battito): delta ~2 Hz, theta ~6 Hz, alfa ~10 Hz, beta ~16 Hz, gamma ~40 Hz
BANDE = ["no", "delta", "theta", "alfa", "beta", "gamma"]

# --- Sequenze standard dallo schema MAPS (4 programmi Potential) ---
_LET = {"b": "Potential", "f": "Focus", "m": "Motor", "r": "Ricarica"}


def _seq_da_lettere(lettere, brani=None):
    out = []
    for i, L in enumerate(lettere):
        b = (brani[i] if brani and i < len(brani) else "")
        out.append((_LET.get(L, "Potential"), b))
    return out


def _growth_ogni_4(seq):
    """Inserisce un passo Growth dopo ogni 4 brani di lavoro (pausa di crescita)."""
    out, c = [], 0
    for m, b in seq:
        out.append((m, b))
        c += 1
        if c % 4 == 0:
            out.append(("Growth", ""))
    return out


_P1_BRANI = None  # i brani non si assegnano: vengono pescati a caso (lavoro o riposo)

SEED_POTENTIAL = [
    ("Potential 1", _seq_da_lettere(list("bbbbbbrbrbrbmbmbfbfbr"))),
    ("Potential 2", _seq_da_lettere(list("mbbbrfrbrbfbfbrbfbfrb"))),
    ("Potential 3", _seq_da_lettere(list("bfrbbfrbmfbbmrbffrbfb"))),
    ("Potential 4", _seq_da_lettere(list("bfrfrbrfmbrbrfbrrfbrb"))),
]


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


def _nome_esiste(conn, nome):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM programmi_ascolto WHERE nome = {ph} LIMIT 1", (nome,))
        return cur.fetchone() is not None
    except Exception:
        return False


def _semina_potential(conn):
    creati = 0
    for nome, seq in SEED_POTENTIAL:
        if _nome_esiste(conn, nome):
            continue
        seqg = _growth_ogni_4(seq)
        sequenza = [{"ordine": i + 1, "modalita": m, "binaurale": "no", "pattern": ""}
                    for i, (m, b) in enumerate(seqg)]
        _salva(conn, {
            "nome": nome, "livello": "Potential", "condizione": "Generico",
            "durata_giorni": len(sequenza), "durata_brano_min": 30,
            "sequenza_json": json.dumps(sequenza, ensure_ascii=False),
            "note": "Seminato dallo schema MAPS (Growth ogni 4 brani)",
        })
        creati += 1
    return creati


def _semina_percorso_104(conn):
    """Crea UN unico percorso di 104 giorni: le 4 sequenze Potential concatenate in fila."""
    nome = "Percorso completo 104 giorni"
    if _nome_esiste(conn, nome):
        return 0
    sequenza, ordine = [], 0
    for _, seq in SEED_POTENTIAL:
        for (m, b) in _growth_ogni_4(seq):
            ordine += 1
            sequenza.append({"ordine": ordine, "modalita": m, "binaurale": "no", "pattern": ""})
    _salva(conn, {
        "nome": nome, "livello": "Potential", "condizione": "Generico",
        "durata_giorni": len(sequenza), "durata_brano_min": 30,
        "sequenza_json": json.dumps(sequenza, ensure_ascii=False),
        "note": "Percorso unico: Potential 1-2-3-4 in fila. Brano scelto fresco ogni giorno.",
    })
    return len(sequenza)


def ui_programmi(conn=None):
    st.header("🗂 Programmi MAPS — costruttore")
    st.caption("Crea e salva i percorsi di ascolto. Ogni programma è una sequenza di passi (modalità + brano).")

    if conn is None:
        conn = _get_conn()
    _ensure_table(conn)

    if pd is None:
        st.error("Manca la libreria pandas: non posso mostrare l'editor della sequenza.")
        return

    st.subheader("📥 Programmi pronti")
    st.write("Crea con un clic i 4 programmi **Potential** (1–4) dello schema MAPS, "
             "con un passo **Growth** ogni 4 brani. Nascono già pronti; poi puoi "
             "modificarli o aggiungerne altri qui sotto.")
    if st.button("📥 Semina i 4 Potential standard", type="primary"):
        n = _semina_potential(conn)
        if n:
            st.success(f"Creati {n} programmi Potential standard (Growth ogni 4 brani). Li trovi nell'elenco in fondo.")
        else:
            st.info("I programmi Potential standard esistono già (vedi l'elenco in fondo alla pagina).")
        st.rerun()

    st.write("Oppure crea **un unico percorso di 104 giorni** (Potential 1-2-3-4 in fila): "
             "lo assegni una volta sola e copre l'intero ciclo. Il brano di ogni giorno è scelto "
             "**fresco** al momento dell'ascolto, per non far abituare il cervello.")
    if st.button("📥 Semina il Percorso completo 104 giorni"):
        n = _semina_percorso_104(conn)
        if n:
            st.success(f"Creato il «Percorso completo 104 giorni» ({n} giorni). Lo trovi nell'elenco in fondo.")
        else:
            st.info("Il «Percorso completo 104 giorni» esiste già (vedi l'elenco in fondo).")
        st.rerun()

    st.divider()
    st.subheader("Nuovo programma")
    c1, c2, c3 = st.columns(3)
    nome = c1.text_input("Nome del programma", value="Potential generico")
    livello = c2.selectbox("Livello", LIVELLI, index=0)
    condizione = c3.selectbox("Condizione", CONDIZIONI, index=0)
    c4, c5 = st.columns(2)
    durata_giorni = c4.number_input("Durata (giorni)", min_value=1, max_value=365, value=84)
    durata_brano = c5.number_input("Durata di ogni brano (minuti)", min_value=1, max_value=180, value=30)

    st.markdown("**Sequenza dei passi** — modalità per ciascun passo (puoi aggiungere o togliere righe):")
    st.caption("Il programma definisce solo il **tipo** di ogni passo (Potential, Focus, Motor, Ricarica, Growth). "
               "Il brano vero è scelto a caso al momento dell'ascolto, da una raccolta dedicata (lavoro o riposo). "
               "Binaurale: scegli la banda (o «no») e il pattern in minuti acceso/spento, es. «10/10/10». Spento di default.")
    n_default = 21
    df = pd.DataFrame({
        "ordine": list(range(1, n_default + 1)),
        "modalità": ["Potential"] * n_default,
        "binaurale": ["no"] * n_default,
        "pattern": [""] * n_default,
    })
    try:
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, hide_index=True,
            column_config={
                "ordine": st.column_config.NumberColumn("Passo", disabled=True),
                "modalità": st.column_config.SelectboxColumn("Modalità", options=MODALITA, required=True),
                "binaurale": st.column_config.SelectboxColumn("Binaurale", options=BANDE, required=True),
                "pattern": st.column_config.TextColumn("Pattern (min)"),
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
                    "binaurale": str(r.get("binaurale", "no") or "no"),
                    "pattern": str(r.get("pattern", "") or ""),
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
