# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/db_schema.py

Schema DB del modulo Consensi Costellazioni Familiari.

Architettura:
- Pattern multi-tenancy: database fisico separato per studio (Pattern C),
  gestito da modules/saas_tenant.py. NON serve titolare_id né RLS dentro
  questo DB perché esiste un solo titolare per DB.
- Coesiste con la tabella Consensi_Privacy legacy (consensi PDF firmati a penna):
  questo modulo gestisce SOLO le costellazioni familiari, le altre tipologie
  restano sulla tabella legacy fino a future migrazioni.
- Solo pazienti adulti nel MVP. La gestione minori/nuclei familiari è rinviata.

Naming:
- prefisso cf_ ("consensi famigliari/familiari/familiari costellazioni")
- evita collisioni con tabelle esistenti (Pazienti, Consensi_Privacy, ecc.)

Convenzioni del gestionale rispettate:
- %s placeholder Postgres / ? per SQLite con _DB_BACKEND detection
- Idempotenza: tutti i CREATE usano IF NOT EXISTS
- ON DELETE CASCADE per le tabelle figlie
- Timestamp con TIMESTAMPTZ (Postgres) / TEXT ISO (SQLite fallback)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# DDL POSTGRESQL (target principale: OVH)
# =============================================================================

DDL_PG_TEMPLATE = """
CREATE TABLE IF NOT EXISTS cf_template (
    id                  BIGSERIAL PRIMARY KEY,
    codice              VARCHAR(80)  NOT NULL,
    versione            VARCHAR(20)  NOT NULL,
    nome                VARCHAR(200) NOT NULL,
    sottocategoria      VARCHAR(50)  NOT NULL,
    testo_md            TEXT         NOT NULL,
    voci                JSONB        NOT NULL DEFAULT '[]'::jsonb,
    requisiti           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    base_giuridica      TEXT,
    finalita            TEXT,
    periodo_conservazione_anni INT,
    attivo              BOOLEAN      NOT NULL DEFAULT TRUE,
    data_creazione      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    data_dismissione    TIMESTAMPTZ,
    creato_da           VARCHAR(200),
    UNIQUE (codice, versione)
);

CREATE INDEX IF NOT EXISTS idx_cf_template_attivo
    ON cf_template(codice) WHERE attivo;
CREATE INDEX IF NOT EXISTS idx_cf_template_sottocategoria
    ON cf_template(sottocategoria);
"""

DDL_PG_FIRME = """
CREATE TABLE IF NOT EXISTS cf_firme (
    id                  BIGSERIAL PRIMARY KEY,
    paziente_id         BIGINT NOT NULL REFERENCES Pazienti(id) ON DELETE CASCADE,
    template_id         BIGINT NOT NULL REFERENCES cf_template(id),

    -- Snapshot per resilienza a modifiche del template
    template_codice     VARCHAR(80)  NOT NULL,
    template_versione   VARCHAR(20)  NOT NULL,

    data_accettazione   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modalita_firma      VARCHAR(20) NOT NULL CHECK
                        (modalita_firma IN ('cartaceo', 'click_studio', 'link_paziente')),

    -- Tracciamento
    ip_address          VARCHAR(45),
    user_agent          TEXT,
    firmato_da          VARCHAR(200),  -- nome operatore (TODO: FK a utenti_meta in futuro)
    firmato_token       VARCHAR(100),

    -- Documento PDF
    pdf_blob            BYTEA,
    pdf_filename        TEXT,
    pdf_hash            VARCHAR(64),

    -- Stato
    stato               VARCHAR(20) NOT NULL DEFAULT 'attivo' CHECK
                        (stato IN ('bozza', 'attivo', 'revocato', 'scaduto', 'superseduto')),
    data_scadenza       TIMESTAMPTZ,

    -- Revoca
    data_revoca         TIMESTAMPTZ,
    revocato_da         VARCHAR(200),
    motivazione_revoca  TEXT,
    modalita_revoca     VARCHAR(20) CHECK
                        (modalita_revoca IS NULL OR
                         modalita_revoca IN ('scritta', 'verbale', 'online', 'altro')),

    -- Versionamento (catena di sostituzioni)
    sostituisce_id      BIGINT REFERENCES cf_firme(id),
    sostituito_da_id    BIGINT REFERENCES cf_firme(id),

    note                TEXT,
    data_creazione      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cf_firme_paziente
    ON cf_firme(paziente_id);
CREATE INDEX IF NOT EXISTS idx_cf_firme_attivi
    ON cf_firme(paziente_id, template_codice) WHERE stato = 'attivo';
CREATE INDEX IF NOT EXISTS idx_cf_firme_template
    ON cf_firme(template_id);
"""

