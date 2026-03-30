CREATE TABLE IF NOT EXISTS photoref_sessions (
    id BIGSERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    patient_id BIGINT NULL,
    visit_id BIGINT NULL,
    mode TEXT NULL,
    status TEXT DEFAULT 'created',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS photoref_captures (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES photoref_sessions(id) ON DELETE CASCADE,
    source TEXT,
    image_bytes BYTEA,
    annotated_image_bytes BYTEA,
    analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
