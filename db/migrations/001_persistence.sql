CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_session_id TEXT UNIQUE,
    channel TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    intent TEXT,
    confidence TEXT,
    citations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'passed', 'failed', 'error')),
    total_cases INTEGER NOT NULL DEFAULT 0 CHECK (total_cases >= 0),
    passed_cases INTEGER NOT NULL DEFAULT 0 CHECK (passed_cases >= 0),
    failed_cases INTEGER NOT NULL DEFAULT 0 CHECK (failed_cases >= 0),
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_run_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    expected TEXT NOT NULL,
    actual_intent TEXT,
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'error')),
    reason TEXT,
    response_text TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_channel_user
    ON chat_sessions (channel, user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
    ON chat_messages (session_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_test_runs_created
    ON test_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_test_run_cases_run_created
    ON test_run_cases (run_id, created_at ASC);
