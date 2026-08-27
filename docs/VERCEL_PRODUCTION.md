# Vercel Production Cutover Runbook

> 목적: Preview에서 검증한 SHA를 Vercel Production으로 수동 배포하고, 실제 Instagram OAuth, Supabase 저장, Dashboard/insights 읽기까지 확인한 뒤에만 `main`에 합친다. 이 문서는 비밀값을 포함하지 않는다.

## 1. 전환 원칙

| 항목 | 기준 |
| --- | --- |
| 배포 순서 | 테스트된 feature SHA를 Production에 수동 배포한 뒤 검증, 그 다음 `main` merge |
| Git merge | OAuth/DB/insights E2E 성공 전에는 `main`에 합치지 않음 |
| Vercel 프로젝트명 | `celeblife`, 사용 불가 시 `celeblife-app` |
| Production URL | `https://celeblife.vercel.app` 또는 rename fallback에 맞춘 URL |
| Production callback | `https://<production-host>/auth/callback` |
| 기존 Streamlit callback | `https://<existing-streamlit-host>/Login` 유지 |
| Streamlit 운영 | 전환 후 최소 7일 유지, Streamlit만 scheduler이면 중지하지 않음 |
| DB | 운영 Supabase 사용, 기존 데이터 보존 |
| Rollback | Vercel known-good deployment로 즉시 promote, Meta callback은 Streamlit 유지 |

Production 검증 전까지 기존 Streamlit 배포가 사용자의 실질 운영 fallback이다.

## 2. Production 환경 변수

Vercel Project의 Production 환경에 아래 값을 넣는다. Preview 값과 섞지 않는다.

| 이름 | 값 | 비밀값 | 검증 기준 |
| --- | --- | --- | --- |
| `INSTAGRAM_APP_ID` | 운영 Meta Instagram 앱 ID | 아니오 | Meta 앱과 일치 |
| `INSTAGRAM_APP_SECRET` | 운영 Meta Instagram 앱 secret | 예 | Vercel에만 입력 |
| `OAUTH_REDIRECT_URI` | `https://<production-host>/auth/callback` | 아니오 | Meta Redirect URI와 정확히 일치 |
| `CONTACT_EMAIL` | 운영 문의 이메일 | 아니오 | 개인정보/삭제 안내와 일치 |
| `SUPABASE_URL` | 운영 Supabase URL | 아니오 | `https://<SUPABASE_PRODUCTION_PROJECT_REF>.supabase.co` |
| `SUPABASE_KEY` | 운영 Supabase secret/service role key | 예 | `sb_secret_...` 또는 JWT `role=service_role` |
| `SESSION_COOKIE_SECRET` | 32바이트 이상 랜덤 문자열 | 예 | Preview 값과 달라야 함, 길이 32바이트 이상 |

`SUPABASE_PREVIEW_PROJECT_REF`, `SUPABASE_PRODUCTION_PROJECT_REF`, `PREVIEW_SAFE_MODE`는 Preview 격리 검증용이다. Production 필수 환경 변수로 등록하지 않는다.

현재 Vercel Project API 값은 `installCommand=null`, `buildCommand=null`이다. `vercel project inspect` 화면에서 과거 `pip install -r requirements.txt`가 보이더라도 API 값이 null이면 정리할 항목은 없다. API 값이 non-null로 바뀐 경우에만 stale install command를 제거한다. 이 프로젝트는 `requirements.txt`가 아니라 `pyproject.toml`/`uv.lock`과 `[tool.vercel] entrypoint = "asgi:app"`를 기준으로 배포한다.

## 3. Meta 설정

Meta App Dashboard의 Instagram OAuth Redirect URI에 Production 콜백을 추가한다.

```text
https://<production-host>/auth/callback
```

기존 Streamlit 콜백은 삭제하지 않는다.

```text
https://<existing-streamlit-host>/Login
```

