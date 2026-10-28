# -*- coding: utf-8 -*-
"""Archivio comune degli esami strumentali (eye tracking oggi; audiometria, EEG e altri domani).

Una sola tabella per tutti gli strumenti: stesso modo di salvare, elencare, confrontare.
Ogni esame arriva come «record» JSON:
    {formato, versione, strumento, tipo, id, data, paziente, sintesi:{...}, dati:{...}}
- sintesi: i numeri principali (piccoli, per elenchi e confronti)
- dati:    tutto il resto (campioni, stimoli, dettagli), caricato solo quando serve
"""
from __future__ import annotations

import datetime as dt
import json


def _cur(conn):
    return conn.cursor()


def _esegui(conn, sql, params=()) -> str | None:
    try:
        c = _cur(conn); c.execute(sql, params); conn.commit(); return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _righe(conn, sql, params=()) -> list[dict]:
    try:
        c = _cur(conn); c.execute(sql, params)
        nomi = [d[0] for d in c.description]
        return [dict(zip(nomi, r)) if not isinstance(r, dict) else r for r in c.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _json(v):
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v or "{}")
    except Exception:
        return {}


def assicura_tabella(conn) -> None:
    if _righe(conn, "SELECT 1 AS ok FROM information_schema.tables WHERE table_name='esami_strumentali'"):
        return
    _esegui(conn, """
        CREATE TABLE IF NOT EXISTS esami_strumentali (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            strumento TEXT NOT NULL,          -- eyetracking, audiometria, eeg, ...
            tipo TEXT,                        -- lettura, saccadi, inseguimento, ...
            data_esame DATE,
            origine_id BIGINT,                -- id creato dalla pagina: evita i doppioni
            sintesi JSONB,
            dati JSONB,
            commento TEXT,
            creato_il TIMESTAMPTZ DEFAULT now(),
            UNIQUE (paziente_id, strumento, origine_id)
        )""")
    _esegui(conn, "CREATE INDEX IF NOT EXISTS esami_strumentali_paz ON esami_strumentali (paziente_id, strumento)")


def salva(conn, paz_id, rec: dict) -> str | None:
    """Salva un record; se esiste già (stesso id della pagina) non lo duplica."""
    data = rec.get("data") or dt.date.today().isoformat()
    return _esegui(conn, """
        INSERT INTO esami_strumentali (paziente_id, strumento, tipo, data_esame, origine_id, sintesi, dati, commento)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (paziente_id, strumento, origine_id) DO NOTHING""",
        (int(paz_id), rec.get("strumento") or "sconosciuto", rec.get("tipo"), data[:10], rec.get("id"),
         json.dumps(rec.get("sintesi") or {}), json.dumps(rec.get("dati") or {}), rec.get("commento") or ""))


def elenco(conn, paz_id, strumento: str | None = None) -> list[dict]:
    sql = ("SELECT id, strumento, tipo, data_esame, origine_id, sintesi, commento, creato_il "
           "FROM esami_strumentali WHERE paziente_id=%s")
    par = [int(paz_id)]
    if strumento:
        sql += " AND strumento=%s"; par.append(strumento)
    out = _righe(conn, sql + " ORDER BY data_esame DESC, creato_il DESC", tuple(par))
    for r in out:
        r["sintesi"] = _json(r.get("sintesi"))
    return out


def dati(conn, esame_id) -> dict:
    r = _righe(conn, "SELECT dati FROM esami_strumentali WHERE id=%s", (int(esame_id),))
    return _json(r[0]["dati"]) if r else {}


def aggiorna_commento(conn, esame_id, testo: str) -> str | None:
    return _esegui(conn, "UPDATE esami_strumentali SET commento=%s WHERE id=%s", (testo, int(esame_id)))


def elimina(conn, esame_id) -> str | None:
    return _esegui(conn, "DELETE FROM esami_strumentali WHERE id=%s", (int(esame_id),))
