-- Instagram onboarding consent transaction.
-- Apply to the intended Supabase project after confirming:
--   select current_setting('request.jwt.claim.role', true);
--   select current_database();
--
-- Rollback:
--   drop function if exists public.complete_instagram_onboarding(
--     text,text,text,timestamptz,text,integer,text,text,text,boolean,boolean,boolean,
--     boolean,timestamptz,text
--   );
--   drop table if exists public.user_consents;
--   drop index if exists public.idx_user_consents_user_accepted_at;
--   alter table public.tokens drop constraint if exists tokens_user_type_unique;

do $$
begin
  if exists (
    select 1
    from public.tokens
    group by user_id, token_type
    having count(*) > 1
  ) then
    raise exception 'duplicate tokens exist; clean public.tokens by (user_id, token_type) before applying migration'
      using errcode = '23505';
  end if;
end $$;

do $$
begin
  alter table public.tokens
    add constraint tokens_user_type_unique unique (user_id, token_type);
exception
  when duplicate_object then null;
end $$;

create table if not exists public.user_consents (
  id bigserial primary key,
  user_id bigint not null references public.users(id) on delete cascade,
  state_nonce text not null unique,
  consent_schema_version integer not null check (consent_schema_version = 1),
  terms_version text not null,
  privacy_version text not null,
  instagram_permissions_version text not null,
  consent_age boolean not null check (consent_age is true),
  consent_terms boolean not null check (consent_terms is true),
  consent_privacy boolean not null check (consent_privacy is true),
  consent_instagram boolean not null check (consent_instagram is true),
  accepted_at timestamptz not null,
  bundle_hash text not null check (bundle_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now()
);

create index if not exists idx_user_consents_user_accepted_at
  on public.user_consents(user_id, accepted_at desc);

alter table public.user_consents enable row level security;

drop policy if exists "Service role full access" on public.user_consents;
create policy "Service role full access" on public.user_consents
  for all to service_role using (true);

create or replace function public.complete_instagram_onboarding(
  p_instagram_id text,
  p_instagram_username text,
  p_access_token text,
  p_expires_at timestamptz,
  p_state_nonce text,
  p_consent_schema_version integer,
  p_terms_version text,
  p_privacy_version text,
  p_instagram_permissions_version text,
  p_consent_age boolean,
  p_consent_terms boolean,
  p_consent_privacy boolean,
  p_consent_instagram boolean,
  p_accepted_at timestamptz,
  p_bundle_hash text
) returns bigint
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_user_id bigint;
  v_existing_user_id bigint;
  v_existing_snapshot record;
begin
  if nullif(btrim(p_instagram_id), '') is null
     or nullif(btrim(p_instagram_username), '') is null
     or nullif(btrim(p_access_token), '') is null
     or nullif(btrim(p_state_nonce), '') is null
     or p_accepted_at is null
     or p_consent_schema_version is null
     or p_terms_version is null
     or p_privacy_version is null
     or p_instagram_permissions_version is null
     or p_bundle_hash is null then
    raise exception 'required onboarding field missing' using errcode = '23502';
  end if;

  if p_consent_schema_version <> 1 then
    raise exception 'unsupported consent schema version' using errcode = '23514';
  end if;

  if p_terms_version <> 'influencer-v1.2-2026-08-26'
     or p_privacy_version <> 'privacy-2026-08-26-v3'
     or p_instagram_permissions_version <> 'instagram-permissions-2026-08-26' then
    raise exception 'unsupported consent policy version' using errcode = '23514';
  end if;

  if p_consent_age is not true
     or p_consent_terms is not true
     or p_consent_privacy is not true
     or p_consent_instagram is not true then
    raise exception 'required consent missing' using errcode = '23514';
  end if;

  if p_bundle_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'invalid consent bundle hash' using errcode = '23514';
  end if;

  insert into public.users (instagram_id, instagram_username, updated_at)
  values (p_instagram_id, p_instagram_username, now())
  on conflict (instagram_id) do update
    set instagram_username = excluded.instagram_username,
        updated_at = now()
  returning id into v_user_id;

  insert into public.user_consents (
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
  ) values (
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
  on conflict (state_nonce) do nothing
  returning user_id into v_existing_user_id;

  if v_existing_user_id is null then
    select user_id,
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
      into v_existing_snapshot
      from public.user_consents
     where state_nonce = p_state_nonce;

    if not found then
      raise exception 'consent_nonce_conflict' using errcode = '23505';
    end if;

    if v_existing_snapshot.user_id = v_user_id
       and v_existing_snapshot.consent_schema_version = p_consent_schema_version
       and v_existing_snapshot.terms_version = p_terms_version
       and v_existing_snapshot.privacy_version = p_privacy_version
       and v_existing_snapshot.instagram_permissions_version = p_instagram_permissions_version
       and v_existing_snapshot.consent_age = p_consent_age
       and v_existing_snapshot.consent_terms = p_consent_terms
       and v_existing_snapshot.consent_privacy = p_consent_privacy
       and v_existing_snapshot.consent_instagram = p_consent_instagram
       and v_existing_snapshot.accepted_at = p_accepted_at
       and v_existing_snapshot.bundle_hash = p_bundle_hash then
      insert into public.tokens (user_id, token_type, access_token, expires_at)
      values (v_user_id, 'user', p_access_token, p_expires_at)
      on conflict (user_id, token_type) do update
        set access_token = excluded.access_token,
            expires_at = excluded.expires_at,
            created_at = now();
      return v_user_id;
    end if;

    raise exception 'consent_nonce_conflict' using errcode = '23505';
  end if;

  insert into public.tokens (user_id, token_type, access_token, expires_at)
  values (v_user_id, 'user', p_access_token, p_expires_at)
  on conflict (user_id, token_type) do update
    set access_token = excluded.access_token,
        expires_at = excluded.expires_at,
        created_at = now();

  return v_user_id;
end;
$$;

revoke all on function public.complete_instagram_onboarding(
  text,text,text,timestamptz,text,integer,text,text,text,boolean,boolean,boolean,
  boolean,timestamptz,text
) from public, anon, authenticated;
-- grant execute on function complete_instagram_onboarding
grant execute on function public.complete_instagram_onboarding(
  text,text,text,timestamptz,text,integer,text,text,text,boolean,boolean,boolean,
  boolean,timestamptz,text
) to service_role;
