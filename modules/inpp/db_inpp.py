# -*- coding: utf-8 -*-
"""
Database layer per il modulo INPP — Valutazione Diagnostica
dello Sviluppo Neurologico.

Convenzioni del progetto:
- Placeholder PostgreSQL: %s
- Connessione fornita dal chiamante (gestita centralmente da app_core.get_connection())
- Timestamp con zoneinfo Europe/Rome
- Salvataggio dei risultati come JSONB (~150 prove per valutazione, schema flessibile)

Audit trail (hard):
- Colonne created_by / updated_by su inpp_valutazioni (username, opzionali)
- Tabella inpp_valutazioni_storico: snapshot atomico del record corrente
  PRIMA di ogni UPDATE. Ogni snapshot ha una "versione" incrementale per
  valutazione_id. La versione 1 è il primo snapshot scritto (cioè lo stato
  della valutazione PRIMA della prima modifica successiva all'insert iniziale).
- Tutto avviene in un'unica transazione: snapshot + update o rollback insieme.
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

-- Colonne aggiunte successivamente (idempotenti, sicure su DB già popolato)
ALTER TABLE inpp_valutazioni
    ADD COLUMN IF NOT EXISTS video_seduta_url TEXT;
ALTER TABLE inpp_valutazioni
    ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE inpp_valutazioni
    ADD COLUMN IF NOT EXISTS updated_by TEXT;

CREATE INDEX IF NOT EXISTS idx_inpp_valutazioni_paziente
    ON inpp_valutazioni(paziente_id);

CREATE INDEX IF NOT EXISTS idx_inpp_valutazioni_data
    ON inpp_valutazioni(data_valutazione DESC);

-- Tabella storico (audit trail): uno snapshot per ogni modifica
CREATE TABLE IF NOT EXISTS inpp_valutazioni_storico (
    id               SERIAL PRIMARY KEY,
    valutazione_id   INTEGER NOT NULL,
    versione         INTEGER NOT NULL,
    data_valutazione DATE,
    terapista        TEXT,
    motivo           TEXT,
    risultati        JSONB NOT NULL DEFAULT '{}'::jsonb,
    riepilogo        JSONB NOT NULL DEFAULT '{}'::jsonb,
    note_finali      TEXT,
    video_seduta_url TEXT,
    archived_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_by      TEXT,
    UNIQUE (valutazione_id, versione)
);

CREATE INDEX IF NOT EXISTS idx_inpp_storico_val
    ON inpp_valutazioni_storico(valutazione_id, versione DESC);

CREATE INDEX IF NOT EXISTS idx_inpp_storico_archived_at
    ON inpp_valutazioni_storico(archived_at DESC);
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
                   riepilogo, video_seduta_url,
                   created_by, updated_by,
                   created_at, updated_at
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
            "video_seduta_url": r[5],
            "created_by": r[6],
            "updated_by": r[7],
            "created_at": r[8],
            "updated_at": r[9],
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
                   risultati, riepilogo, note_finali, video_seduta_url,
                   created_by, updated_by,
                   created_at, updated_at
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
        "video_seduta_url": r[8],
        "created_by": r[9],
        "updated_by": r[10],
        "created_at": r[11],
        "updated_at": r[12],
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
    video_seduta_url: Optional[str] = None,
    username: Optional[str] = None,
) -> int:
    """
    Salva (insert o update) una valutazione INPP.

    Se val_id è None → INSERT (nuova valutazione).
    Altrimenti → UPDATE preceduto da snapshot del record corrente
                  nella tabella inpp_valutazioni_storico, atomicamente.

    Ritorna l'id della valutazione (nuovo o esistente).
    """
    risultati_json = json.dumps(risultati, ensure_ascii=False, default=str)
    riepilogo_json = json.dumps(riepilogo, ensure_ascii=False, default=str)
    now = datetime.now(ROMA)

    # Normalizzazioni: stringa vuota → NULL
    video_seduta_url = (video_seduta_url or "").strip() or None
    username = (username or "").strip() or None

    cur = conn.cursor()
    try:
        if val_id is None:
            # ── INSERT ────────────────────────────────────────────────
            cur.execute(
                """
                INSERT INTO inpp_valutazioni
                    (paziente_id, data_valutazione, terapista, motivo,
                     risultati, riepilogo, note_finali, video_seduta_url,
                     created_by, updated_by,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                        %s, %s,
                        %s, %s)
                RETURNING id
                """,
                (
                    paziente_id, data_valutazione, terapista, motivo,
                    risultati_json, riepilogo_json, note_finali,
                    video_seduta_url,
                    username, username,
                    now, now,
                ),
            )
            new_id = cur.fetchone()[0]
        else:
            # ── UPDATE con snapshot pre-modifica ──────────────────────
            # 1) Snapshot del record corrente nella tabella storico.
            #    Versione = MAX(versione) + 1 per quella valutazione_id (parte da 1).
            cur.execute(
                """
                INSERT INTO inpp_valutazioni_storico (
                    valutazione_id, versione,
                    data_valutazione, terapista, motivo,
                    risultati, riepilogo, note_finali, video_seduta_url,
                    archived_at, archived_by
                )
                SELECT
                    v.id,
                    COALESCE(
                        (SELECT MAX(versione)
                         FROM inpp_valutazioni_storico
                         WHERE valutazione_id = %s),
                        0
                    ) + 1,
                    v.data_valutazione, v.terapista, v.motivo,
                    v.risultati, v.riepilogo, v.note_finali, v.video_seduta_url,
                    %s, %s
                FROM inpp_valutazioni v
                WHERE v.id = %s
                """,
                (val_id, now, username, val_id),
            )

            # 2) UPDATE vero e proprio
            cur.execute(
                """
                UPDATE inpp_valutazioni
                SET data_valutazione = %s,
                    terapista        = %s,
                    motivo           = %s,
                    risultati        = %s::jsonb,
                    riepilogo        = %s::jsonb,
                    note_finali      = %s,
                    video_seduta_url = %s,
                    updated_by       = %s,
                    updated_at       = %s
                WHERE id = %s
                RETURNING id
                """,
                (
                    data_valutazione, terapista, motivo,
                    risultati_json, riepilogo_json, note_finali,
                    video_seduta_url,
                    username,
                    now, val_id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                # Se la valutazione non esiste, l'INSERT dello storico
                # non ha inserito nulla (SELECT vuoto) e l'UPDATE non trova
                # la riga. Rollback per non lasciare stato sporco.
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
    """
    Elimina una valutazione INPP. Ritorna True se eliminata.

    Nota: NON elimina lo storico associato (le righe di
    inpp_valutazioni_storico con valutazione_id=val_id restano in DB,
    "orfane" ma consultabili a fini di audit). Se in futuro vorrai
    cancellare anche lo storico, aggiungiamo un parametro purge_storico.
    """
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


# -----------------------------------------------------------------------------
# STORICO / AUDIT TRAIL — primitive di lettura
# -----------------------------------------------------------------------------
# Queste funzioni espongono lo storico ma NON sono ancora usate dall'UI:
# saranno consumate nella passata successiva ("UI storico versioni").
# Sono qui ora per non dover modificare nuovamente db_inpp.py dopo.

def lista_versioni_storico(conn, valutazione_id: int) -> list[dict]:
    """
    Lista (metadata) delle versioni storico di una valutazione,
    dalla più recente. NON include i payload JSONB pesanti.
    """
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, versione, data_valutazione, terapista,
                   archived_at, archived_by
            FROM inpp_valutazioni_storico
            WHERE valutazione_id = %s
            ORDER BY versione DESC
            """,
            (valutazione_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    return [
        {
            "id": r[0],
            "versione": r[1],
            "data_valutazione": r[2],
            "terapista": r[3],
            "archived_at": r[4],
            "archived_by": r[5],
        }
        for r in rows
    ]


def carica_versione_storico(conn, storico_id: int) -> Optional[dict]:
    """Carica una singola versione storico, payload incluso."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, valutazione_id, versione,
                   data_valutazione, terapista, motivo,
                   risultati, riepilogo, note_finali, video_seduta_url,
                   archived_at, archived_by
            FROM inpp_valutazioni_storico
            WHERE id = %s
            """,
            (storico_id,),
        )
        r = cur.fetchone()
    finally:
        cur.close()

    if r is None:
        return None

    return {
        "id": r[0],
        "valutazione_id": r[1],
        "versione": r[2],
        "data_valutazione": r[3],
        "terapista": r[4],
        "motivo": r[5],
        "risultati": r[6] or {},
        "riepilogo": r[7] or {},
        "note_finali": r[8],
        "video_seduta_url": r[9],
        "archived_at": r[10],
        "archived_by": r[11],
    }


def conta_versioni_storico(conn, valutazione_id: int) -> int:
    """Quante versioni storico esistono per una valutazione."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM inpp_valutazioni_storico WHERE valutazione_id = %s",
            (valutazione_id,),
        )
        n = cur.fetchone()[0]
    finally:
        cur.close()
    return int(n)
