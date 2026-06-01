# -*- coding: utf-8 -*-
"""
modules/eventi/db_schema.py

Schema DB del modulo Eventi.

Gestisce:
- Eventi pubblici (costellazioni, webinar, workshop, altro)
- Iscrizioni online tramite form pubblico
- Link manuale a evento Facebook già creato
- Aggancio opzionale a pazienti esistenti

Naming:
- prefisso ev_ per tutte le tabelle del modulo
- evita collisioni con tabelle esistenti

Convenzioni del gestionale rispettate:
- %s placeholder Postgres / ? per SQLite con _DB_BACKEND detection
- Idempotenza: tutti i CREATE usano IF NOT EXISTS
- ON DELETE CASCADE per le tabelle figlie
- Timestamp con TIMESTAMPTZ (Postgres) / TEXT ISO (SQLite fallback)
- Riferimento a Pazienti(ID) opzionale (paziente_id NULL ammesso per non-pazienti)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# DDL POSTGRESQL (target principale: OVH theorganism.com)
# =============================================================================

DDL_PG_EVENTI = """
CREATE TABLE IF NOT EXISTS ev_eventi (
    id                  BIGSERIAL PRIMARY KEY,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    titolo              VARCHAR(200) NOT NULL,
    tipo                VARCHAR(50)  NOT NULL CHECK
                        (tipo IN ('costellazioni', 'webinar', 'workshop', 'altro')),
    data_ora            TIMESTAMPTZ  NOT NULL,
    durata_minuti       INTEGER,
    sede                VARCHAR(200),
    descrizione         TEXT,
    posti_max           INTEGER,
    prezzo              NUMERIC(10,2),
    fb_event_url        TEXT,
    immagine_url        TEXT,
    conduttore          VARCHAR(200),
    attivo              BOOLEAN      NOT NULL DEFAULT TRUE,
    iscrizioni_aperte   BOOLEAN      NOT NULL DEFAULT TRUE,
    note_interne        TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ev_eventi_data_ora
    ON ev_eventi(data_ora);
CREATE INDEX IF NOT EXISTS idx_ev_eventi_slug
    ON ev_eventi(slug);
CREATE INDEX IF NOT EXISTS idx_ev_eventi_attivo
    ON ev_eventi(attivo) WHERE attivo = TRUE;
CREATE INDEX IF NOT EXISTS idx_ev_eventi_tipo
    ON ev_eventi(tipo);
"""

DDL_PG_ISCRIZIONI = """
CREATE TABLE IF NOT EXISTS ev_iscrizioni (
    id                      BIGSERIAL PRIMARY KEY,
    evento_id               BIGINT NOT NULL REFERENCES ev_eventi(id) ON DELETE CASCADE,

    -- Dati iscritto (sempre presenti, anche se è già paziente)
    nome                    VARCHAR(100) NOT NULL,
    cognome                 VARCHAR(100) NOT NULL,
    email                   VARCHAR(200) NOT NULL,
    telefono                VARCHAR(50),
    note                    TEXT,

    -- Aggancio opzionale a Pazienti esistenti
    paziente_id             BIGINT REFERENCES Pazienti(ID) ON DELETE SET NULL,

    -- Stato iscrizione
    stato                   VARCHAR(20) NOT NULL DEFAULT 'confermata' CHECK
                            (stato IN ('confermata', 'lista_attesa', 'annullata')),

    -- Privacy e comunicazioni
    consenso_privacy        BOOLEAN NOT NULL DEFAULT FALSE,
    consenso_marketing      BOOLEAN NOT NULL DEFAULT FALSE,

    -- Email di conferma
    email_conferma_inviata  BOOLEAN NOT NULL DEFAULT FALSE,
    email_conferma_ts       TIMESTAMPTZ,
    email_promemoria_inviata BOOLEAN NOT NULL DEFAULT FALSE,
    email_promemoria_ts     TIMESTAMPTZ,

    -- Tracciamento
    ip_address              VARCHAR(45),
    user_agent              TEXT,
    sorgente                VARCHAR(50) DEFAULT 'web',

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_evento
    ON ev_iscrizioni(evento_id);
CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_email
    ON ev_iscrizioni(email);
CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_paziente
    ON ev_iscrizioni(paziente_id);
CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_stato
    ON ev_iscrizioni(stato);

-- Vincolo: stessa email non si può iscrivere due volte (se non annullata)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ev_iscrizione_unica
    ON ev_iscrizioni(evento_id, lower(email))
    WHERE stato != 'annullata';
"""

DDL_PG_ALL = [
    DDL_PG_EVENTI,
    DDL_PG_ISCRIZIONI,
]


# =============================================================================
# DDL SQLITE (fallback dev)
# =============================================================================

DDL_SQLITE_ALL = [
    """
    CREATE TABLE IF NOT EXISTS ev_eventi (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        slug                TEXT UNIQUE NOT NULL,
        titolo              TEXT NOT NULL,
        tipo                TEXT NOT NULL,
        data_ora            TEXT NOT NULL,
        durata_minuti       INTEGER,
        sede                TEXT,
        descrizione         TEXT,
        posti_max           INTEGER,
        prezzo              REAL,
        fb_event_url        TEXT,
        immagine_url        TEXT,
        conduttore          TEXT,
        attivo              INTEGER NOT NULL DEFAULT 1,
        iscrizioni_aperte   INTEGER NOT NULL DEFAULT 1,
        note_interne        TEXT,
        created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ev_eventi_data_ora ON ev_eventi(data_ora)",
    "CREATE INDEX IF NOT EXISTS idx_ev_eventi_slug ON ev_eventi(slug)",
    "CREATE INDEX IF NOT EXISTS idx_ev_eventi_attivo ON ev_eventi(attivo)",
    "CREATE INDEX IF NOT EXISTS idx_ev_eventi_tipo ON ev_eventi(tipo)",
    """
    CREATE TABLE IF NOT EXISTS ev_iscrizioni (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        evento_id               INTEGER NOT NULL,
        nome                    TEXT NOT NULL,
        cognome                 TEXT NOT NULL,
        email                   TEXT NOT NULL,
        telefono                TEXT,
        note                    TEXT,
        paziente_id             INTEGER,
        stato                   TEXT NOT NULL DEFAULT 'confermata',
        consenso_privacy        INTEGER NOT NULL DEFAULT 0,
        consenso_marketing      INTEGER NOT NULL DEFAULT 0,
        email_conferma_inviata  INTEGER NOT NULL DEFAULT 0,
        email_conferma_ts       TEXT,
        email_promemoria_inviata INTEGER NOT NULL DEFAULT 0,
        email_promemoria_ts     TEXT,
        ip_address              TEXT,
        user_agent              TEXT,
        sorgente                TEXT DEFAULT 'web',
        created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evento_id) REFERENCES ev_eventi(id) ON DELETE CASCADE,
        FOREIGN KEY (paziente_id) REFERENCES Pazienti(id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_evento ON ev_iscrizioni(evento_id)",
    "CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_email ON ev_iscrizioni(email)",
    "CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_paziente ON ev_iscrizioni(paziente_id)",
    "CREATE INDEX IF NOT EXISTS idx_ev_iscrizioni_stato ON ev_iscrizioni(stato)",
]


# =============================================================================
# APPLICAZIONE DELLO SCHEMA
# =============================================================================

def apply_schema(conn: Any, db_backend: str = "postgres") -> None:
    """
    Applica lo schema del modulo al database.

    Args:
        conn: connessione DB (psycopg2 wrapper o sqlite3)
        db_backend: 'postgres' o 'sqlite'

    Idempotente: tutti i CREATE usano IF NOT EXISTS, può essere chiamata
    a ogni avvio dell'app come parte di init_db().
    """
    cur = conn.cursor()
    try:
        logger.info(f"Apply schema modulo eventi (backend={db_backend})...")

        if db_backend == "postgres":
            for ddl in DDL_PG_ALL:
                cur.execute(ddl)
        else:
            for ddl in DDL_SQLITE_ALL:
                cur.execute(ddl)

        conn.commit()
        logger.info("Schema modulo eventi applicato.")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass

    # Migrazione colonne promemoria (48h/24h) - idempotente
    _ensure_promemoria_columns(conn, db_backend)


def _ensure_promemoria_columns(conn: Any, db_backend: str = "postgres") -> None:
    """
    Migrazione idempotente: aggiunge le colonne per il tracking dei due
    promemoria distinti (48h e 24h) alla tabella ev_iscrizioni.

    Le colonne pre-esistenti (email_promemoria_inviata, email_promemoria_ts)
    restano per retrocompatibilità ma non vengono più usate dalla nuova logica.
    """
    nuove_colonne_pg = [
        ("promemoria_48h_inviato", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("promemoria_48h_ts", "TIMESTAMPTZ"),
        ("promemoria_24h_inviato", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("promemoria_24h_ts", "TIMESTAMPTZ"),
    ]
    nuove_colonne_sqlite = [
        ("promemoria_48h_inviato", "INTEGER NOT NULL DEFAULT 0"),
        ("promemoria_48h_ts", "TEXT"),
        ("promemoria_24h_inviato", "INTEGER NOT NULL DEFAULT 0"),
        ("promemoria_24h_ts", "TEXT"),
    ]

    cur = conn.cursor()
    try:
        if db_backend == "postgres":
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ev_iscrizioni'
            """)
            esistenti = {r[0] for r in cur.fetchall()}
            for nome, tipo in nuove_colonne_pg:
                if nome not in esistenti:
                    cur.execute(
                        f"ALTER TABLE ev_iscrizioni ADD COLUMN {nome} {tipo}"
                    )
                    logger.info(f"Aggiunta colonna ev_iscrizioni.{nome}")
        else:
            cur.execute("PRAGMA table_info(ev_iscrizioni)")
            esistenti = {r[1] for r in cur.fetchall()}
            for nome, tipo in nuove_colonne_sqlite:
                if nome not in esistenti:
                    cur.execute(
                        f"ALTER TABLE ev_iscrizioni ADD COLUMN {nome} {tipo}"
                    )
                    logger.info(f"Aggiunta colonna ev_iscrizioni.{nome}")

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def drop_schema(conn: Any) -> None:
    """
    ATTENZIONE: rimuove tutte le tabelle del modulo. Solo per dev/test.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            DROP TABLE IF EXISTS ev_iscrizioni CASCADE;
            DROP TABLE IF EXISTS ev_eventi CASCADE;
        """)
        conn.commit()
        logger.warning("Schema modulo eventi distrutto.")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
