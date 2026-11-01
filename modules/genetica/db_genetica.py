"""
Modulo Genetica PNEV · accesso al database (PostgreSQL).

Convenzioni del gestionale: segnaposto %s, BIGSERIAL, TEXT, TIMESTAMPTZ, fuso Europe/Rome.
Tutte le funzioni ricevono la connessione del gestionale (`conn`, il wrapper _PgConn di
app_core): nessuna connessione aperta qui dentro.

Allineato alle convenzioni del gestionale (come db_audiometria, lead_sito, sportivi):
- il cursore del gestionale (_PgCursor) non supporta «with conn.cursor()»: si usa _cur();
- multi-tenant: `studio_id BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint`
  (app.current_studio è impostato da app_core._connect_cached su ogni connessione);
- RLS attiva (ENABLE + FORCE) con policy USING / WITH CHECK su app.current_studio;
- niente «?» negli SQL: _PgCursor li trasforma in %s.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

_TABELLE = ("genetica_profilo", "genetica_esito", "genetica_analisi")
_tabelle_pronte = False   # ensure_tables una sola volta per processo


@contextmanager
def _cur(conn):
    """Il cursore del gestionale (_PgCursor) non si puo' usare con «with
    conn.cursor()»: questo lo apre e lo chiude comunque."""
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _sid(studio_id):
    """studio_id dal chiamante (int o str) → int, oppure None (= usa app.current_studio)."""
    try:
        return int(studio_id) if studio_id not in (None, "") else None
    except (TypeError, ValueError):
        return None


DDL = """
CREATE TABLE IF NOT EXISTS genetica_profilo (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
    paziente_id  BIGINT NOT NULL,
    hpo_id       TEXT NOT NULL,
    stato        TEXT NOT NULL CHECK (stato IN ('presente', 'assente')),
    fonte        TEXT,              -- es. 'ponte PNEV', 'ricerca HPO', 'modulo INPP'
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (paziente_id, hpo_id)
);
CREATE INDEX IF NOT EXISTS ix_genetica_profilo_paz ON genetica_profilo (paziente_id);

CREATE TABLE IF NOT EXISTS genetica_esito (
    id                BIGSERIAL PRIMARY KEY,
    studio_id         BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
    paziente_id       BIGINT NOT NULL,
    data_esito        DATE,
    tipo_test         TEXT,          -- 'CGH-array', 'esoma', 'esoma trio', 'genoma', 'X-fragile', 'pannello', 'altro'
    esito             TEXT NOT NULL CHECK (esito IN ('in_attesa', 'diagnosi_confermata', 'negativo', 'vus')),
    disease_id        TEXT,          -- es. 'OMIM:616789'
    gene              TEXT,
    variante          TEXT,
    laboratorio       TEXT,
    consenso_ricerca  BOOLEAN NOT NULL DEFAULT FALSE,
    note              TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_genetica_esito_paz ON genetica_esito (paziente_id);

CREATE TABLE IF NOT EXISTS genetica_analisi (
    id            BIGSERIAL PRIMARY KEY,
    studio_id     BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
    paziente_id   BIGINT NOT NULL,
    eseguita_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_presenti    INTEGER,
    n_assenti     INTEGER,
    informativita REAL,
    versione_dati TEXT,
    risultati     JSONB
);
CREATE INDEX IF NOT EXISTS ix_genetica_analisi_paz ON genetica_analisi (paziente_id);
"""

# Policy RLS: stessa convenzione di audiometrie_tonali, lead_sito, sportivi.
RLS = "\n".join(f"""
ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {t} FORCE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies
                   WHERE tablename = '{t}' AND policyname = '{t}_studio') THEN
        CREATE POLICY {t}_studio ON {t}
            USING      (studio_id = current_setting('app.current_studio', true)::bigint)
            WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
    END IF;
