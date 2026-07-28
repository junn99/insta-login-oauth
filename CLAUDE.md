# CelebLife Instagram Insights

Streamlit app: a creator connects their Instagram Business account over OAuth, and
the app collects account-level insights into Supabase.

- Entry: `app.py`; pages in `pages/`; logic in `src/`; batch jobs in `jobs/`
- Test: `uv run pytest` &nbsp;&nbsp; Lint: `uv run ruff check`
- Deployed on Streamlit Community Cloud; DB is Supabase (schema in
  `supabase_schema.sql`, changes go in `migrations/`)

## Open items

Tracked as issues [#2](https://github.com/junn99/insta-login-oauth/issues/2),
[#3](https://github.com/junn99/insta-login-oauth/issues/3) and
[#4](https://github.com/junn99/insta-login-oauth/issues/4); the summaries below are
here so a session picks them up without needing network access.

**1. Move the scheduler out of the Streamlit process — has a hard deadline. (#2)**

`app.py:29-54` starts an APScheduler `BackgroundScheduler` inside the web process.
It cannot work there: the `st.session_state.scheduler_started` guard is per browser
session, so every visitor spawns another scheduler (duplicate `insights` rows, N×
the Instagram API calls), and Streamlit Cloud kills the process when the app sleeps
or redeploys.

The consequence that matters is `jobs/refresh_tokens.py` never running. Instagram
long-lived tokens expire after 60 days (`src/oauth.py:109`), so **60 days after the
first celeb's login, every stored token is dead and each celeb must log in again.**
This is the only open item that cannot be repaired after the fact.

Moving to Vercel is not the fix — Streamlit needs a persistent WebSocket process and
does not run there, and the scheduler would still need somewhere to live. Keep
Streamlit; move only the cron out. Least-rewrite option is GitHub Actions: the
`collect-insights` / `refresh-tokens` entry points already exist
(`pyproject.toml:19-20`) and this repo is public, so Actions minutes are free.
Watch for GitHub disabling scheduled workflows after 60 days of repo inactivity —
that window collides with the token window, so add a keepalive and a failure alert.

**2. Run `migrations/001_scope_rls_to_service_role.sql` against the live project. (#3)**

Written and committed, not yet executed. Read the header first: if the deployed
`SUPABASE_KEY` is the anon/publishable key rather than the secret key, the migration
denies every query and the OAuth callback starts failing.

**3. `render_login_page` does not validate URL schemes. (#4)**

`src/ui/celeblife_login.py` escapes URLs with `html.escape` but never checks the
scheme, so a `javascript:` URL would reach the `href` intact. Unreachable today —
all three call sites pass constants (`pages/2_🔐_Login.py:138`) — and there is no
downstream backstop: Streamlit's `transformLinkUri` is the identity function and
DOMPurify only runs on the `st.html` path. Add an allowlist before any call site
starts taking user input.

## Gotchas that have already cost a day

**Deleting an asset breaks the deployed app until it is rebooted.** Streamlit Cloud
updates the checkout on disk but does not re-import modules already in `sys.modules`,
so the old code keeps reading a file the new commit deleted. The tell is a traceback
whose line numbers contradict the source snippet shown next to them. Fix: reboot from
share.streamlit.io, not a browser refresh.

**The login UI's CSS is load-bearing in ways that look like mistakes.** Read the
module docstring in `src/ui/celeblife_login.py` before touching the stylesheet or the
heading tags. Verify in the running app, never in a standalone HTML preview —
Streamlit's own theme outranks single-class selectors and the two do not match.
