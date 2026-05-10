# -*- coding: utf-8 -*-
"""
Database layer per il modulo INPP — Valutazione Diagnostica
dello Sviluppo Neurologico.

Convenzioni del progetto:
- Placeholder PostgreSQL: %s
- Connessione fornita dal chiamante (gestita centralmente da app_core.get_connection())
- Timestamp con zoneinfo Europe/Rome
- Salvataggio dei risultati come JSONB (~150 prove per valutazione, schema flessibile)
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Optional

ROMA = ZoneInfo("Europe/Rome")


# -----------------------------------------------------------------------------
# SCHEMA — creato al primo accesso al modulo (idempotente)
# -----------------------------------------------------------------------------

DDL_INPP = """
CREATE TABLE IF NOT EXISTS inpp_valutazioni (
    id              SERIAL PRIMARY KEY,
    paziente_id     INTEGER NOT NULL,
    data_valutazione DATE NOT NULL,
    terapista       TEXT,
    motivo          TEXT,
    risultati       JSONB NOT NULL DEFAULT '{}'::jsonb,
    riepilogo       JSONB NOT NULL DEFAULT '{}'::jsonb,
    note_finali     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inpp_valutazioni_paziente
    ON inpp_valutazioni(paziente_id);

CREATE INDEX IF NOT EXISTS idx_inpp_valutazioni_data
    ON inpp_valutazioni(data_valutazione DESC);
"""


def ensure_schema(conn) -> None:
    """Crea le tabelle del modulo INPP se non esistono. Idempotente."""
    cur = conn.cursor()
    try:
        cur.execute(DDL_INPP)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


# -----------------------------------------------------------------------------
# CRUD
# -----------------------------------------------------------------------------

def lista_valutazioni(conn, paziente_id: int) -> list[dict]:
    """
    Lista delle valutazioni INPP di un paziente, dalla più recente.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, data_valutazione, terapista, motivo,
                   riepilogo, created_at, updated_at
            FROM inpp_valutazioni
            WHERE paziente_id = %s
            ORDER BY data_valutazione DESC, id DESC
            """,
            (paziente_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "data_valutazione": r[1],
            "terapista": r[2],
            "motivo": r[3],
            "riepilogo": r[4] or {},
            "created_at": r[5],
            "updated_at": r[6],
        })
    return out


def carica_valutazione(conn, val_id: int) -> Optional[dict]:
    """
    Carica una singola valutazione INPP per id, includendo tutti i risultati.
    Ritorna None se non esiste.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, paziente_id, data_valutazione, terapista, motivo,
                   risultati, riepilogo, note_finali, created_at, updated_at
            FROM inpp_valutazioni
            WHERE id = %s
            """,
            (val_id,),
        )
        r = cur.fetchone()
    finally:
        cur.close()

    if r is None:
        return None

    return {
        "id": r[0],
        "paziente_id": r[1],
        "data_valutazione": r[2],
        "terapista": r[3],
        "motivo": r[4],
        "risultati": r[5] or {},
        "riepilogo": r[6] or {},
        "note_finali": r[7],
        "created_at": r[8],
        "updated_at": r[9],
    }


def salva_valutazione(
    conn,
    paziente_id: int,
    data_valutazione,
    terapista: str,
    motivo: str,
    risultati: dict[str, Any],
    riepilogo: dict[str, Any],
    note_finali: str,
    val_id: Optional[int] = None,
) -> int:
    """
    Salva (insert o update) una valutazione INPP.

    Se val_id è None → INSERT (nuova valutazione)
    Altrimenti → UPDATE (modifica esistente)

    Ritorna l'id della valutazione (nuovo o esistente).
    """
    risultati_json = json.dumps(risultati, ensure_ascii=False, default=str)
    riepilogo_json = json.dumps(riepilogo, ensure_ascii=False, default=str)
    now = datetime.now(ROMA)

    cur = conn.cursor()
    try:
        if val_id is None:
            cur.execute(
                """
                INSERT INTO inpp_valutazioni
                    (paziente_id, data_valutazione, terapista, motivo,
                     risultati, riepilogo, note_finali, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                RETURNING id
                """,
                (
                    paziente_id, data_valutazione, terapista, motivo,
                    risultati_json, riepilogo_json, note_finali,
                    now, now,
                ),
            )
            new_id = cur.fetchone()[0]
        else:
            cur.execute(
                """
                UPDATE inpp_valutazioni
                SET data_valutazione = %s,
                    terapista        = %s,
                    motivo           = %s,
                    risultati        = %s::jsonb,
                    riepilogo        = %s::jsonb,
                    note_finali      = %s,
                    updated_at       = %s
                WHERE id = %s
                RETURNING id
                """,
                (
                    data_valutazione, terapista, motivo,
                    risultati_json, riepilogo_json, note_finali,
                    now, val_id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise ValueError(f"Valutazione INPP id={val_id} non trovata")
            new_id = row[0]
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    return new_id


def elimina_valutazione(conn, val_id: int) -> bool:
    """Elimina una valutazione INPP. Ritorna True se eliminata."""
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM inpp_valutazioni WHERE id = %s", (val_id,))
        deleted = cur.rowcount > 0
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    return deleted


def conta_valutazioni_paziente(conn, paziente_id: int) -> int:
    """Numero di valutazioni INPP fatte a un paziente."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM inpp_valutazioni WHERE paziente_id = %s",
            (paziente_id,),
        )
        n = cur.fetchone()[0]
    finally:
        cur.close()
    return int(n)
