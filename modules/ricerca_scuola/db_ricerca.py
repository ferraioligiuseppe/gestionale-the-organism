# -*- coding: utf-8 -*-
"""
modules/ricerca_scuola/db_ricerca.py

PNEV Academy · Ricerca scuola — strato dati.

Dati di ricerca ANONIMI raccolti dai giochi in classe. Sono separati di proposito
dall'archivio clinico: nessuna tabella qui contiene nomi, né rimanda ai pazienti.
L'alunno è solo un codice (es. "5A-07"); la corrispondenza codice ↔ nome resta
all'insegnante, su carta.

Tabelle (tutte con studio_id e RLS, come il resto del gestionale):
  ric_sperimentazioni  — il progetto (es. «Validazione PNEV Games – quinta primaria»)
  ric_classi           — le classi coinvolte, ognuna con un codice classe da digitare sul tablet
  ric_alunni           — i codici alunno di ogni classe
  ric_sessioni         — una riga per partita, inviata dai giochi

Usato sia dal gestionale (Streamlit) sia dal servizio dati (apps/ricerca_api.py).
"""

import json
import secrets
import string

GRUPPI = ["sperimentale", "controllo", "unico"]

# Alfabeto dei codici classe: niente 0/O, 1/I/L per non confondere chi li digita
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _righe(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


_TABELLE = ("ric_sperimentazioni", "ric_classi", "ric_alunni", "ric_sessioni")


def _gia_pronte(cur):
    """True se le quattro tabelle esistono già con RLS attiva: allora non si tocca nulla
    (niente ALTER TABLE a ogni avvio, che chiederebbe un lock esclusivo)."""
    cur.execute("""SELECT count(*) FROM pg_class
                   WHERE relname = ANY(%s) AND relkind = 'r'
                     AND relrowsecurity AND relforcerowsecurity""", (list(_TABELLE),))
    return cur.fetchone()[0] == len(_TABELLE)


def _rls(cur, tabella):
    cur.execute("SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE relname = %s AND relkind = 'r'",
                (tabella,))
    r = cur.fetchone()
    if not (r and r[0]):
        cur.execute(f"ALTER TABLE {tabella} ENABLE ROW LEVEL SECURITY;")
        cur.execute(f"ALTER TABLE {tabella} FORCE ROW LEVEL SECURITY;")
    cur.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies
                           WHERE tablename = '{tabella}' AND policyname = '{tabella}_studio') THEN
                CREATE POLICY {tabella}_studio ON {tabella}
                    USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                    WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
            END IF;
        END $$;
    """)


def init_ricerca_db(conn):
    """Crea le tabelle se mancano. Idempotente."""
    cur = conn.cursor()
    try:
        if _gia_pronte(cur):
            conn.commit()
            return
        sid = "BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint"
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS ric_sperimentazioni (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   {sid},
                titolo      TEXT NOT NULL,
                descrizione TEXT,
                scuola      TEXT,
                referenti   TEXT,
                attiva      BOOLEAN NOT NULL DEFAULT TRUE,
                creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS ric_classi (
                id                 BIGSERIAL PRIMARY KEY,
                studio_id          {sid},
                sperimentazione_id BIGINT NOT NULL REFERENCES ric_sperimentazioni(id) ON DELETE CASCADE,
                nome               TEXT NOT NULL,
                codice_classe      TEXT NOT NULL UNIQUE,
                gruppo             TEXT NOT NULL DEFAULT 'unico',
                insegnante         TEXT,
                attiva             BOOLEAN NOT NULL DEFAULT TRUE,
                creato_il          TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS ric_alunni (
                id         BIGSERIAL PRIMARY KEY,
                studio_id  {sid},
                classe_id  BIGINT NOT NULL REFERENCES ric_classi(id) ON DELETE CASCADE,
                codice     TEXT NOT NULL,
                attivo     BOOLEAN NOT NULL DEFAULT TRUE,
                creato_il  TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (classe_id, codice)
            );
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS ric_sessioni (
                id            BIGSERIAL PRIMARY KEY,
                studio_id     {sid},
                classe_id     BIGINT NOT NULL REFERENCES ric_classi(id) ON DELETE CASCADE,
                codice_alunno TEXT NOT NULL,
                gioco         TEXT NOT NULL,
                livello       TEXT,
                condizione    TEXT,
                err_pct       NUMERIC(5,2),
                corrette      INTEGER,
                totali        INTEGER,
                durata_s      NUMERIC(8,2),
                metriche      JSONB,
                dispositivo   TEXT,
                client_id     TEXT UNIQUE,
                giocata_il    TIMESTAMPTZ,
                ricevuta_il   TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_ric_sessioni_classe ON ric_sessioni (classe_id, giocata_il);")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_ric_sessioni_alunno ON ric_sessioni (classe_id, codice_alunno);")
        for t in _TABELLE:
            _rls(cur, t)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try: cur.close()
        except Exception: pass


# ── Sperimentazioni ─────────────────────────────────────────────────────
def crea_sperimentazione(conn, titolo, descrizione=None, scuola=None, referenti=None):
    cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO ric_sperimentazioni (titolo, descrizione, scuola, referenti)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (titolo.strip(), descrizione, scuola, referenti))
        nid = cur.fetchone()[0]
        conn.commit()
        return nid
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()


def lista_sperimentazioni(conn):
    cur = conn.cursor()
    try:
        cur.execute("""SELECT s.id, s.titolo, s.descrizione, s.scuola, s.referenti, s.attiva, s.creato_il,
                              (SELECT count(*) FROM ric_classi c WHERE c.sperimentazione_id = s.id) AS n_classi
                       FROM ric_sperimentazioni s ORDER BY s.creato_il DESC""")
        return _righe(cur)
    finally:
        cur.close()


# ── Classi e codici ─────────────────────────────────────────────────────
def _nuovo_codice_classe(cur):
    for _ in range(20):
        c = "".join(secrets.choice(_ALFABETO) for _ in range(6))
        cur.execute("SELECT 1 FROM ric_classi WHERE codice_classe = %s", (c,))
        if not cur.fetchone():
            return c
    raise RuntimeError("Impossibile generare un codice classe libero")


def crea_classe(conn, sperimentazione_id, nome, n_alunni, gruppo="unico", insegnante=None):
    """Crea la classe, il suo codice e i codici alunno (prefisso-01 … prefisso-NN)."""
    nome = nome.strip()
    prefisso = "".join(ch for ch in nome.upper() if ch in string.ascii_uppercase + string.digits)[:6] or "AL"
    cur = conn.cursor()
    try:
        codice = _nuovo_codice_classe(cur)
        cur.execute("""INSERT INTO ric_classi (sperimentazione_id, nome, codice_classe, gruppo, insegnante)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (sperimentazione_id, nome, codice, gruppo if gruppo in GRUPPI else "unico", insegnante))
        cid = cur.fetchone()[0]
        for i in range(1, int(n_alunni) + 1):
            cur.execute("INSERT INTO ric_alunni (classe_id, codice) VALUES (%s, %s)",
                        (cid, f"{prefisso}-{i:02d}"))
        conn.commit()
        return cid, codice
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()


