# -*- coding: utf-8 -*-
"""
MAPS — Percorsi del paziente.

Assegna un programma a un paziente (con data di inizio) e mostra il calendario
giorno per giorno del percorso, con i checkpoint dei questionari ogni 21 giorni.
Il calendario riflette esattamente la sequenza del programma costruito.
"""
import json
import datetime
import random
import streamlit as st

try:
    import pandas as pd
except Exception:
    pd = None

CHECKPOINT_OGNI = 21  # giorni tra un questionario e l'altro

# Famiglie di brani e quante tracce ha ciascuna (nomi file: famiglia_01, famiglia_02 ...)
# I nomi esatti dei file verranno riconciliati quando i brani saranno su R2.
POOL_LAVORO = {"bach": 12, "mozart": 28, "vivaldi": 35, "celtica": 21, "jazz": 6, "country": 9, "ambient": 30}
POOL_RIPOSO = {"nature": 3, "gregoriano": 1, "ambient": 30}


def _brani(pool):
    out = []
    for fam, n in pool.items():
        for i in range(1, int(n) + 1):
            out.append(f"{fam}_{i:02d}")
    return out


def _genera_sequenza(programma_seq):
    """Genera la sequenza personale CONGELATA: per ogni passo pesca un brano vero.
    Lavoro: niente ripetizione della coppia brano+modalità nel ciclo. Growth: libero."""
    lavoro = _brani(POOL_LAVORO)
    riposo = _brani(POOL_RIPOSO)
    usate = set()
    out = []
    for i, passo in enumerate(programma_seq):
        mod = passo.get("modalita", "Potential")
        if mod == "Growth":
            brano = random.choice(riposo) if riposo else ""
        else:
            cand = [b for b in lavoro if (b, mod) not in usate]
            if not cand:
                cand = lavoro[:]  # coppie esaurite: si ricomincia
            brano = random.choice(cand) if cand else ""
            if brano:
                usate.add((brano, mod))
        out.append({
            "ordine": i + 1,
            "modalita": mod,
            "brano": brano,
            "binaurale": passo.get("binaurale", "no"),
            "pattern": passo.get("pattern", ""),
        })
    return out


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
    if _is_postgres(conn):
        cur.execute("""
        CREATE TABLE IF NOT EXISTS percorsi_ascolto (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT,
            programma_id BIGINT,
            data_inizio TEXT,
            stato TEXT,
            sequenza_json TEXT,
            created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS percorsi_ascolto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER,
            programma_id INTEGER,
            data_inizio TEXT,
            stato TEXT,
            sequenza_json TEXT,
            created_at TEXT
        )""")
    try:
        conn.commit()
    except Exception:
        pass
    _ensure_columns(conn)


def _ensure_columns(conn):
    """Aggiunge sequenza_json alle tabelle già esistenti senza quella colonna."""
    cur = conn.cursor()
    if _is_postgres(conn):
        try:
            cur.execute("ALTER TABLE percorsi_ascolto ADD COLUMN IF NOT EXISTS sequenza_json TEXT")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    else:
        try:
            cur.execute("ALTER TABLE percorsi_ascolto ADD COLUMN sequenza_json TEXT")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass  # colonna già presente


def _programmi(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nome, livello, condizione, durata_brano_min, sequenza_json "
                    "FROM programmi_ascolto ORDER BY nome")
        return cur.fetchall()
    except Exception:
        return []


def _programma_by_id(conn, pid):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT id, nome, durata_brano_min, sequenza_json FROM programmi_ascolto WHERE id = {ph}", (pid,))
        return cur.fetchone()
    except Exception:
        return None


def _assegna(conn, paz_id, prog_id, data_inizio, sequenza_json):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    cur.execute(
        f"""INSERT INTO percorsi_ascolto (paziente_id, programma_id, data_inizio, stato, sequenza_json, created_at)
            VALUES ({ph},{ph},{ph},{ph},{ph},{ph})""",
        (paz_id, prog_id, data_inizio, "attivo", sequenza_json,
         datetime.datetime.now().isoformat(timespec="seconds")))
    try:
        conn.commit()
    except Exception:
        pass


def _percorsi_paziente(conn, paz_id):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    try:
        cur.execute(f"""SELECT id, programma_id, data_inizio, stato, sequenza_json, created_at
                        FROM percorsi_ascolto WHERE paziente_id = {ph}
                        ORDER BY id DESC""", (paz_id,))
        return cur.fetchall()
    except Exception:
        return []


def _elimina_percorso(conn, pid):
    pg = _is_postgres(conn)
    ph = "%s" if pg else "?"
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM percorsi_ascolto WHERE id = {ph}", (pid,))
        conn.commit()
    except Exception:
        pass


def _g(row, i, key):
    """Legge una colonna sia da tuple sia da Row."""
    try:
        return row[key] if hasattr(row, "keys") else row[i]
    except Exception:
        try:
            return row[i]
        except Exception:
            return None