운영 검증은 public Business/Creator Instagram 계정으로 진행한다. 앱이 Live/승인 상태인지, 요청 권한이 실제 운영 계정에서 허용되는지 Dashboard에서 확인한다.

## 4. 운영 Supabase Preflight

운영 Supabase에는 먼저 읽기 전용 preflight만 실행한다. 중복 토큰, RLS, 함수/테이블 존재 여부를 확인하기 전에는 migration을 실행하지 않는다.

### 4.1 Key 확인

`SUPABASE_KEY` 기준:

- 새 형식: `sb_secret_...`이면 통과, `sb_publishable_...`이면 중단
- JWT 형식: payload의 `role`이 `service_role`이면 통과, `anon`이면 중단

### 4.2 RLS/정책 확인

```sql
SELECT c.relname AS tablename, c.relrowsecurity AS rls_enabled
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('users', 'tokens', 'insights', 'audience_data', 'collection_log', 'user_consents')
ORDER BY c.relname;

SELECT tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('users', 'tokens', 'insights', 'audience_data', 'collection_log', 'user_consents')
ORDER BY tablename, policyname;
```

`users`, `tokens`, `insights`, `audience_data`, `collection_log`는 RLS가 켜져 있어야 한다. 정책은 service role 전용이어야 한다. `{public}`, `anon`, `authenticated`에 열려 있으면 Production 전환을 중단하고 `migrations/001_scope_rls_to_service_role.sql` 적용 여부를 먼저 결정한다.

### 4.3 Duplicate token 확인

```sql
SELECT user_id, token_type, COUNT(*) AS count
FROM public.tokens
GROUP BY user_id, token_type
HAVING COUNT(*) > 1;
```

행이 나오면 중단한다. `tokens(user_id, token_type)` unique constraint를 추가하기 전에 수동 정리 계획이 필요하다.

### 4.4 동의/RPC 존재 확인

```sql
SELECT to_regclass('public.user_consents') AS user_consents_table;

SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'complete_instagram_onboarding';

SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND table_name = 'tokens'
  AND constraint_type = 'UNIQUE';
```

판단:

- `user_consents`와 RPC가 없고 duplicate token도 없으면, 운영 DB에는 pending `001`/`002` 순서로 적용한다.
- `002`가 이미 적용된 흔적이 있고 버전 문자열만 이전 Preview 값이면, 새 `003` migration으로 RPC의 허용 버전만 최종 값으로 갱신한다.
- 적용 상태가 불명확하면 Production 전환을 중단하고 DB snapshot/backup 이후 별도 복구 가능한 migration을 작성한다.

Production OAuth 검증에 필요한 최종 동의 버전은 다음 값이어야 한다.

| 항목 | 버전 |
| --- | --- |
| Consent schema | `1` |
| Terms | `influencer-v1.2-2026-08-26` |
| Privacy | `privacy-2026-08-26-v3` |
| Instagram permissions | `instagram-permissions-2026-08-26` |

## 5. Vercel Project 전환

1. 프로젝트명을 `celeblife`로 변경한다. 이미 사용 중이면 `celeblife-app`을 사용한다.
2. Production branch는 `main`으로 둔다.
3. Preview/Production 환경 변수가 분리되어 있는지 확인한다.
4. Production 배포의 anonymous access를 확인한다. 일반 사용자가 로그인 없이 `/Login`, `/Privacy`, `/Data-Deletion`을 열 수 있어야 한다.
5. Preview는 계속 보호 상태로 둔다.

## 6. 수동 Production 배포

검증된 feature SHA를 기록한다.

```bash
git rev-parse HEAD
```

로컬 검증을 먼저 실행한다.

```bash
uv run pytest -q
uv run python -c 'import asgi; print(type(asgi.app).__name__)'
```

Production으로 수동 배포한다.

```bash
vercel --prod
```

중요: 이 수동 Production 배포가 성공하고 E2E 검증이 끝나기 전에는 `main`에 merge하지 않는다.

## 7. Production Smoke/E2E

필수 확인:

