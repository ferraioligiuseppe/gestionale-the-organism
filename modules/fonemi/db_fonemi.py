# -*- coding: utf-8 -*-
"""
db_fonemi.py - Persistenza del modulo Impostazione fonemi (PNEV).
Convenzioni gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
ZoneInfo("Europe/Rome"), multi-tenant con RLS su app.studio_id.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from .catalogo_fonemi import (FONEMI, LIVELLI, CRITERIO_PERC,
                              CRITERIO_MIN_PROVE, CRITERIO_SEDUTE)

TZ = ZoneInfo("Europe/Rome")

DDL = """
CREATE TABLE IF NOT EXISTS fon_obiettivi (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    paziente_id     BIGINT NOT NULL,
    fonema          TEXT   NOT NULL,
    livello         INTEGER NOT NULL DEFAULT 1 CHECK (livello BETWEEN 1 AND 6),
    stato           TEXT   NOT NULL DEFAULT 'attivo'
                    CHECK (stato IN ('attivo','raggiunto','sospeso')),
    note            TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, paziente_id, fonema)
);

CREATE TABLE IF NOT EXISTS fon_sedute (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    paziente_id     BIGINT NOT NULL,
    data_seduta     TIMESTAMPTZ NOT NULL,
    operatore       TEXT,
    note            TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fon_prove (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT NOT NULL,
    seduta_id       BIGINT NOT NULL REFERENCES fon_sedute(id) ON DELETE CASCADE,
    obiettivo_id    BIGINT NOT NULL REFERENCES fon_obiettivi(id) ON DELETE CASCADE,
    livello         INTEGER NOT NULL CHECK (livello BETWEEN 1 AND 6),
    n_prove         INTEGER NOT NULL CHECK (n_prove >= 0),
    n_corrette      INTEGER NOT NULL CHECK (n_corrette >= 0),
    appoggi         TEXT,          -- csv: tatto,specchio,ascolto,...
    contesto        TEXT,          -- es. vocali/parole usate
    note            TEXT,
    CHECK (n_corrette <= n_prove)
);

CREATE INDEX IF NOT EXISTS ix_fon_obiettivi_paz ON fon_obiettivi(studio_id, paziente_id);
CREATE INDEX IF NOT EXISTS ix_fon_sedute_paz    ON fon_sedute(studio_id, paziente_id, data_seduta);
CREATE INDEX IF NOT EXISTS ix_fon_prove_ob      ON fon_prove(obiettivo_id);

ALTER TABLE fon_obiettivi ENABLE ROW LEVEL SECURITY;
ALTER TABLE fon_sedute    ENABLE ROW LEVEL SECURITY;
ALTER TABLE fon_prove     ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='fon_obiettivi' AND policyname='fon_obiettivi_studio') THEN
    CREATE POLICY fon_obiettivi_studio ON fon_obiettivi
      USING (studio_id = current_setting('app.studio_id')::BIGINT)
      WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='fon_sedute' AND policyname='fon_sedute_studio') THEN
    CREATE POLICY fon_sedute_studio ON fon_sedute
      USING (studio_id = current_setting('app.studio_id')::BIGINT)
      WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='fon_prove' AND policyname='fon_prove_studio') THEN
    CREATE POLICY fon_prove_studio ON fon_prove
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


def init_db(conn, studio_id):
    cur = _cur(conn, studio_id)
    try:
        cur.execute(DDL)
        conn.commit()
    finally:
        cur.close()


def perc(n_corrette, n_prove):
    return round(100.0 * n_corrette / n_prove, 1) if n_prove else 0.0


# ---------------------------------------------------------------- obiettivi
def lista_obiettivi(conn, studio_id, paziente_id, solo_attivi=False):
    cur = _cur(conn, studio_id)
    try:
        sql = ("SELECT id, fonema, livello, stato, note, creato_il, aggiornato_il "
               "FROM fon_obiettivi WHERE studio_id=%s AND paziente_id=%s")
        if solo_attivi:
            sql += " AND stato='attivo'"
        sql += " ORDER BY stato, fonema"
        cur.execute(sql, (studio_id, paziente_id))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        cur.close()


def crea_obiettivo(conn, studio_id, paziente_id, fonema, livello=1, note=None):
    if fonema not in FONEMI:
        raise ValueError(f"Fonema non in catalogo: {fonema}")
    cur = _cur(conn, studio_id)
    try:
        cur.execute(
            "INSERT INTO fon_obiettivi (studio_id, paziente_id, fonema, livello, note) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (studio_id, paziente_id, fonema) DO UPDATE "
            "SET stato='attivo', aggiornato_il=now() RETURNING id",
            (studio_id, paziente_id, fonema, livello, note))
        oid = cur.fetchone()[0]
        conn.commit()
        return oid
    finally:
        cur.close()


