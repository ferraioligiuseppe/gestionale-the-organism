# modules/pnev/db_pnev.py
import streamlit as st
import secrets
import string
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from modules.app_core import get_connection, _DB_BACKEND

PH = "%s" if _DB_BACKEND == "postgres" else "?"
TZ = ZoneInfo("Europe/Rome")


def init_pnev_tables():
    conn = get_connection()
    cur = conn.cursor()
    if _DB_BACKEND == "sqlite":
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS pnev_token (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                paziente_id INTEGER NOT NULL,
                versione TEXT NOT NULL DEFAULT 'bambini',
                nome_paziente TEXT NOT NULL DEFAULT '',
                usato INTEGER NOT NULL DEFAULT 0,
                scadenza TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS pnev_risposte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paziente_id INTEGER NOT NULL,
                versione TEXT NOT NULL,
                token TEXT NOT NULL,
                nome_compilatore TEXT DEFAULT '',
                relazione TEXT DEFAULT '',
                dati_json TEXT NOT NULL,
                note_finali TEXT DEFAULT '',
                completato INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS pnev_token (
            id SERIAL PRIMARY KEY, token TEXT NOT NULL UNIQUE,
            paziente_id INTEGER NOT NULL, versione TEXT NOT NULL DEFAULT 'bambini',
            nome_paziente TEXT NOT NULL DEFAULT '',
            usato INTEGER NOT NULL DEFAULT 0, scadenza TEXT NOT NULL,
            created_at TEXT DEFAULT to_char(now(),'YYYY-MM-DD HH24:MI:SS'))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS pnev_risposte (
            id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL,
            versione TEXT NOT NULL, token TEXT NOT NULL,
            nome_compilatore TEXT DEFAULT '', relazione TEXT DEFAULT '',
            dati_json TEXT NOT NULL, note_finali TEXT DEFAULT '',
            completato INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT to_char(now(),'YYYY-MM-DD HH24:MI:SS'))""")
    conn.commit()
    cur.close()


# ── TOKEN OTP ─────────────────────────────────────────────────────────────────

def genera_token(paziente_id, nome_paziente, versione="bambini", ore_validita=72):
    """Genera un token alfanumerico di 8 caratteri maiuscoli."""
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(8))
    scadenza = (datetime.now(TZ) + timedelta(hours=ore_validita)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    # Invalida eventuali token precedenti non usati per lo stesso paziente+versione
    cur.execute(
        f"UPDATE pnev_token SET usato=1 WHERE paziente_id={PH} AND versione={PH} AND usato=0",
        (paziente_id, versione)
    )
    cur.execute(
        f"""INSERT INTO pnev_token (token, paziente_id, versione, nome_paziente, scadenza)
            VALUES ({PH},{PH},{PH},{PH},{PH})""",
        (token, paziente_id, versione, nome_paziente, scadenza)
    )
    conn.commit()
    cur.close()
    return token


def verifica_token(token):
    """Restituisce il record del token se valido e non scaduto, altrimenti None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM pnev_token WHERE token={PH} AND usato=0",
        (token.upper().strip(),)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    cols = [d[0] for d in cur.description]
    rec = dict(zip(cols, row))
    # Verifica scadenza
    scadenza = datetime.strptime(rec["scadenza"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
    if datetime.now(TZ) > scadenza:
        cur.close()
        return None
    cur.close()
    return rec


def get_token_paziente(paziente_id, versione):
    """Restituisce l'ultimo token attivo per un paziente."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT * FROM pnev_token
            WHERE paziente_id={PH} AND versione={PH} AND usato=0
            ORDER BY id DESC LIMIT 1""",
        (paziente_id, versione)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    cols = [d[0] for d in cur.description]
    cur.close()
    return dict(zip(cols, row))


# ── RISPOSTE ──────────────────────────────────────────────────────────────────

def salva_risposte(token, dati_json, nome_compilatore="", relazione="",
                   note_finali="", completato=False):
    """Salva le risposte del questionario pubblico."""
    import json
    rec = verifica_token(token)
    if not rec:
        return False

    conn = get_connection()
    cur = conn.cursor()

    # Controlla se esiste già un record parziale
    cur.execute(f"SELECT id FROM pnev_risposte WHERE token={PH}", (token,))
    existing = cur.fetchone()

    dati_str = json.dumps(dati_json, ensure_ascii=False)

    if existing:
        cur.execute(
            f"""UPDATE pnev_risposte SET dati_json={PH}, nome_compilatore={PH},
                relazione={PH}, note_finali={PH}, completato={PH}
                WHERE token={PH}""",
            (dati_str, nome_compilatore, relazione, note_finali,
             1 if completato else 0, token)
        )
    else:
        cur.execute(
            f"""INSERT INTO pnev_risposte
                (paziente_id, versione, token, nome_compilatore, relazione,
                 dati_json, note_finali, completato)
                VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})""",
            (rec["paziente_id"], rec["versione"], token,
             nome_compilatore, relazione, dati_str, note_finali,
             1 if completato else 0)
        )

    if completato:
        # Marca il token come usato
        cur.execute(f"UPDATE pnev_token SET usato=1 WHERE token={PH}", (token,))

    conn.commit()
    cur.close()
    return True


@st.cache_data(ttl=30)
def get_risposte_paziente(paziente_id):
    """Recupera tutte le risposte per un paziente (usato dal gestionale)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT r.*, t.nome_paziente
            FROM pnev_risposte r
            JOIN pnev_token t ON t.token = r.token
            WHERE r.paziente_id={PH}
            ORDER BY r.created_at DESC""",
        (paziente_id,)
    )
    rows = cur.fetchall()
    if not rows:
        cur.close()
        return []
    cols = [d[0] for d in cur.description]
    cur.close()
    return [dict(zip(cols, r)) for r in rows]


def get_ultima_risposta(paziente_id, versione):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""SELECT * FROM pnev_risposte
            WHERE paziente_id={PH} AND versione={PH} AND completato=1
            ORDER BY created_at DESC LIMIT 1""",
        (paziente_id, versione)
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        return None
    cols = [d[0] for d in cur.description]
    cur.close()
    return dict(zip(cols, row))