END $$;""" for t in _TABELLE)

# Mantenuto per compatibilità con il README dello zip: ora è la policy effettiva.
RLS_TEMPLATE = RLS


def ensure_tables(conn) -> None:
    """Crea tabelle, indici e policy RLS (idempotente). Gira una volta per processo,
    come gli altri moduli che si creano le tabelle al primo accesso."""
    global _tabelle_pronte
    if _tabelle_pronte:
        return
    try:
        with _cur(conn) as cur:
            cur.execute(DDL)
            cur.execute(RLS)
        conn.commit()
        _tabelle_pronte = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


# ------------------------------------------------------------------ profilo HPO
def get_profilo(conn, paziente_id: int) -> dict[str, dict]:
    """{hpo_id: {'stato':..., 'fonte':..., 'note':...}}"""
    with _cur(conn) as cur:
        cur.execute("SELECT hpo_id, stato, fonte, note FROM genetica_profilo WHERE paziente_id = %s",
                    (paziente_id,))
        return {r[0]: {"stato": r[1], "fonte": r[2], "note": r[3]} for r in cur.fetchall()}


def set_segno(conn, paziente_id: int, hpo_id: str, stato: str | None, fonte: str = "", note: str = "",
              studio_id: str | None = None) -> None:
    """stato: 'presente' | 'assente' | None (= non valutato → cancella la riga)."""
    with _cur(conn) as cur:
        if stato is None:
            cur.execute("DELETE FROM genetica_profilo WHERE paziente_id = %s AND hpo_id = %s",
                        (paziente_id, hpo_id))
        else:
            cur.execute(
                """INSERT INTO genetica_profilo (studio_id, paziente_id, hpo_id, stato, fonte, note)
                   VALUES (COALESCE(%s::bigint, current_setting('app.current_studio', true)::bigint), %s, %s, %s, %s, %s)
                   ON CONFLICT (paziente_id, hpo_id)
                   DO UPDATE SET stato = EXCLUDED.stato, fonte = EXCLUDED.fonte,
                                 note = EXCLUDED.note, updated_at = now()""",
                (_sid(studio_id), paziente_id, hpo_id, stato, fonte, note))
    conn.commit()


# ------------------------------------------------------------------ esiti genetici
def add_esito(conn, paziente_id: int, esito: str, tipo_test: str = "", disease_id: str = "",
              gene: str = "", variante: str = "", laboratorio: str = "", data_esito=None,
              consenso_ricerca: bool = False, note: str = "", studio_id: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO genetica_esito (studio_id, paziente_id, data_esito, tipo_test, esito,
                   disease_id, gene, variante, laboratorio, consenso_ricerca, note)
               VALUES (COALESCE(%s::bigint, current_setting('app.current_studio', true)::bigint), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (_sid(studio_id), paziente_id, data_esito, tipo_test, esito, disease_id or None, gene, variante,
             laboratorio, consenso_ricerca, note))
    conn.commit()


def get_esiti(conn, paziente_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, data_esito, tipo_test, esito, disease_id, gene, variante, laboratorio,
                      consenso_ricerca, note
               FROM genetica_esito WHERE paziente_id = %s ORDER BY created_at DESC""", (paziente_id,))
        cols = ["id", "data_esito", "tipo_test", "esito", "disease_id", "gene", "variante",
                "laboratorio", "consenso_ricerca", "note"]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def casi_confermati(conn, escludi_paziente: int | None = None) -> list[dict]:
    """
    Casi per l'apprendimento (livello 3): solo diagnosi confermate CON consenso alla ricerca.
    Restituisce [{'disease_id', 'presenti': [...], 'assenti': [...]}].
    """
    with _cur(conn) as cur:
        cur.execute(
            """SELECT DISTINCT ON (e.paziente_id) e.paziente_id, e.disease_id
               FROM genetica_esito e
               WHERE e.esito = 'diagnosi_confermata' AND e.consenso_ricerca AND e.disease_id IS NOT NULL
               ORDER BY e.paziente_id, e.created_at DESC""")
        casi = cur.fetchall()
        out = []
        for paz, dis in casi:
            if paz == escludi_paziente:   # il paziente in analisi non deve «insegnare» a sé stesso
                continue
            cur.execute("SELECT hpo_id, stato FROM genetica_profilo WHERE paziente_id = %s", (paz,))
            rows = cur.fetchall()
            out.append({"disease_id": dis,
                        "presenti": [h for h, s in rows if s == "presente"],
                        "assenti": [h for h, s in rows if s == "assente"]})
        return out


# ------------------------------------------------------------------ analisi salvate
def salva_analisi(conn, paziente_id: int, n_presenti: int, n_assenti: int, informativita: float,
                  versione_dati: str, risultati: list[dict], studio_id: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO genetica_analisi (studio_id, paziente_id, eseguita_at, n_presenti, n_assenti,
                   informativita, versione_dati, risultati)
               VALUES (COALESCE(%s::bigint, current_setting('app.current_studio', true)::bigint), %s, %s, %s, %s, %s, %s, %s::jsonb)""",
            (_sid(studio_id), paziente_id, datetime.now(TZ), n_presenti, n_assenti, informativita,
             versione_dati, json.dumps(risultati, ensure_ascii=False)))
    conn.commit()


def storico_analisi(conn, paziente_id: int, limite: int = 10) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT eseguita_at, n_presenti, n_assenti, informativita, risultati
               FROM genetica_analisi WHERE paziente_id = %s ORDER BY eseguita_at DESC LIMIT %s""",
            (paziente_id, limite))
        return [{"eseguita_at": r[0], "n_presenti": r[1], "n_assenti": r[2], "informativita": r[3],
                 "risultati": r[4] if isinstance(r[4], list) else json.loads(r[4] or "[]")}
                for r in cur.fetchall()]