def aggiorna_obiettivo(conn, studio_id, obiettivo_id, livello=None, stato=None, note=None):
    sets, vals = [], []
    if livello is not None:
        sets.append("livello=%s"); vals.append(int(livello))
    if stato is not None:
        sets.append("stato=%s"); vals.append(stato)
    if note is not None:
        sets.append("note=%s"); vals.append(note)
    if not sets:
        return
    sets.append("aggiornato_il=now()")
    cur = _cur(conn, studio_id)
    try:
        cur.execute(f"UPDATE fon_obiettivi SET {', '.join(sets)} "
                    "WHERE id=%s AND studio_id=%s", (*vals, obiettivo_id, studio_id))
        conn.commit()
    finally:
        cur.close()


# ---------------------------------------------------------------- sedute
def salva_seduta(conn, studio_id, paziente_id, prove, operatore=None, note=None, data_seduta=None):
    """
    prove: lista di dict con chiavi
        obiettivo_id, livello, n_prove, n_corrette, appoggi (list), contesto, note
    Ritorna l'id della seduta. Tutto in un'unica transazione.
    """
    data_seduta = data_seduta or datetime.now(TZ)
    cur = _cur(conn, studio_id)
    try:
        cur.execute(
            "INSERT INTO fon_sedute (studio_id, paziente_id, data_seduta, operatore, note) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (studio_id, paziente_id, data_seduta, operatore, note))
        sid = cur.fetchone()[0]
        for p in prove:
            if int(p["n_prove"]) == 0:
                continue
            cur.execute(
                "INSERT INTO fon_prove (studio_id, seduta_id, obiettivo_id, livello, "
                "n_prove, n_corrette, appoggi, contesto, note) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (studio_id, sid, p["obiettivo_id"], int(p["livello"]),
                 int(p["n_prove"]), int(p["n_corrette"]),
                 ",".join(p.get("appoggi") or []), p.get("contesto"), p.get("note")))
        conn.commit()
        return sid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def elimina_seduta(conn, studio_id, seduta_id):
    cur = _cur(conn, studio_id)
    try:
        cur.execute("DELETE FROM fon_sedute WHERE id=%s AND studio_id=%s", (seduta_id, studio_id))
        conn.commit()
    finally:
        cur.close()


def storico_prove(conn, studio_id, paziente_id, obiettivo_id=None):
    cur = _cur(conn, studio_id)
    try:
        sql = ("SELECT s.id AS seduta_id, s.data_seduta, s.operatore, s.note AS note_seduta, "
               "p.id AS prova_id, p.obiettivo_id, o.fonema, p.livello, p.n_prove, p.n_corrette, "
               "p.appoggi, p.contesto, p.note "
               "FROM fon_prove p "
               "JOIN fon_sedute s ON s.id=p.seduta_id "
               "JOIN fon_obiettivi o ON o.id=p.obiettivo_id "
               "WHERE s.studio_id=%s AND s.paziente_id=%s")
        vals = [studio_id, paziente_id]
        if obiettivo_id:
            sql += " AND p.obiettivo_id=%s"; vals.append(obiettivo_id)
        sql += " ORDER BY s.data_seduta, p.id"
        cur.execute(sql, vals)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        for r in rows:
            r["perc"] = perc(r["n_corrette"], r["n_prove"])
            r["appoggi"] = [a for a in (r["appoggi"] or "").split(",") if a]
        return rows
    finally:
        cur.close()


def lista_sedute(conn, studio_id, paziente_id):
    cur = _cur(conn, studio_id)
    try:
        cur.execute(
            "SELECT s.id, s.data_seduta, s.operatore, s.note, COUNT(p.id) AS n_obiettivi "
            "FROM fon_sedute s LEFT JOIN fon_prove p ON p.seduta_id=s.id "
            "WHERE s.studio_id=%s AND s.paziente_id=%s "
            "GROUP BY s.id ORDER BY s.data_seduta DESC", (studio_id, paziente_id))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        cur.close()


# ---------------------------------------------------------------- criterio
def valuta_passaggio(conn, studio_id, paziente_id, obiettivo):
    """
    Restituisce (pronto: bool, motivo: str).
    Pronto se le ultime CRITERIO_SEDUTE sedute al livello corrente hanno
    ciascuna >= CRITERIO_MIN_PROVE prove e >= CRITERIO_PERC % corrette.
    """
    rows = [r for r in storico_prove(conn, studio_id, paziente_id, obiettivo["id"])
            if r["livello"] == obiettivo["livello"]]
    if len(rows) < CRITERIO_SEDUTE:
        return False, f"Servono almeno {CRITERIO_SEDUTE} sedute al livello {obiettivo['livello']}."
    ultime = rows[-CRITERIO_SEDUTE:]
    for r in ultime:
        if r["n_prove"] < CRITERIO_MIN_PROVE:
            return False, f"Seduta con meno di {CRITERIO_MIN_PROVE} prove."
        if r["perc"] < CRITERIO_PERC:
            return False, f"Accuratezza {r['perc']}% in una delle ultime sedute (soglia {CRITERIO_PERC}%)."
    if obiettivo["livello"] >= max(LIVELLI):
        return True, "Criterio raggiunto all'ultimo livello: obiettivo raggiungibile."
    return True, (f"Criterio raggiunto ({CRITERIO_PERC}% su {CRITERIO_SEDUTE} sedute): "
                  f"proponibile il livello {obiettivo['livello'] + 1}.")
