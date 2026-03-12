CREATE TABLE IF NOT EXISTS gaze_sessions (
    id BIGSERIAL PRIMARY KEY,
    paziente_id BIGINT NOT NULL REFERENCES Pazienti(id) ON DELETE CASCADE,
    operatore TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    protocollo TEXT NOT NULL,
    camera_type TEXT,
    screen_width INT,
    screen_height INT,
    distance_cm NUMERIC(6,2),
    calibration_points INT DEFAULT 9,
    calibration_score NUMERIC(6,3),
    status TEXT DEFAULT 'draft',
    note TEXT
);

CREATE TABLE IF NOT EXISTS gaze_samples (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES gaze_sessions(id) ON DELETE CASCADE,
    ts_ms BIGINT NOT NULL,
    gaze_x NUMERIC(8,3),
    gaze_y NUMERIC(8,3),
    confidence NUMERIC(6,3),
    target_label TEXT,
    tracking_ok BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS gaze_reports (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL UNIQUE REFERENCES gaze_sessions(id) ON DELETE CASCADE,
    fixation_total_ms BIGINT,
    mean_fixation_ms NUMERIC(10,2),
    saccade_count INT,
    target_hit_rate NUMERIC(6,3),
    tracking_loss_pct NUMERIC(6,3),
    center_bias_pct NUMERIC(6,3),
    sample_count INT,
    summary_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gaze_samples_session_ts ON gaze_samples(session_id, ts_ms);
