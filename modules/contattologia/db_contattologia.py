"""
Progetto multicurva RGP — persistenza dei progetti di lente a contatto.

Progettato da Dott. Giuseppe Ferraioli — www.pnev.it
© 2026 Giuseppe Ferraioli. Tutti i diritti riservati.

Il modulo HTML produce un `record` JSON autoconsistente. Qui non lo si
smonta: si salva intero in JSONB e si duplicano fuori solo i pochi campi
su cui si cerca o si filtra. Così un domani il modulo può aggiungere
campi senza migrazioni.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Iterable

TZ = ZoneInfo("Europe/Rome")

# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS contattologia_progetti (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    paziente_id     BIGINT      REFERENCES pazienti(id) ON DELETE CASCADE,
    rec_id          TEXT        NOT NULL,
    occhio          TEXT,
    geometria       TEXT,
    sintesi         TEXT,
    etichetta       TEXT,
    progetto        JSONB       NOT NULL,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT contattologia_rec_unico UNIQUE (studio_id, rec_id)
);

CREATE INDEX IF NOT EXISTS contattologia_paziente_idx
    ON contattologia_progetti (studio_id, paziente_id, aggiornato_il DESC);

CREATE TABLE IF NOT EXISTS contattologia_ordini (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    progetto_id     BIGINT      REFERENCES contattologia_progetti(id) ON DELETE CASCADE,
    paziente_id     BIGINT      REFERENCES pazienti(id) ON DELETE CASCADE,
    numero          TEXT,
    nome_file       TEXT,
    pdf             BYTEA       NOT NULL,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS contattologia_ordini_idx
    ON contattologia_ordini (studio_id, paziente_id, creato_il DESC);
"""

RLS = """
ALTER TABLE contattologia_progetti ENABLE ROW LEVEL SECURITY;
ALTER TABLE contattologia_ordini   ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS contattologia_progetti_studio ON contattologia_progetti;
CREATE POLICY contattologia_progetti_studio ON contattologia_progetti
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);

DROP POLICY IF EXISTS contattologia_ordini_studio ON contattologia_ordini;
CREATE POLICY contattologia_ordini_studio ON contattologia_ordini
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
"""


def crea_schema(conn) -> None:
    """Idempotente: si può richiamare a ogni avvio."""
    try:
        conn.rollback()  # la connessione è condivisa: pulisce transazioni
    except Exception:      # lasciate aperte/abortite da un modulo precedente
        pass
    cur = conn.cursor()
    cur.execute(DDL)
    try:
        cur.execute(RLS)
    except Exception:
        # in ambienti senza app.studio_id le policy si applicano a mano
        conn.rollback()
        cur = conn.cursor()
        cur.execute(DDL)
    conn.commit()


# --------------------------------------------------------------------------
# progetti
# --------------------------------------------------------------------------

def salva_progetto(conn, studio_id: int, paziente_id: int | None,
                   record: dict[str, Any]) -> int:
    """
    Inserisce o aggiorna. La chiave è `rec_id`, generato dal modulo e stabile:
    risalvare lo stesso progetto aggiorna la riga invece di duplicarla.
    Restituisce l'id della riga.
    """
    if not isinstance(record, dict) or not record.get("id"):
        raise ValueError("record senza id: non arriva dal modulo")

    eyes = record.get("eyes") or {}
    occhi = "+".join(sorted(eyes.keys())) or record.get("cur") or ""

    sql = """
        INSERT INTO contattologia_progetti
            (studio_id, paziente_id, rec_id, occhio, geometria, sintesi, etichetta, progetto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (studio_id, rec_id) DO UPDATE SET
            paziente_id   = EXCLUDED.paziente_id,
            occhio        = EXCLUDED.occhio,
            geometria     = EXCLUDED.geometria,
            sintesi       = EXCLUDED.sintesi,
            etichetta     = EXCLUDED.etichetta,
            progetto      = EXCLUDED.progetto,
            aggiornato_il = now()
        RETURNING id;
    """
    cur = conn.cursor()
    cur.execute(sql, (
        studio_id, paziente_id, record["id"], occhi,
        record.get("geo"), record.get("sintesi"), record.get("etichetta"),
        json.dumps(record, ensure_ascii=False),
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def elenco_progetti(conn, studio_id: int, paziente_id: int | None = None,
                    limite: int = 50) -> list[dict[str, Any]]:
    sql = """
        SELECT id, rec_id, paziente_id, etichetta, occhio, geometria, sintesi, aggiornato_il
          FROM contattologia_progetti
         WHERE studio_id = %s
           AND (%s::BIGINT IS NULL OR paziente_id = %s)
         ORDER BY aggiornato_il DESC
         LIMIT %s;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, paziente_id, paziente_id, limite))
    colonne = [d[0] for d in cur.description]
    return [dict(zip(colonne, r)) for r in cur.fetchall()]


def leggi_progetto(conn, studio_id: int, rec_id: str) -> dict[str, Any] | None:
    sql = """
        SELECT progetto FROM contattologia_progetti
         WHERE studio_id = %s AND rec_id = %s;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, rec_id))
    riga = cur.fetchone()
    if not riga:
        return None
    dato = riga[0]
    return dato if isinstance(dato, dict) else json.loads(dato)


def elimina_progetto(conn, studio_id: int, rec_id: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM contattologia_progetti WHERE studio_id = %s AND rec_id = %s;",
        (studio_id, rec_id))
    tolte = cur.rowcount
    conn.commit()
    return tolte > 0


# --------------------------------------------------------------------------
# ordini
# --------------------------------------------------------------------------

def salva_ordine(conn, studio_id: int, paziente_id: int | None,
                 rec_id: str | None, numero: str | None,
                 nome_file: str, pdf: bytes) -> int:
    sql = """
        INSERT INTO contattologia_ordini
            (studio_id, progetto_id, paziente_id, numero, nome_file, pdf)
        VALUES (
            %s,
            (SELECT id FROM contattologia_progetti
              WHERE studio_id = %s AND rec_id = %s),
            %s, %s, %s, %s)
        RETURNING id;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, studio_id, rec_id,
                      paziente_id, numero, nome_file, pdf))
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def elenco_ordini(conn, studio_id: int, paziente_id: int | None = None,
                  limite: int = 30) -> list[dict[str, Any]]:
    sql = """
        SELECT id, numero, nome_file, creato_il, octet_length(pdf) AS peso
          FROM contattologia_ordini
         WHERE studio_id = %s
           AND (%s::BIGINT IS NULL OR paziente_id = %s)
         ORDER BY creato_il DESC
         LIMIT %s;
    """
    cur = conn.cursor()
    cur.execute(sql, (studio_id, paziente_id, paziente_id, limite))
    colonne = [d[0] for d in cur.description]
    return [dict(zip(colonne, r)) for r in cur.fetchall()]


def leggi_ordine(conn, studio_id: int, ordine_id: int) -> tuple[str, bytes] | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT nome_file, pdf FROM contattologia_ordini WHERE studio_id = %s AND id = %s;",
        (studio_id, ordine_id))
    riga = cur.fetchone()
    if not riga:
        return None
    return riga[0], bytes(riga[1])


def ora_locale() -> datetime:
    return datetime.now(TZ)
