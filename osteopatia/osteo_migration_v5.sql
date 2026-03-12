-- Migrazione V5 Osteopatia: soft-delete + audit + indici
ALTER TABLE osteo_anamnesi
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_by TEXT,
  ADD COLUMN IF NOT EXISTS updated_by TEXT;

ALTER TABLE osteo_seduta
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deleted_by TEXT,
  ADD COLUMN IF NOT EXISTS updated_by TEXT;

CREATE INDEX IF NOT EXISTS idx_osteo_anamnesi_not_deleted
  ON osteo_anamnesi(paziente_id, data_anamnesi DESC)
  WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_osteo_seduta_not_deleted
  ON osteo_seduta(paziente_id, data_seduta DESC)
  WHERE is_deleted = FALSE;