DDL_PG_VOCI = """
CREATE TABLE IF NOT EXISTS cf_voci (
    id                  BIGSERIAL PRIMARY KEY,
    firma_id            BIGINT NOT NULL REFERENCES cf_firme(id) ON DELETE CASCADE,
    codice_voce         VARCHAR(20) NOT NULL,
    valore              BOOLEAN NOT NULL,
    note                TEXT,
    UNIQUE (firma_id, codice_voce)
);

CREATE INDEX IF NOT EXISTS idx_cf_voci_firma ON cf_voci(firma_id);
"""

DDL_PG_GRUPPI = """
CREATE TABLE IF NOT EXISTS cf_gruppi (
    id                  BIGSERIAL PRIMARY KEY,
    data_sessione       DATE NOT NULL,
    ora_inizio          TIME,
    ora_fine            TIME,
    conduttore          VARCHAR(200) NOT NULL,
    titolo              VARCHAR(200),
    descrizione         TEXT,
    n_max_partecipanti  INT,
    stato               VARCHAR(20) NOT NULL DEFAULT 'pianificato' CHECK
                        (stato IN ('pianificato', 'concluso', 'annullato')),
    note                TEXT,
    data_creazione      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cf_gruppi_data ON cf_gruppi(data_sessione);
"""

DDL_PG_GRUPPI_PART = """
CREATE TABLE IF NOT EXISTS cf_gruppi_partecipanti (
    id                          BIGSERIAL PRIMARY KEY,
    gruppo_id                   BIGINT NOT NULL REFERENCES cf_gruppi(id) ON DELETE CASCADE,
    paziente_id                 BIGINT NOT NULL REFERENCES Pazienti(id),
    ruoli                       JSONB NOT NULL DEFAULT '["cliente"]'::jsonb,
    firma_gruppo_id             BIGINT REFERENCES cf_firme(id),
    firma_rappresentante_id     BIGINT REFERENCES cf_firme(id),
    firma_registrazione_id      BIGINT REFERENCES cf_firme(id),
    presente                    BOOLEAN NOT NULL DEFAULT FALSE,
    note                        TEXT,
    data_creazione              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (gruppo_id, paziente_id)
);

CREATE INDEX IF NOT EXISTS idx_cf_gp_gruppo
    ON cf_gruppi_partecipanti(gruppo_id);
CREATE INDEX IF NOT EXISTS idx_cf_gp_paziente
    ON cf_gruppi_partecipanti(paziente_id);
"""

DDL_PG_TOKEN = """
CREATE TABLE IF NOT EXISTS cf_token_firma (
    id                  BIGSERIAL PRIMARY KEY,
    token               VARCHAR(100) NOT NULL UNIQUE,
    paziente_id         BIGINT NOT NULL REFERENCES Pazienti(id),
    template_id         BIGINT NOT NULL REFERENCES cf_template(id),
    creato_da           VARCHAR(200),
    data_creazione      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_scadenza       TIMESTAMPTZ NOT NULL,
    data_consumo        TIMESTAMPTZ,
    firma_id            BIGINT REFERENCES cf_firme(id),
    stato               VARCHAR(20) NOT NULL DEFAULT 'attivo' CHECK
                        (stato IN ('attivo', 'consumato', 'scaduto', 'revocato'))
);

CREATE INDEX IF NOT EXISTS idx_cf_token_lookup
    ON cf_token_firma(token) WHERE stato = 'attivo';
CREATE INDEX IF NOT EXISTS idx_cf_token_paziente
    ON cf_token_firma(paziente_id);
"""

