# -*- coding: utf-8 -*-
"""
db_raven.py - Persistenza del modulo Matrici di Raven (CPM, SPM).
Convenzioni gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
ZoneInfo("Europe/Rome"), multi-tenant con RLS su app.studio_id.

Due tabelle:
  raven_registrazioni  una riga per somministrazione (risposte e punteggi in JSON, relazione)
  raven_tabelle        norme, composizione attesa e chiave di correzione, caricate dallo studio
                       dal proprio manuale (una riga per forma e tipo)
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
TIPI = ("norme", "attese", "chiave")

DDL = """
CREATE TABLE IF NOT EXISTS raven_registrazioni (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    paziente_id     BIGINT NOT NULL,
    forma           TEXT   NOT NULL CHECK (forma IN ('CPM','SPM')),
    data_reg        TIMESTAMPTZ NOT NULL,
    risposte        TEXT,          -- JSON: griglia inserita e osservazioni
    punteggi        TEXT,          -- JSON: esito di scoring_raven.valuta
    relazione       TEXT,
    operatore       TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raven_tabelle (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    forma           TEXT   NOT NULL CHECK (forma IN ('CPM','SPM')),
    tipo            TEXT   NOT NULL CHECK (tipo IN ('norme','attese','chiave')),
    dati            TEXT   NOT NULL,   -- JSON
    fonte           TEXT,
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, forma, tipo)
);

CREATE INDEX IF NOT EXISTS ix_raven_reg_paz ON raven_registrazioni(studio_id, paziente_id, data_reg);

ALTER TABLE raven_registrazioni ENABLE ROW LEVEL SECURITY;
ALTER TABLE raven_tabelle       ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='raven_registrazioni' AND policyname='raven_registrazioni_studio') THEN
    CREATE POLICY raven_registrazioni_studio ON raven_registrazioni
      USING (studio_id = current_setting('app.studio_id')::BIGINT)
      WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='raven_tabelle' AND policyname='raven_tabelle_studio') THEN
    CREATE POLICY raven_tabelle_studio ON raven_tabelle
      USING (studio_id = current_setting('app.studio_id')::BIGINT)
      WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
  END IF;
END $$;
"""


# ---------------------------------------------------------------- utilita
def _cur(conn, studio_id):
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.studio_id', %s, false)", (str(studio_id),))
    return cur


def _righe(cur):
    """Righe come dict, sia con cursori a tuple sia con cursori a dizionario."""
    nomi = [c[0] for c in cur.description]
    return [dict(r) if isinstance(r, dict) else dict(zip(nomi, r)) for r in cur.fetchall()]


def _primo(riga, nome):
    if riga is None:
        return None
    return riga[nome] if isinstance(riga, dict) else riga[0]


def _annulla(conn):
    try:
        conn.rollback()
    except Exception:
        pass


def _json(testo, vuoto):
    if not testo:
        return vuoto
    try:
        return json.loads(testo)
    except (TypeError, ValueError):
        return vuoto


def _esegui(conn, studio_id, sql, par, leggi=None):
    cur = _cur(conn, studio_id)
    try:
        cur.execute(sql, par)
        out = leggi(cur) if leggi else None
        conn.commit()
        return out
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def init_db(conn, studio_id):
    _esegui(conn, studio_id, DDL, None)


def adesso():
    return datetime.now(TZ)


# ------------------------------------------------------------- registrazioni
def salva(conn, studio_id, paziente_id, forma, punteggi, risposte=None, relazione=None,
          data_reg=None, operatore=None):
    return _esegui(
        conn, studio_id,
        "INSERT INTO raven_registrazioni (studio_id, paziente_id, forma, data_reg, risposte, punteggi, "
        "relazione, operatore) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (studio_id, paziente_id, forma, data_reg or adesso(),
         json.dumps(risposte, ensure_ascii=False) if risposte is not None else None,
         json.dumps(punteggi, ensure_ascii=False), relazione or None, operatore or None),
        lambda cur: _primo(cur.fetchone(), "id"))


def aggiorna_punteggi(conn, studio_id, paziente_id, reg_id, punteggi, relazione):
    _esegui(conn, studio_id,
            "UPDATE raven_registrazioni SET punteggi=%s, relazione=%s, aggiornato_il=now() "
            "WHERE studio_id=%s AND paziente_id=%s AND id=%s",
            (json.dumps(punteggi, ensure_ascii=False), relazione or None, studio_id, paziente_id, reg_id))


def aggiorna_relazione(conn, studio_id, paziente_id, reg_id, relazione):
    _esegui(conn, studio_id,
            "UPDATE raven_registrazioni SET relazione=%s, aggiornato_il=now() "
            "WHERE studio_id=%s AND paziente_id=%s AND id=%s",
            (relazione or None, studio_id, paziente_id, reg_id))


def lista(conn, studio_id, paziente_id):
    """Dalla piu' recente. 'risposte' e 'punteggi' tornano gia' decodificati."""
    righe = _esegui(
        conn, studio_id,
        "SELECT id, forma, data_reg, risposte, punteggi, relazione, operatore, creato_il "
        "FROM raven_registrazioni WHERE studio_id=%s AND paziente_id=%s "
        "ORDER BY data_reg DESC, id DESC", (studio_id, paziente_id), _righe)
    for r in righe:
        r["risposte"] = _json(r.get("risposte"), {})
        r["punteggi"] = _json(r.get("punteggi"), {})
    return righe


def elimina(conn, studio_id, paziente_id, reg_id):
    _esegui(conn, studio_id,
            "DELETE FROM raven_registrazioni WHERE studio_id=%s AND paziente_id=%s AND id=%s",
            (studio_id, paziente_id, reg_id))


# ------------------------------------------------------------------ tabelle
def leggi_tabella(conn, studio_id, forma, tipo):
    """Ritorna (dati, fonte) oppure (None, None) se non caricata."""
    r = _esegui(conn, studio_id,
                "SELECT dati, fonte FROM raven_tabelle WHERE studio_id=%s AND forma=%s AND tipo=%s",
                (studio_id, forma, tipo), _righe)
    if not r:
        return None, None
    return _json(r[0]["dati"], None), r[0].get("fonte")


def salva_tabella(conn, studio_id, forma, tipo, dati, fonte=None):
    if tipo not in TIPI:
        raise ValueError("Tipo di tabella non valido: %s" % tipo)
    _esegui(conn, studio_id,
            "INSERT INTO raven_tabelle (studio_id, forma, tipo, dati, fonte) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (studio_id, forma, tipo) DO UPDATE "
            "SET dati=EXCLUDED.dati, fonte=EXCLUDED.fonte, aggiornato_il=now()",
            (studio_id, forma, tipo, json.dumps(dati, ensure_ascii=False), fonte or None))


def elimina_tabella(conn, studio_id, forma, tipo):
    _esegui(conn, studio_id,
            "DELETE FROM raven_tabelle WHERE studio_id=%s AND forma=%s AND tipo=%s",
            (studio_id, forma, tipo))
