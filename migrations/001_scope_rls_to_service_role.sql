-- Migration 001: restrict the RLS policies to the service role.
--
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard) against
-- an existing project. New projects get the fixed policies straight from
-- supabase_schema.sql and do not need this file.
--
-- WHY
-- The original policies were created as:
--     CREATE POLICY "Service role full access" ON users FOR ALL USING (true);
-- With no TO clause, Postgres defaults to TO PUBLIC, which includes Supabase's
-- "anon" role. Despite the policy name, anyone holding the project's
-- publishable/anon key could read and write every table -- including
-- tokens.access_token, which is stored in plaintext.
--
-- BEFORE YOU RUN THIS
-- Confirm SUPABASE_KEY is the *secret* / service_role key, not the anon or
-- publishable key. This app connects server-side only (src/database.py), so the
-- secret key is the correct choice -- but if the anon key is currently deployed,
-- this migration will deny every query and the OAuth callback will start
-- failing. Swap the key first, then run this.
--
-- Check which role a JWT-style key carries (older sb keys are JWTs):
--     echo '<key>' | cut -d. -f2 | base64 -d
-- Newer keys are self-describing: sb_secret_... vs sb_publishable_...

BEGIN;

DROP POLICY IF EXISTS "Service role full access" ON users;
CREATE POLICY "Service role full access" ON users
    FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service role full access" ON tokens;
CREATE POLICY "Service role full access" ON tokens
    FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service role full access" ON insights;
CREATE POLICY "Service role full access" ON insights
    FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service role full access" ON audience_data;
CREATE POLICY "Service role full access" ON audience_data
    FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "Service role full access" ON collection_log;
CREATE POLICY "Service role full access" ON collection_log
    FOR ALL TO service_role USING (true);

COMMIT;

-- Verify: every row should show roles = {service_role}. A row showing {public}
-- means that table was missed.
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;

-- Rollback (restores the permissive behaviour -- only for an emergency):
--     DROP POLICY IF EXISTS "Service role full access" ON <table>;
--     CREATE POLICY "Service role full access" ON <table> FOR ALL USING (true);
