-- =====================================================================
-- modules/pecs/schema_pecs.sql
-- Modulo PECS - Studio The Organism
-- Convenzioni: BIGSERIAL, TEXT, TIMESTAMPTZ, RLS multi-tenant su studio_id
-- Idempotente: puo' essere rieseguito senza effetti collaterali.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Protocollo: una riga per paziente (piu' righe se si riparte da capo)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_protocolli (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    paziente_id     BIGINT      NOT NULL,
    data_inizio     DATE        NOT NULL DEFAULT CURRENT_DATE,
    fase_corrente   TEXT        NOT NULL DEFAULT 'I',
    stato           TEXT        NOT NULL DEFAULT 'attivo',
    obiettivo       TEXT,
    note            TEXT,
    creato_da       TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pecs_protocolli_fase_chk
        CHECK (fase_corrente IN ('I','II','IIIA','IIIB','IV','V','VI')),
    CONSTRAINT pecs_protocolli_stato_chk
        CHECK (stato IN ('attivo','sospeso','concluso'))
);

CREATE INDEX IF NOT EXISTS idx_pecs_protocolli_paziente
    ON pecs_protocolli (studio_id, paziente_id, stato);

-- Un solo protocollo attivo per paziente
CREATE UNIQUE INDEX IF NOT EXISTS uq_pecs_protocollo_attivo
    ON pecs_protocolli (studio_id, paziente_id)
    WHERE stato = 'attivo';

-- ---------------------------------------------------------------------
-- 2. Rinforzatori: valutazione delle preferenze, da riverificare
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_rinforzatori (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    protocollo_id   BIGINT      NOT NULL
                    REFERENCES pecs_protocolli(id) ON DELETE CASCADE,
    item            TEXT        NOT NULL,
    categoria       TEXT,
    gerarchia       INTEGER     NOT NULL DEFAULT 1,
    data_verifica   DATE        NOT NULL DEFAULT CURRENT_DATE,
    attivo          BOOLEAN     NOT NULL DEFAULT TRUE,
    note            TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pecs_rinforzatori_protocollo
    ON pecs_rinforzatori (studio_id, protocollo_id, attivo);

-- ---------------------------------------------------------------------
-- 3. Sessioni: una riga per seduta/blocco di prove
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_sessioni (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    protocollo_id   BIGINT      NOT NULL
                    REFERENCES pecs_protocolli(id) ON DELETE CASCADE,
    data            DATE        NOT NULL DEFAULT CURRENT_DATE,
    fase            TEXT        NOT NULL,
    operatore       TEXT,
    partner         TEXT,
    prompter        TEXT,
    contesto        TEXT,
    item_usati      TEXT[]      NOT NULL DEFAULT '{}',
    n_opportunita   INTEGER     NOT NULL DEFAULT 0,
    n_autonome      INTEGER     NOT NULL DEFAULT 0,
    n_prompt        INTEGER     NOT NULL DEFAULT 0,
    n_errori        INTEGER     NOT NULL DEFAULT 0,
    parametri       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    fedelta         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    note            TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pecs_sessioni_fase_chk
        CHECK (fase IN ('I','II','IIIA','IIIB','IV','V','VI')),
    CONSTRAINT pecs_sessioni_conteggi_chk
        CHECK (n_opportunita >= 0 AND n_autonome >= 0
               AND n_autonome <= n_opportunita)
);

CREATE INDEX IF NOT EXISTS idx_pecs_sessioni_protocollo
    ON pecs_sessioni (studio_id, protocollo_id, fase, data DESC);

-- ---------------------------------------------------------------------
-- 4. Prove: dettaglio prova per prova (opzionale ma consigliato)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_prove (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    sessione_id     BIGINT      NOT NULL
                    REFERENCES pecs_sessioni(id) ON DELETE CASCADE,
    ordine          INTEGER     NOT NULL,
    esito           TEXT        NOT NULL,
    item            TEXT,
    note            TEXT,
    CONSTRAINT pecs_prove_esito_chk
        CHECK (esito IN ('autonoma','prompt','errore'))
);

CREATE INDEX IF NOT EXISTS idx_pecs_prove_sessione
    ON pecs_prove (studio_id, sessione_id, ordine);

-- ---------------------------------------------------------------------
-- 6. Foto personalizzate del vocabolario (sostituiscono il pittogramma
--    ARASAAC standard con una foto reale dell'item/paziente)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_foto_item (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT      NOT NULL,
    paziente_id     BIGINT      NOT NULL,
    nome_item       TEXT        NOT NULL,
    foto            BYTEA       NOT NULL,
    aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (studio_id, paziente_id, nome_item)
);

-- ---------------------------------------------------------------------
-- 5. Transizioni di fase: traccia di ogni passaggio, con evidenza
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pecs_transizioni (
    id                  BIGSERIAL PRIMARY KEY,
    studio_id           BIGINT      NOT NULL,
    protocollo_id       BIGINT      NOT NULL
                        REFERENCES pecs_protocolli(id) ON DELETE CASCADE,
    da_fase             TEXT,
    a_fase              TEXT        NOT NULL,
    data                DATE        NOT NULL DEFAULT CURRENT_DATE,
    criterio_soddisfatto BOOLEAN    NOT NULL DEFAULT FALSE,
    forzata             BOOLEAN     NOT NULL DEFAULT FALSE,
    motivazione         TEXT,
    evidenza            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    operatore           TEXT,
    creato_il           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pecs_transizioni_protocollo
    ON pecs_transizioni (studio_id, protocollo_id, data DESC);

-- ---------------------------------------------------------------------
-- 6. Row Level Security
--    Convenzione del gestionale: il tenant corrente e' in
--    current_setting('app.studio_id', true).
-- ---------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['pecs_protocolli','pecs_rinforzatori',
                             'pecs_sessioni','pecs_prove','pecs_transizioni']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant', t);
        EXECUTE format($f$
            CREATE POLICY %I ON %I
            USING (studio_id = NULLIF(current_setting('app.studio_id', true), '')::bigint)
            WITH CHECK (studio_id = NULLIF(current_setting('app.studio_id', true), '')::bigint)
        $f$, t || '_tenant', t);
    END LOOP;
END
$$;

-- Nota: pecs_prove non ha una colonna paziente; l'isolamento passa da
-- studio_id come nelle altre tabelle del gestionale.
