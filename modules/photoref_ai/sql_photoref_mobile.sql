CREATE TABLE IF NOT EXISTS photoref_sessions (
    id BIGSERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    patient_id TEXT NULL,
    visit_id TEXT NULL,
    eye_side TEXT NULL,
    capture_type TEXT NULL,
    operator_user TEXT NULL,
    notes TEXT NULL,
    mode TEXT NULL,
    mobile_link TEXT NULL,
    status TEXT DEFAULT 'created',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photoref_sessions_token
    ON photoref_sessions(token);

CREATE INDEX IF NOT EXISTS idx_photoref_sessions_created_at
    ON photoref_sessions(created_at DESC);

CREATE TABLE IF NOT EXISTS photoref_captures (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NULL REFERENCES photoref_sessions(id) ON DELETE SET NULL,
    token TEXT NULL,
    source TEXT,
    image_bytes BYTEA,
    annotated_image_bytes BYTEA,
    analysis_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photoref_captures_session_id
    ON photoref_captures(session_id);

CREATE INDEX IF NOT EXISTS idx_photoref_captures_token
    ON photoref_captures(token);
