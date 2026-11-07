-- pei_core — tabelle comuni a gestionale The Organism e TFA Manager
-- rif_tipo/rif_id: 'paziente' (gestionale) oppure 'corsista' (TFA Manager)

CREATE TABLE IF NOT EXISTS pei_documenti (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT,                      -- gestionale: studio (RLS); TFA: NULL
    rif_tipo        TEXT NOT NULL CHECK (rif_tipo IN ('paziente', 'corsista')),
    rif_id          BIGINT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('PEI', 'PDF', 'DF', 'PF')),
    anno_scolastico TEXT,
    grado           TEXT DEFAULT 'secondaria_II',
    anonimo         BOOLEAN NOT NULL DEFAULT FALSE,
    stato           TEXT NOT NULL DEFAULT 'bozza' CHECK (stato IN ('bozza', 'definitivo')),
    schema_version  TEXT NOT NULL,
    contenuto       JSONB NOT NULL DEFAULT '{}'::jsonb,
    sorgente_id     BIGINT REFERENCES pei_documenti(id) ON DELETE SET NULL, -- PEI <- PDF/DF/PF
    creato_da       TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pei_doc_rif ON pei_documenti (rif_tipo, rif_id, tipo);

CREATE TABLE IF NOT EXISTS pei_allegati (
    id              BIGSERIAL PRIMARY KEY,
    documento_id    BIGINT NOT NULL REFERENCES pei_documenti(id) ON DELETE CASCADE,
    nome_file       TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    dimensione      BIGINT NOT NULL,
    pagine          INTEGER,
    testo_estratto  TEXT,
    scansione       BOOLEAN DEFAULT FALSE,
    dati            BYTEA NOT NULL,
    caricato_da     TEXT,
    caricato_il     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (documento_id, sha256)                -- niente doppioni dello stesso file
);
