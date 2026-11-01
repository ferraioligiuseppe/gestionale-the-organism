-- Laboratorio PNEV: tabella dei risultati della sezione sperimentale
-- Esegui una volta su PostgreSQL (OVH). Il modulo la crea anche da solo con CREATE TABLE IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS lab_risultati (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    BIGINT,                      -- ADATTA: colonna tenant usata dalle policy RLS
    paziente_id  BIGINT      NOT NULL,        -- ADATTA: aggiungi REFERENCES alla tabella pazienti
    modulo       TEXT        NOT NULL,
    seduta       TEXT,
    operatore    TEXT,
    parametri    TEXT,
    risultato    TEXT,
    metriche     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    prove        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    eseguito_il  TIMESTAMPTZ,
    salvato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    impronta     TEXT        UNIQUE
);

CREATE INDEX IF NOT EXISTS lab_risultati_paziente_idx
    ON lab_risultati (paziente_id, modulo, eseguito_il);

-- RLS multi-tenant: copia la stessa policy che usi nelle altre tabelle cliniche.
-- Esempio (ADATTA il nome dell'impostazione di sessione che usi per lo studio):
-- ALTER TABLE lab_risultati ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY lab_risultati_studio ON lab_risultati
--     USING (studio_id = current_setting('app.studio_id')::bigint)
--     WITH CHECK (studio_id = current_setting('app.studio_id')::bigint);