- 익명 브라우저에서 `https://<production-host>/healthz`가 200과 `{"status":"ok"}`를 반환한다.
- 익명 브라우저에서 `/Login`, `/Privacy`, `/Data-Deletion`이 열린다.
- `/Login`에서 제목 `반응을 읽고, 선택의 기준을 만듭니다.`가 보인다.
- `Instagram으로 계속하기` 후 전체 페이지 동의 화면으로 이동한다.
- 보이는 필수 동의 3개 전에는 OAuth가 시작되지 않는다.
- 필수 동의 후 Meta OAuth 화면으로 이동한다.
- OAuth 승인 후 `/auth/callback`에서 `/Dashboard`로 303 이동한다.
- `cl_session` 쿠키는 `HttpOnly`, `Secure`, `SameSite=Lax`, `Max-Age=604800`이다.
- 운영 Supabase `user_consents`, `users`, `tokens`에 한 트랜잭션 결과가 저장된다.
- Dashboard가 운영 데이터를 읽는다.
- insights 수집/조회가 운영 정책에 맞게 동작한다.
- Vercel 로그에 OAuth `code`, Instagram access token, Supabase key가 찍히지 않는다.

브라우저, DB, 로그 세 가지가 모두 맞아야 Production 통과다.

## 8. `main` Merge

Production E2E가 통과한 뒤에만 feature branch를 `main`에 합친다.

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff codex/vercel-preview
git push origin main
```

merge 후 Vercel 자동 Production 배포가 뜨면 동일 SHA 또는 의도한 merge commit인지 확인하고 `/healthz`, `/Login`, OAuth callback을 다시 smoke 한다.

## 9. Rollback

Production 문제가 발생하면 즉시 known-good deployment로 되돌린다.

1. Vercel dashboard에서 마지막 known-good Production deployment를 Promote/Redeploy한다.
2. Meta Dashboard에는 기존 Streamlit `/Login` callback이 남아 있어야 한다.
3. 필요하면 DNS/custom domain을 known-good deployment 또는 Streamlit 쪽으로 되돌린다.
4. 운영 Supabase migration rollback은 데이터 손실 가능성이 있으므로 자동 실행하지 않는다. DB 문제면 먼저 snapshot/backup과 영향 범위를 확인한다.
5. Git `main`에 merge된 뒤 문제를 발견했다면 revert commit을 만든다. `git reset --hard`로 공유 브랜치를 되감지 않는다.

## 10. Streamlit 유지 조건

Vercel Production 전환 후에도 Streamlit 운영 배포는 최소 7일 유지한다.

Streamlit을 중지하면 안 되는 경우:

- Streamlit이 유일한 scheduler 실행 위치인 경우
- Vercel Production OAuth/DB/insights E2E가 아직 하루 이상 안정적으로 확인되지 않은 경우
- Meta callback, privacy, data deletion URL 중 하나라도 Vercel로 완전히 검증되지 않은 경우

Streamlit 중지는 별도 작업으로 다룬다. 이 cutover runbook의 완료 조건에는 포함하지 않는다.

## 11. 완료 기준

- Vercel project가 `celeblife` 또는 `celeblife-app`으로 정리되었다.
- Production 환경 변수가 Preview/Streamlit과 섞이지 않았고 `SESSION_COOKIE_SECRET`이 Preview 값과 다르다.
- Production anonymous access가 정상이다.
- Production OAuth callback이 Meta에 등록되어 있고 Streamlit callback도 유지되어 있다.
- 운영 Supabase preflight와 필요한 migration이 완료되었다.
- 실제 Business/Creator 계정으로 OAuth, DB 저장, Dashboard/insights 확인이 끝났다.
- 테스트된 feature SHA가 Production에서 통과한 뒤 `main`에 merge되었다.
- known-good deployment rollback 경로가 확인되었다.
- Streamlit 운영 배포는 최소 7일 유지되며, scheduler 역할이 남아 있으면 중지하지 않는다.
