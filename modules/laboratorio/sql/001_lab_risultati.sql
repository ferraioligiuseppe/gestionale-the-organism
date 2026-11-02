-- Laboratorio PNEV: tabella dei risultati + protezione multi-studio (RLS).
-- Non serve eseguirlo a mano: il modulo lo fa da solo al primo accesso (crea_tabella).
-- Stessa convenzione di PECS e genosociogramma: lo studio arriva da app.current_studio.

CREATE TABLE IF NOT EXISTS lab_risultati (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    BIGINT      NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    paziente_id  BIGINT      NOT NULL,
    modulo       TEXT        NOT NULL,
    seduta       TEXT,
    operatore    TEXT,
    parametri    TEXT,
    risultato    TEXT,
    metriche     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    prove        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    eseguito_il  TIMESTAMPTZ,
    salvato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    impronta     TEXT        UNIQUE           -- impedisce di salvare due volte lo stesso risultato
);
CREATE INDEX IF NOT EXISTS lab_risultati_paziente_idx
    ON lab_risultati (studio_id, paziente_id, modulo, eseguito_il);

UPDATE lab_risultati SET studio_id = 1 WHERE studio_id IS NULL;
ALTER TABLE lab_risultati ALTER COLUMN studio_id
    SET DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint;
ALTER TABLE lab_risultati ALTER COLUMN studio_id SET NOT NULL;
ALTER TABLE lab_risultati ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_risultati FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS lab_risultati_tenant ON lab_risultati;
CREATE POLICY lab_risultati_tenant ON lab_risultati
    USING (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint)
    WITH CHECK (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint);
