-- === OSTEOPATIA: ANAMNESI + SEDUTE ===
-- Nota: ho lasciato paziente_id senza FK per non rompere il tuo schema.
-- Se vuoi il vincolo FK, aggiungilo quando sei sicuro del nome/tabella PK.

CREATE TABLE IF NOT EXISTS osteo_anamnesi (
  id               BIGSERIAL PRIMARY KEY,
  paziente_id      BIGINT NOT NULL,
  data_anamnesi    DATE NOT NULL DEFAULT CURRENT_DATE,

  motivo           TEXT,
  dolore_sede      TEXT,
  dolore_intensita SMALLINT, -- 0..10
  dolore_durata    TEXT,
  aggravanti       TEXT,
  allevianti       TEXT,

  storia_clinica   JSONB DEFAULT '{}'::jsonb,
  area_neuro_post  JSONB DEFAULT '{}'::jsonb,
  stile_vita       JSONB DEFAULT '{}'::jsonb,
  area_pediatrica  JSONB DEFAULT '{}'::jsonb,

  valutazione      TEXT,
  ipotesi          TEXT,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_osteo_anamnesi_paziente ON osteo_anamnesi(paziente_id);

CREATE TABLE IF NOT EXISTS osteo_seduta (
  id               BIGSERIAL PRIMARY KEY,
  paziente_id      BIGINT NOT NULL,
  anamnesi_id      BIGINT REFERENCES osteo_anamnesi(id) ON DELETE SET NULL,

  data_seduta      DATE NOT NULL DEFAULT CURRENT_DATE,
  operatore        TEXT,

  tipo_seduta      TEXT,     -- "Prima visita" / "Controllo" / "Follow-up"
  dolore_pre       SMALLINT, -- 0..10
  note_pre         TEXT,

  tecniche         JSONB DEFAULT '{}'::jsonb,
  descrizione      TEXT,

  risposta         TEXT,
  dolore_post      SMALLINT, -- 0..10
  reazioni         TEXT,

  indicazioni      TEXT,
  prossimo_step    TEXT,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_osteo_seduta_paziente ON osteo_seduta(paziente_id);
CREATE INDEX IF NOT EXISTS idx_osteo_seduta_anamnesi ON osteo_seduta(anamnesi_id);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_osteo_anamnesi_updated ON osteo_anamnesi;
CREATE TRIGGER trg_osteo_anamnesi_updated
BEFORE UPDATE ON osteo_anamnesi
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_osteo_seduta_updated ON osteo_seduta;
CREATE TRIGGER trg_osteo_seduta_updated
BEFORE UPDATE ON osteo_seduta
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
