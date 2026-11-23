# -*- coding: utf-8 -*-
"""
db_adhd.py - Persistenza del modulo ADHD (PNEV).
Convenzioni gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
ZoneInfo("Europe/Rome"), multi-tenant con RLS su app.studio_id.

Due tabelle:
  adhd_registrazioni  una riga per ogni scala, scheda criteri, prova a schermo
                      o punteggio di test esterno (risposte e punteggi in JSON)
  adhd_testi          il testo degli item delle scale, caricato dallo studio
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
CATEGORIE = ("scala", "checklist", "prova", "esterno")

DDL = """
CREATE TABLE IF NOT EXISTS adhd_registrazioni (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    paziente_id     BIGINT NOT NULL,
    categoria       TEXT   NOT NULL
                    CHECK (categoria IN ('scala','checklist','prova','esterno')),
    strumento       TEXT   NOT NULL,
    informatore     TEXT,
    data_reg        TIMESTAMPTZ NOT NULL,
    risposte        TEXT,          -- JSON
    punteggi        TEXT,          -- JSON
    note            TEXT,
    operatore       TEXT,
    origine_id      TEXT,          -- id della prova a schermo: evita i doppioni
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS adhd_testi (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    strumento       TEXT   NOT NULL,
    testi           TEXT   NOT NULL,   -- JSON: lista di stringhe, una per item
    fonte           TEXT,
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, strumento)
);

CREATE INDEX IF NOT EXISTS ix_adhd_reg_paz ON adhd_registrazioni(studio_id, paziente_id, data_reg);
CREATE UNIQUE INDEX IF NOT EXISTS ux_adhd_reg_origine
    ON adhd_registrazioni(studio_id, paziente_id, origine_id) WHERE origine_id IS NOT NULL;

ALTER TABLE adhd_registrazioni ENABLE ROW LEVEL SECURITY;
ALTER TABLE adhd_testi         ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='adhd_registrazioni' AND policyname='adhd_registrazioni_studio') THEN
    CREATE POLICY adhd_registrazioni_studio ON adhd_registrazioni
      USING (studio_id = current_setting('app.studio_id')::BIGINT)
      WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='adhd_testi' AND policyname='adhd_testi_studio') THEN
    CREATE POLICY adhd_testi_studio ON adhd_testi
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


def init_db(conn, studio_id):
    cur = _cur(conn, studio_id)
    try:
        cur.execute(DDL)
        conn.commit()
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def adesso():
    return datetime.now(TZ)


# ------------------------------------------------------------- registrazioni
def salva(conn, studio_id, paziente_id, categoria, strumento, punteggi, risposte=None,
          informatore=None, data_reg=None, note=None, operatore=None, origine_id=None):
    """Ritorna l'id della riga, oppure None se era un doppione (stessa origine_id)."""
    if categoria not in CATEGORIE:
        raise ValueError("Categoria non valida: %s" % categoria)
    cur = _cur(conn, studio_id)
    try:
        cur.execute(
            "INSERT INTO adhd_registrazioni (studio_id, paziente_id, categoria, strumento, informatore, "
            "data_reg, risposte, punteggi, note, operatore, origine_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING id",
            (studio_id, paziente_id, categoria, strumento, informatore or None,
             data_reg or adesso(),
             json.dumps(risposte, ensure_ascii=False) if risposte is not None else None,
             json.dumps(punteggi, ensure_ascii=False) if punteggi is not None else None,
             note or None, operatore or None, origine_id or None))
        rid = _primo(cur.fetchone(), "id")
        conn.commit()
        return rid
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def lista(conn, studio_id, paziente_id, categoria=None, strumento=None):
    """Dalla piu' recente. 'risposte' e 'punteggi' tornano gia' decodificati."""
    cur = _cur(conn, studio_id)
    try:
        sql = ("SELECT id, categoria, strumento, informatore, data_reg, risposte, punteggi, note, "
               "operatore, creato_il FROM adhd_registrazioni WHERE studio_id=%s AND paziente_id=%s")
        par = [studio_id, paziente_id]
        if categoria:
            sql += " AND categoria=%s"; par.append(categoria)
        if strumento:
            sql += " AND strumento=%s"; par.append(strumento)
        sql += " ORDER BY data_reg DESC, id DESC"
        cur.execute(sql, tuple(par))
        righe = _righe(cur)
        conn.commit()          # chiude la lettura
        for r in righe:
            r["risposte"] = _json(r.get("risposte"), {})
            r["punteggi"] = _json(r.get("punteggi"), {})
        return righe
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def elimina(conn, studio_id, paziente_id, reg_id):
    cur = _cur(conn, studio_id)
    try:
        cur.execute("DELETE FROM adhd_registrazioni WHERE studio_id=%s AND paziente_id=%s AND id=%s",
                    (studio_id, paziente_id, reg_id))
        conn.commit()
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


# -------------------------------------------------------------------- testi
def leggi_testi(conn, studio_id, strumento):
    """Ritorna (lista_testi, fonte) oppure ([], None) se non caricati."""
    cur = _cur(conn, studio_id)
    try:
        cur.execute("SELECT testi, fonte FROM adhd_testi WHERE studio_id=%s AND strumento=%s",
                    (studio_id, strumento))
        r = _righe(cur)
        conn.commit()
        if not r:
            return [], None
        return _json(r[0]["testi"], []), r[0].get("fonte")
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def salva_testi(conn, studio_id, strumento, testi, fonte=None):
    cur = _cur(conn, studio_id)
    try:
        cur.execute(
            "INSERT INTO adhd_testi (studio_id, strumento, testi, fonte) VALUES (%s,%s,%s,%s) "
            "ON CONFLICT (studio_id, strumento) DO UPDATE "
            "SET testi=EXCLUDED.testi, fonte=EXCLUDED.fonte, aggiornato_il=now()",
            (studio_id, strumento, json.dumps(list(testi), ensure_ascii=False), fonte or None))
        conn.commit()
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()


def elimina_testi(conn, studio_id, strumento):
    cur = _cur(conn, studio_id)
    try:
        cur.execute("DELETE FROM adhd_testi WHERE studio_id=%s AND strumento=%s", (studio_id, strumento))
        conn.commit()
    except Exception:
        _annulla(conn)
        raise
    finally:
        cur.close()
