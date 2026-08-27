-- Supabase Schema for CelebLife
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT tokens_user_type_unique UNIQUE (user_id, token_type)
);

-- Consent audit table for the Instagram onboarding handoff.
CREATE TABLE user_consents (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state_nonce TEXT NOT NULL UNIQUE,
    consent_schema_version INTEGER NOT NULL CHECK (consent_schema_version = 1),
    terms_version TEXT NOT NULL,
    privacy_version TEXT NOT NULL,
    instagram_permissions_version TEXT NOT NULL,
    consent_age BOOLEAN NOT NULL CHECK (consent_age IS TRUE),
    consent_terms BOOLEAN NOT NULL CHECK (consent_terms IS TRUE),
    consent_privacy BOOLEAN NOT NULL CHECK (consent_privacy IS TRUE),
    consent_instagram BOOLEAN NOT NULL CHECK (consent_instagram IS TRUE),
    accepted_at TIMESTAMPTZ NOT NULL,
    bundle_hash TEXT NOT NULL CHECK (bundle_hash ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
CREATE INDEX idx_user_consents_user_accepted_at ON user_consents(user_id, accepted_at DESC);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE audience_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_log ENABLE ROW LEVEL SECURITY;

-- Allow all operations for the service role only.
--
-- The "TO service_role" clause is load-bearing. Omitting it makes the policy
-- apply "TO PUBLIC", which includes the "anon" role -- i.e. anyone holding the
-- project's publishable/anon key could read every row, and tokens.access_token
-- is stored in plaintext.
--
-- service_role itself has BYPASSRLS, so these policies are never actually
-- evaluated for it; their real effect is that anon and authenticated now match
-- no permissive policy and are denied. This app talks to Supabase server-side
-- with the secret key only (see src/database.py get_client), so it needs no
-- anon or authenticated access.
CREATE POLICY "Service role full access" ON users
    FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON tokens
    FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON user_consents
    FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON insights
    FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON audience_data
    FOR ALL TO service_role USING (true);
CREATE POLICY "Service role full access" ON collection_log
    FOR ALL TO service_role USING (true);

CREATE OR REPLACE FUNCTION public.complete_instagram_onboarding(
    p_instagram_id TEXT,
    p_instagram_username TEXT,
    p_access_token TEXT,
    p_expires_at TIMESTAMPTZ,
    p_state_nonce TEXT,
    p_consent_schema_version INTEGER,
    p_terms_version TEXT,
    p_privacy_version TEXT,
    p_instagram_permissions_version TEXT,
    p_consent_age BOOLEAN,
    p_consent_terms BOOLEAN,
    p_consent_privacy BOOLEAN,
    p_consent_instagram BOOLEAN,
    p_accepted_at TIMESTAMPTZ,
    p_bundle_hash TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_user_id BIGINT;
    v_existing_user_id BIGINT;
    v_existing_snapshot RECORD;
BEGIN
    IF NULLIF(BTRIM(p_instagram_id), '') IS NULL
       OR NULLIF(BTRIM(p_instagram_username), '') IS NULL
        OR NULLIF(BTRIM(p_access_token), '') IS NULL
        OR NULLIF(BTRIM(p_state_nonce), '') IS NULL
        OR p_accepted_at IS NULL
        OR p_consent_schema_version IS NULL
        OR p_terms_version IS NULL
        OR p_privacy_version IS NULL
        OR p_instagram_permissions_version IS NULL
        OR p_bundle_hash IS NULL THEN
        RAISE EXCEPTION 'required onboarding field missing' USING ERRCODE = '23502';
    END IF;

    IF p_consent_schema_version <> 1 THEN
        RAISE EXCEPTION 'unsupported consent schema version' USING ERRCODE = '23514';
    END IF;

    IF p_terms_version <> 'influencer-v1.2-2026-08-26'
       OR p_privacy_version <> 'privacy-2026-08-26-v3'
       OR p_instagram_permissions_version <> 'instagram-permissions-2026-08-26' THEN
        RAISE EXCEPTION 'unsupported consent policy version' USING ERRCODE = '23514';
    END IF;

    IF p_consent_age IS NOT TRUE
       OR p_consent_terms IS NOT TRUE
       OR p_consent_privacy IS NOT TRUE
       OR p_consent_instagram IS NOT TRUE THEN
        RAISE EXCEPTION 'required consent missing' USING ERRCODE = '23514';
    END IF;

    IF p_bundle_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'invalid consent bundle hash' USING ERRCODE = '23514';
    END IF;

    INSERT INTO public.users (instagram_id, instagram_username, updated_at)
    VALUES (p_instagram_id, p_instagram_username, NOW())
    ON CONFLICT (instagram_id) DO UPDATE
        SET instagram_username = EXCLUDED.instagram_username,
            updated_at = NOW()
    RETURNING id INTO v_user_id;

    INSERT INTO public.user_consents (
        user_id,
        state_nonce,
        consent_schema_version,
        terms_version,
        privacy_version,
        instagram_permissions_version,
        consent_age,
        consent_terms,
        consent_privacy,
        consent_instagram,
        accepted_at,
        bundle_hash
    ) VALUES (
        v_user_id,
        p_state_nonce,
        p_consent_schema_version,
        p_terms_version,
        p_privacy_version,
        p_instagram_permissions_version,
        p_consent_age,
        p_consent_terms,
        p_consent_privacy,
        p_consent_instagram,
        p_accepted_at,
        p_bundle_hash
    )
    ON CONFLICT (state_nonce) DO NOTHING
    RETURNING user_id INTO v_existing_user_id;

    IF v_existing_user_id IS NULL THEN
        SELECT user_id,
               consent_schema_version,
               terms_version,
               privacy_version,
               instagram_permissions_version,
               consent_age,
               consent_terms,
               consent_privacy,
               consent_instagram,
               accepted_at,
               bundle_hash
          INTO v_existing_snapshot
          FROM public.user_consents
         WHERE state_nonce = p_state_nonce;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'consent_nonce_conflict' USING ERRCODE = '23505';
        END IF;

        IF v_existing_snapshot.user_id = v_user_id
           AND v_existing_snapshot.consent_schema_version = p_consent_schema_version
           AND v_existing_snapshot.terms_version = p_terms_version
           AND v_existing_snapshot.privacy_version = p_privacy_version
           AND v_existing_snapshot.instagram_permissions_version = p_instagram_permissions_version
           AND v_existing_snapshot.consent_age = p_consent_age
           AND v_existing_snapshot.consent_terms = p_consent_terms
           AND v_existing_snapshot.consent_privacy = p_consent_privacy
           AND v_existing_snapshot.consent_instagram = p_consent_instagram
           AND v_existing_snapshot.accepted_at = p_accepted_at
           AND v_existing_snapshot.bundle_hash = p_bundle_hash THEN
            INSERT INTO public.tokens (user_id, token_type, access_token, expires_at)
            VALUES (v_user_id, 'user', p_access_token, p_expires_at)
            ON CONFLICT (user_id, token_type) DO UPDATE
                SET access_token = EXCLUDED.access_token,
                    expires_at = EXCLUDED.expires_at,
                    created_at = NOW();
            RETURN v_user_id;
        END IF;

        RAISE EXCEPTION 'consent_nonce_conflict' USING ERRCODE = '23505';
    END IF;

    INSERT INTO public.tokens (user_id, token_type, access_token, expires_at)
    VALUES (v_user_id, 'user', p_access_token, p_expires_at)
    ON CONFLICT (user_id, token_type) DO UPDATE
        SET access_token = EXCLUDED.access_token,
            expires_at = EXCLUDED.expires_at,
            created_at = NOW();

    RETURN v_user_id;
END;
$$;

REVOKE ALL ON FUNCTION public.complete_instagram_onboarding(
    TEXT,TEXT,TEXT,TIMESTAMPTZ,TEXT,INTEGER,TEXT,TEXT,TEXT,BOOLEAN,BOOLEAN,BOOLEAN,
    BOOLEAN,TIMESTAMPTZ,TEXT
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.complete_instagram_onboarding(
    TEXT,TEXT,TEXT,TIMESTAMPTZ,TEXT,INTEGER,TEXT,TEXT,TEXT,BOOLEAN,BOOLEAN,BOOLEAN,
    BOOLEAN,TIMESTAMPTZ,TEXT
) TO service_role;