def ui_percorsi(conn=None):
    st.header("🧭 Percorsi MAPS")
    st.caption("Assegna un programma a un paziente e segui il suo calendario di ascolto.")

    if conn is None:
        conn = _get_conn()
    _ensure_table(conn)

    # paziente attivo (lettura silenziosa)
    paz_id, nome = None, ""
    try:
        from modules.paziente_attivo import paziente_attivo_id, paziente_attivo_record
        paz_id = paziente_attivo_id()
        rec = paziente_attivo_record() or {}
        nome = (str(rec.get("cognome", "")) + " " + str(rec.get("nome", ""))).strip()
    except Exception:
        pass

    if not paz_id:
        st.info("Seleziona un paziente per gestire il suo percorso.")
        return

    st.markdown(f"Paziente: **{nome or paz_id}**")

    programmi = _programmi(conn)
    if not programmi:
        st.warning("Non ci sono ancora programmi. Vai in «🗂 Programmi MAPS» e creane uno.")
        return

    # --- ASSEGNA ---
    st.subheader("Assegna un programma")
    nomi = {f"{_g(p,1,'nome')} — {_g(p,2,'livello')} · {_g(p,3,'condizione')}": _g(p, 0, "id") for p in programmi}
    c1, c2 = st.columns([2, 1])
    scelta = c1.selectbox("Programma", list(nomi.keys()))
    data_inizio = c2.date_input("Data di inizio", value=datetime.date.today())
    if st.button("➕ Assegna al paziente", type="primary"):
        prog_scelto = _programma_by_id(conn, nomi[scelta])
        try:
            prog_seq = json.loads(_g(prog_scelto, 3, "sequenza_json") or "[]")
        except Exception:
            prog_seq = []
        seq_concreta = _genera_sequenza(prog_seq)
        _assegna(conn, paz_id, nomi[scelta], data_inizio.isoformat(),
                 json.dumps(seq_concreta, ensure_ascii=False))
        st.success(f"Programma «{scelta.split(' — ')[0]}» assegnato a {nome or paz_id}. "
                   f"Sequenza personale generata ({len(seq_concreta)} giorni).")
        st.rerun()

    # --- PERCORSI DEL PAZIENTE ---
    st.divider()
    percorsi = _percorsi_paziente(conn, paz_id)
    if not percorsi:
        st.info("Nessun percorso assegnato a questo paziente.")
        return

    st.subheader("Percorso attivo")
    attivo = percorsi[0]
    prog_id = _g(attivo, 1, "programma_id")
    data_str = _g(attivo, 2, "data_inizio")
    prog = _programma_by_id(conn, prog_id)
    if not prog:
        st.error("Il programma collegato non esiste più.")
        return

    prog_nome = _g(prog, 1, "nome")
    durata_brano = _g(prog, 2, "durata_brano_min") or 30
    # sequenza CONGELATA del percorso (brani veri); fallback al programma (solo modalità) se assente
    seq_congelata = _g(attivo, 4, "sequenza_json")
    sequenza, congelata = [], False
    if seq_congelata:
        try:
            sequenza = json.loads(seq_congelata)
            congelata = True
        except Exception:
            sequenza = []
    if not sequenza:
        try:
            sequenza = json.loads(_g(prog, 3, "sequenza_json") or "[]")
        except Exception:
            sequenza = []
    try:
        d0 = datetime.date.fromisoformat(str(data_str)[:10])
    except Exception:
        d0 = datetime.date.today()

    def _brano_txt(passo):
        b = passo.get("brano", "")
        if congelata and b:
            return b
        return "casuale (riposo)" if passo.get("modalita") == "Growth" else "casuale (lavoro)"

    n = len(sequenza)
    oggi = datetime.date.today()
    giorno_corrente = (oggi - d0).days + 1

    st.markdown(f"**{prog_nome}** · inizio {d0.strftime('%d/%m/%Y')} · {n} giorni · brani da {durata_brano} min")
    if 1 <= giorno_corrente <= n:
        st.progress(giorno_corrente / n, text=f"Giorno {giorno_corrente} di {n}")
        passo = sequenza[giorno_corrente - 1]
        bina = passo.get("binaurale", "no")
        bina_txt = ""
        if bina and bina != "no":
            bina_txt = f" · binaurale {bina}" + (f" ({passo.get('pattern')})" if passo.get("pattern") else "")
        st.info(f"**Oggi (giorno {giorno_corrente}):** modalità **{passo.get('modalita','')}**"
                + f" · brano: {_brano_txt(passo)}"
                + bina_txt)
    elif giorno_corrente < 1:
        st.info(f"Il percorso inizia il {d0.strftime('%d/%m/%Y')} (tra {1 - giorno_corrente} giorni).")
    else:
        st.success("Percorso completato. 🎉")

    # calendario
    if pd is not None:
        righe = []
        for i, passo in enumerate(sequenza):
            g = i + 1
            data_g = d0 + datetime.timedelta(days=i)
            check = "📋 questionario" if g % CHECKPOINT_OGNI == 0 else ""
            bina = passo.get("binaurale", "no")
            bina_txt = "—"
            if bina and bina != "no":
                bina_txt = bina + (f" {passo.get('pattern')}" if passo.get("pattern") else "")
            righe.append({
                "Giorno": g,
                "Data": data_g.strftime("%d/%m/%Y"),
                "Modalità": passo.get("modalita", ""),
                "Brano": _brano_txt(passo),
                "Binaurale": bina_txt,
                "Checkpoint": check,
                "Oggi": "👉" if g == giorno_corrente else "",
            })
        with st.expander("📅 Calendario completo", expanded=False):
            st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

    # storico
    if len(percorsi) > 1:
        with st.expander("Percorsi precedenti"):
            for p in percorsi[1:]:
                pid = _g(p, 0, "id")
                di = _g(p, 2, "data_inizio")
                cc1, cc2 = st.columns([5, 1])
                cc1.write(f"Percorso del {str(di)[:10]} · stato {_g(p,3,'stato')}")
                if cc2.button("Elimina", key=f"delp_{pid}"):
                    _elimina_percorso(conn, pid)
                    st.rerun()
