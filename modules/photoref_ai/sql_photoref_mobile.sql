-- Schema minimo di supporto per il flusso Photoref mobile.
-- Adattalo solo se le tue tabelle hanno già questi campi.
-- NON lanciare alla cieca in produzione senza confrontarlo col DB reale.

CREATE TABLE IF NOT EXISTS photoref_sessions (
    id BIGSERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    patient_id BIGINT NULL,
    visit_id BIGINT NULL,
    side TEXT NULL,
    acquisition_type TEXT NULL DEFAULT 'photoref',
    status TEXT NOT NULL DEFAULT 'created',
    operator TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NULL,
    captured_at TIMESTAMPTZ NULL,
    analyzed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token ON photoref_sessions(token);
CREATE INDEX IF NOT EXISTS idx_photoref_sessions_visit_id ON photoref_sessions(visit_id);

CREATE TABLE IF NOT EXISTS photoref_captures (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NULL REFERENCES photoref_sessions(id) ON DELETE SET NULL,
    token TEXT NOT NULL,
    source TEXT NOT NULL,
    image_path TEXT NULL,
    annotated_image_path TEXT NULL,
    analysis_json JSONB NULL,
    quality_score NUMERIC(5,2) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photoref_captures_token ON photoref_captures(token);
CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id ON photoref_captures(session_id);