DDL_PG_AUDIT = """
CREATE TABLE IF NOT EXISTS cf_audit_log (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp_evento    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tipo_evento         VARCHAR(50) NOT NULL,
    entita              VARCHAR(50) NOT NULL,
    entita_id           BIGINT,
    paziente_id         BIGINT REFERENCES Pazienti(id),
    operatore           VARCHAR(200),
    ip_address          VARCHAR(45),
    user_agent          TEXT,
    descrizione         TEXT,
    dati_before         JSONB,
    dati_after          JSONB
);

CREATE INDEX IF NOT EXISTS idx_cf_audit_paziente
    ON cf_audit_log(paziente_id, timestamp_evento DESC);
CREATE INDEX IF NOT EXISTS idx_cf_audit_entita
    ON cf_audit_log(entita, entita_id);
"""

DDL_PG_ALL = [
    DDL_PG_TEMPLATE,
    DDL_PG_FIRME,
    DDL_PG_VOCI,
    DDL_PG_GRUPPI,
    DDL_PG_GRUPPI_PART,
    DDL_PG_TOKEN,
    DDL_PG_AUDIT,
]


# =============================================================================
# DDL SQLITE (fallback dev locale - allineato al pattern del gestionale)
# =============================================================================

DDL_SQLITE_ALL = [
    """
    CREATE TABLE IF NOT EXISTS cf_template (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        codice              TEXT NOT NULL,
        versione            TEXT NOT NULL,
        nome                TEXT NOT NULL,
        sottocategoria      TEXT NOT NULL,
        testo_md            TEXT NOT NULL,
        voci                TEXT NOT NULL DEFAULT '[]',
        requisiti           TEXT NOT NULL DEFAULT '{}',
        base_giuridica      TEXT,
        finalita            TEXT,
        periodo_conservazione_anni INTEGER,
        attivo              INTEGER NOT NULL DEFAULT 1,
        data_creazione      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        data_dismissione    TEXT,
        creato_da           TEXT,
        UNIQUE (codice, versione)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cf_template_attivo ON cf_template(codice)",
    """
    CREATE TABLE IF NOT EXISTS cf_firme (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        paziente_id         INTEGER NOT NULL,
        template_id         INTEGER NOT NULL,
        template_codice     TEXT NOT NULL,
        template_versione   TEXT NOT NULL,
        data_accettazione   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        modalita_firma      TEXT NOT NULL,
        ip_address          TEXT,
        user_agent          TEXT,
        firmato_da          TEXT,
        firmato_token       TEXT,
        pdf_blob            BLOB,
        pdf_filename        TEXT,
        pdf_hash            TEXT,
        stato               TEXT NOT NULL DEFAULT 'attivo',
        data_scadenza       TEXT,
        data_revoca         TEXT,
        revocato_da         TEXT,
        motivazione_revoca  TEXT,
        modalita_revoca     TEXT,
        sostituisce_id      INTEGER,
        sostituito_da_id    INTEGER,
        note                TEXT,
        data_creazione      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (paziente_id) REFERENCES Pazienti(id) ON DELETE CASCADE,
        FOREIGN KEY (template_id) REFERENCES cf_template(id),
        FOREIGN KEY (sostituisce_id) REFERENCES cf_firme(id),
        FOREIGN KEY (sostituito_da_id) REFERENCES cf_firme(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cf_firme_paziente ON cf_firme(paziente_id)",
    "CREATE INDEX IF NOT EXISTS idx_cf_firme_attivi ON cf_firme(paziente_id, template_codice, stato)",
    """
    CREATE TABLE IF NOT EXISTS cf_voci (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        firma_id        INTEGER NOT NULL,
        codice_voce     TEXT NOT NULL,
        valore          INTEGER NOT NULL,
        note            TEXT,
        UNIQUE (firma_id, codice_voce),
        FOREIGN KEY (firma_id) REFERENCES cf_firme(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cf_gruppi (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        data_sessione       TEXT NOT NULL,
        ora_inizio          TEXT,
        ora_fine            TEXT,
        conduttore          TEXT NOT NULL,
        titolo              TEXT,
        descrizione         TEXT,
        n_max_partecipanti  INTEGER,
        stato               TEXT NOT NULL DEFAULT 'pianificato',
        note                TEXT,
        data_creazione      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cf_gruppi_partecipanti (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        gruppo_id                   INTEGER NOT NULL,
        paziente_id                 INTEGER NOT NULL,
        ruoli                       TEXT NOT NULL DEFAULT '["cliente"]',
        firma_gruppo_id             INTEGER,
        firma_rappresentante_id     INTEGER,
        firma_registrazione_id      INTEGER,
        presente                    INTEGER NOT NULL DEFAULT 0,
        note                        TEXT,
        data_creazione              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (gruppo_id, paziente_id),
        FOREIGN KEY (gruppo_id) REFERENCES cf_gruppi(id) ON DELETE CASCADE,
        FOREIGN KEY (paziente_id) REFERENCES Pazienti(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cf_token_firma (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        token           TEXT NOT NULL UNIQUE,
        paziente_id     INTEGER NOT NULL,
        template_id     INTEGER NOT NULL,
        creato_da       TEXT,
        data_creazione  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        data_scadenza   TEXT NOT NULL,
        data_consumo    TEXT,
        firma_id        INTEGER,
        stato           TEXT NOT NULL DEFAULT 'attivo',
        FOREIGN KEY (paziente_id) REFERENCES Pazienti(id),
        FOREIGN KEY (template_id) REFERENCES cf_template(id),
        FOREIGN KEY (firma_id) REFERENCES cf_firme(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cf_audit_log (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp_evento    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tipo_evento         TEXT NOT NULL,
        entita              TEXT NOT NULL,
        entita_id           INTEGER,
        paziente_id         INTEGER,
        operatore           TEXT,
        ip_address          TEXT,
        user_agent          TEXT,
        descrizione         TEXT,
        dati_before         TEXT,
        dati_after          TEXT,
        FOREIGN KEY (paziente_id) REFERENCES Pazienti(id)
    )
    """,
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
        logger.info(f"Apply schema modulo consensi costellazioni (backend={db_backend})...")

        if db_backend == "postgres":
            for ddl in DDL_PG_ALL:
                cur.execute(ddl)
        else:
            for ddl in DDL_SQLITE_ALL:
                cur.execute(ddl)

        conn.commit()
        logger.info("Schema modulo consensi costellazioni applicato.")
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
            DROP TABLE IF EXISTS cf_audit_log CASCADE;
            DROP TABLE IF EXISTS cf_token_firma CASCADE;
            DROP TABLE IF EXISTS cf_gruppi_partecipanti CASCADE;
            DROP TABLE IF EXISTS cf_gruppi CASCADE;
            DROP TABLE IF EXISTS cf_voci CASCADE;
            DROP TABLE IF EXISTS cf_firme CASCADE;
            DROP TABLE IF EXISTS cf_template CASCADE;
        """)
        conn.commit()
        logger.warning("Schema modulo consensi costellazioni distrutto.")
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


# =============================================================================
# HOOK DI INTEGRAZIONE CON IL GESTIONALE
# =============================================================================

def init_db_hook():
    """
    Hook da chiamare da modules/app_core.py::init_db() dopo le tabelle base.

    Esempio di integrazione:

        # In modules/app_core.py::init_db()
        from modules.consensi_costellazioni.db_schema import init_db_hook
        init_db_hook()
    """
    try:
        from modules.app_core import get_connection, _DB_BACKEND
    except ImportError:
        logger.warning("Impossibile importare modules.app_core; skip init.")
        return

    conn = get_connection()
    apply_schema(conn, db_backend=_DB_BACKEND)
