CREATE TABLE IF NOT EXISTS pipeline_provenance (
    id               SERIAL PRIMARY KEY,
    run_id           TEXT        NOT NULL,
    environment_name TEXT        NOT NULL,
    python_version   TEXT        NOT NULL,
    dependencies     JSONB,
    git_hash         TEXT,
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
