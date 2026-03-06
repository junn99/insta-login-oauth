-- Supabase Schema for urlinsta
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard)

-- Users table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    instagram_id TEXT UNIQUE NOT NULL,
    instagram_username TEXT NOT NULL,
    facebook_page_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tokens table
CREATE TABLE tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_type TEXT NOT NULL,
    access_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insights table
CREATE TABLE insights (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    period TEXT NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audience data table
CREATE TABLE audience_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    data_type TEXT NOT NULL,
    data_json JSONB NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collection log table
CREATE TABLE collection_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_insights_user_collected ON insights(user_id, collected_at);
CREATE INDEX idx_insights_metric ON insights(metric_name);
CREATE INDEX idx_tokens_user ON tokens(user_id);
CREATE INDEX idx_audience_user ON audience_data(user_id);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE audience_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated service role
CREATE POLICY "Service role full access" ON users FOR ALL USING (true);
CREATE POLICY "Service role full access" ON tokens FOR ALL USING (true);
CREATE POLICY "Service role full access" ON insights FOR ALL USING (true);
CREATE POLICY "Service role full access" ON audience_data FOR ALL USING (true);
CREATE POLICY "Service role full access" ON collection_log FOR ALL USING (true);