def aggiungi_alunni(conn, classe_id, quanti):
    cur = conn.cursor()
    try:
        cur.execute("SELECT nome FROM ric_classi WHERE id = %s", (classe_id,))
        nome = cur.fetchone()[0]
        prefisso = "".join(ch for ch in nome.upper() if ch in string.ascii_uppercase + string.digits)[:6] or "AL"
        cur.execute("SELECT count(*) FROM ric_alunni WHERE classe_id = %s", (classe_id,))
        n = cur.fetchone()[0]
        for i in range(n + 1, n + int(quanti) + 1):
            cur.execute("INSERT INTO ric_alunni (classe_id, codice) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (classe_id, f"{prefisso}-{i:02d}"))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()


def lista_classi(conn, sperimentazione_id):
    cur = conn.cursor()
    try:
        cur.execute("""SELECT c.id, c.nome, c.codice_classe, c.gruppo, c.insegnante, c.attiva,
                              (SELECT count(*) FROM ric_alunni a WHERE a.classe_id = c.id) AS n_alunni,
                              (SELECT count(*) FROM ric_sessioni s WHERE s.classe_id = c.id) AS n_sessioni,
                              (SELECT max(s.ricevuta_il) FROM ric_sessioni s WHERE s.classe_id = c.id) AS ultima
                       FROM ric_classi c WHERE c.sperimentazione_id = %s ORDER BY c.nome""",
                    (sperimentazione_id,))
        return _righe(cur)
    finally:
        cur.close()


def lista_alunni(conn, classe_id):
    cur = conn.cursor()
    try:
        cur.execute("SELECT codice, attivo FROM ric_alunni WHERE classe_id = %s ORDER BY codice", (classe_id,))
        return _righe(cur)
    finally:
        cur.close()


def imposta_classe_attiva(conn, classe_id, attiva):
    cur = conn.cursor()
    try:
        cur.execute("UPDATE ric_classi SET attiva = %s WHERE id = %s", (bool(attiva), classe_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()


# ── Sessioni ────────────────────────────────────────────────────────────
def classe_da_codice(conn, codice_classe):
    """Ritorna {id, nome, attiva, alunni:[...]} oppure None."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nome, attiva FROM ric_classi WHERE codice_classe = %s",
                    ((codice_classe or "").strip().upper(),))
        r = cur.fetchone()
        if not r:
            return None
        cur.execute("SELECT codice FROM ric_alunni WHERE classe_id = %s AND attivo ORDER BY codice", (r[0],))
        return {"id": r[0], "nome": r[1], "attiva": r[2], "alunni": [x[0] for x in cur.fetchall()]}
    finally:
        cur.close()


def salva_sessione_ricerca(conn, classe_id, s):
    """s: dict già validato dal servizio dati. Ritorna True se salvata, False se già presente."""
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ric_sessioni (classe_id, codice_alunno, gioco, livello, condizione, err_pct,
                                      corrette, totali, durata_s, metriche, dispositivo, client_id, giocata_il)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, to_timestamp(%s / 1000.0))
            ON CONFLICT (client_id) DO NOTHING
            RETURNING id
        """, (classe_id, s["alunno"], s["gioco"], s.get("livello"), s.get("condizione"), s.get("err_pct"),
              s.get("corrette"), s.get("totali"), s.get("durata_s"),
              json.dumps(s["metriche"]) if s.get("metriche") else None,
              s.get("dispositivo"), s["client_id"], s["t"]))
        nuova = cur.fetchone() is not None
        conn.commit()
        return nuova
    except Exception:
        conn.rollback(); raise
    finally:
        cur.close()


def sessioni_classe(conn, classe_ids):
    if not classe_ids:
        return []
    cur = conn.cursor()
    try:
        cur.execute("""SELECT c.nome AS classe, c.gruppo, s.codice_alunno, s.gioco, s.livello, s.condizione,
                              s.err_pct, s.corrette, s.totali, s.durata_s, s.giocata_il, s.ricevuta_il,
                              s.dispositivo, s.metriche
                       FROM ric_sessioni s JOIN ric_classi c ON c.id = s.classe_id
                       WHERE s.classe_id = ANY(%s)
                       ORDER BY s.giocata_il""", (list(classe_ids),))
        return _righe(cur)
    finally:
        cur.close()
