# Vercel Preview Runbook

> 목적: 기존 Streamlit 운영 배포는 그대로 두고, `codex/vercel-preview` 브랜치를 Vercel 보호 Preview에서 검증한다. DB는 기본적으로 별도 Preview Supabase를 권장하지만, 명시적 opt-in이 있으면 기존 Supabase를 공유해 OAuth 화면과 콜백까지 확인할 수 있다. 이 문서는 Production 전환 절차가 아니다.

## 1. 배포 경계

| 항목 | 값 |
| --- | --- |
| Git 브랜치 | `codex/vercel-preview` |
| Vercel 프로젝트 | 현재 연결 프로젝트, Production 전환 전에는 Preview 용도로만 사용 |
| Python | `3.12` (`.python-version`) |
| 앱 런타임 | Streamlit `>=1.61,<1.62` ASGI |
| Vercel 엔트리포인트 | `asgi:app` (`pyproject.toml`) |
| Vercel 설정 | `vercel.json`은 스키마만 두고 Python framework detection 사용 |
| 추가 HTTP 라우트 | `/auth/instagram/start`, `/auth/callback`, `/auth/logout`, `/healthz` |
| DB 변경 | 기본값은 별도 Preview Supabase. 기존 Supabase 공유 시 preflight 후 `migrations/001`, `migrations/002`만 적용 |
| 운영 전환 | 하지 않음 |

Evidence boundary:

- `/healthz` 200은 Vercel 함수가 살아 있다는 증거다. DB, UI, OAuth 성공을 증명하지 않는다.
- `/Login` 화면 확인은 UI 렌더링 증거다. OAuth 콜백, Supabase 저장, 세션 생성을 증명하지 않는다.
- 실제 OAuth 성공은 Meta 테스트 계정 또는 앱 역할 계정으로 동의 후 `/auth/callback`에서 Supabase 트랜잭션이 완료되고 `/Dashboard`로 이동해야 증명된다.

## 2. Preview 환경 변수

Vercel Project의 Preview 환경에만 아래 값을 넣는다.

기본 모드는 별도 Preview Supabase 격리다. 기존 Supabase를 공유하려면 `ALLOW_SHARED_SUPABASE_IN_PREVIEW=true`를 명시적으로 넣는다. 이 경우 Supabase URL/key는 기존 Streamlit과 같은 값을 써도 되지만, `OAUTH_REDIRECT_URI`는 반드시 Vercel Preview 전용 `/auth/callback` 값이어야 한다.

| 이름 | 값 | 비밀값 | 검증 기준 |
| --- | --- | --- | --- |
| `INSTAGRAM_APP_ID` | Meta Instagram 앱 ID | 아니오 | Meta 앱과 일치 |
| `INSTAGRAM_APP_SECRET` | Meta Instagram 앱 secret | 예 | Vercel에만 입력 |
| `OAUTH_REDIRECT_URI` | `https://<vercel-preview-host>/auth/callback` | 아니오 | Meta Redirect URI와 정확히 일치 |
| `CONTACT_EMAIL` | 운영 문의 이메일 | 아니오 | 개인정보/삭제 안내와 일치 |
| `SUPABASE_URL` | Supabase URL | 아니오 | 격리 모드: `https://<SUPABASE_PREVIEW_PROJECT_REF>.supabase.co`, 공유 모드: 기존 Supabase URL 허용 |
| `SUPABASE_KEY` | Supabase secret/service role key | 예 | `sb_secret_...` 또는 JWT `role=service_role` |
| `SUPABASE_PREVIEW_PROJECT_REF` | Preview Supabase project ref | 아니오 | 격리 모드 필수, 공유 모드 불필요 |
| `SUPABASE_PRODUCTION_PROJECT_REF` | Production Supabase project ref | 아니오 | 격리 모드 필수, 공유 모드 불필요 |
| `ALLOW_SHARED_SUPABASE_IN_PREVIEW` | `false` 또는 `true` | 아니오 | 기본 `false`; 기존 Supabase 공유 시에만 `true` |
| `SESSION_COOKIE_SECRET` | 32바이트 이상 랜덤 문자열 | 예 | 길이 32바이트 이상 |
| `PREVIEW_SAFE_MODE` | `true` | 아니오 | Preview에서는 쓰기/수집 안전모드 강제 |

`SESSION_COOKIE_SECRET`은 값을 터미널에 남기지 않도록 stdin으로 입력한다.

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' | vercel env add SESSION_COOKIE_SECRET preview --sensitive
```

다른 secret도 `vercel env add <NAME> preview --sensitive`로 넣는다. Vercel Preview Feedback 같은 제품 옵션은 앱 동작 필수 env가 아니다.

## 3. Meta 설정

Meta App Dashboard의 Instagram OAuth Redirect URI에 Preview 콜백을 추가한다.

```text
https://<vercel-preview-host>/auth/callback
```

기존 Streamlit 운영 콜백은 삭제하지 않는다.

```text
https://<existing-streamlit-host>/Login
```

Preview 검증은 Meta 테스트 계정 또는 앱 역할이 있는 계정만 사용한다.

## 4. Vercel 접근 보호

Preview 배포에는 Vercel Authentication을 켠다. 보호 설정 전에는 OAuth 검증을 진행하지 않는다.

확인 기준:

- 비로그인 브라우저에서 Preview URL을 열면 Vercel 보호 화면이 먼저 나온다.
- 보호 통과 후 `/Login` 페이지가 보인다.
- 보호를 우회하는 공개 Preview URL을 공유하지 않는다.

## 5. Supabase 준비

### 5.1 별도 Preview Supabase 사용

새 Preview Supabase 프로젝트를 만든 경우에만 SQL Editor에서 canonical schema를 한 번 실행한다.

```text
supabase_schema.sql
```

이 파일은 다음을 한 번에 만든다.

- `users`, `tokens`, `insights`, `audience_data`, `collection_log`
- `user_consents`
- `tokens(user_id, token_type)` unique constraint
- service role 전용 RLS 정책
- `complete_instagram_onboarding` RPC

### 5.2 기존 Supabase 공유 사용

기존 Streamlit이 쓰는 Supabase를 그대로 Preview에 연결할 수 있다. 단, Vercel Preview 환경변수에 아래 조건을 같이 맞춘다.

- `ALLOW_SHARED_SUPABASE_IN_PREVIEW=true`
- `SUPABASE_URL`과 `SUPABASE_KEY`는 기존 Streamlit과 같은 값 사용 가능
- `SUPABASE_KEY`는 anon/publishable key가 아니라 secret/service role key
- `OAUTH_REDIRECT_URI`는 기존 Streamlit `/Login`이 아니라 Vercel Preview `https://<vercel-preview-host>/auth/callback`
- `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`은 기존 Meta 앱 값과 같아도 됨

기존 Supabase 공유 모드에서는 `supabase_schema.sql`을 다시 실행하지 않는다. 이미 있는 테이블을 통째로 다시 만들려는 목적의 파일이라 운영/기존 프로젝트에는 맞지 않는다.

대신 아래 preflight를 먼저 실행한 뒤, 필요한 경우에만 migration을 순서대로 적용한다.

- `migrations/001_scope_rls_to_service_role.sql`
- `migrations/002_add_consent_onboarding_transaction.sql`

공유 DB preflight:

```sql
SELECT to_regclass('public.users') AS users_table,
       to_regclass('public.tokens') AS tokens_table,
       to_regclass('public.insights') AS insights_table,
       to_regclass('public.audience_data') AS audience_data_table,
       to_regclass('public.collection_log') AS collection_log_table,
       to_regclass('public.user_consents') AS user_consents_table;

SELECT user_id, token_type, COUNT(*) AS count
FROM public.tokens
GROUP BY user_id, token_type
HAVING COUNT(*) > 1;

SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND table_name = 'tokens'
  AND constraint_name = 'tokens_user_type_unique'
  AND constraint_type = 'UNIQUE';

SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'complete_instagram_onboarding';
```

판단 기준:

- 기존 기본 테이블이 없으면 공유 DB로 쓰지 않는다.
- duplicate token 행이 나오면 `002` 적용 전에 수동 정리가 필요하다.
- RLS 정책이 `{public}`, `anon`, `authenticated`에 열려 있으면 `001` 적용을 먼저 검토한다.
- `user_consents`, `complete_instagram_onboarding`, `tokens_user_type_unique`가 없으면 `002`가 필요하다.

적용 후 smoke 확인:

```sql
SELECT to_regclass('public.users') AS users_table,
       to_regclass('public.tokens') AS tokens_table,
       to_regclass('public.user_consents') AS user_consents_table;

SELECT c.relname AS tablename, c.relrowsecurity AS rls_enabled
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('users', 'tokens', 'user_consents', 'insights', 'audience_data', 'collection_log')
ORDER BY c.relname;

SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'complete_instagram_onboarding';
```

모든 테이블은 존재해야 하고, RLS는 켜져 있어야 하며, 정책은 `roles = {service_role}`이어야 한다. `{public}`, `anon`, `authenticated`에 열려 있으면 Preview OAuth 검증을 중단한다.

## 6. Preview 안전모드

`VERCEL_ENV=preview`이면 `PREVIEW_SAFE_MODE=false`가 들어가도 안전모드가 강제된다.

Preview에서 허용되는 작업:

- Instagram OAuth 콜백 처리
- 동의 내역, 사용자, 토큰을 Preview Supabase에 트랜잭션 저장
- 기존 `insights` / `audience_data` 읽기
- `cl_session` HttpOnly 쿠키 생성과 삭제

Preview에서 막는 작업:

- 앱 프로세스 안의 APScheduler 시작
- Dashboard 첫 로그인 자동 수집
- Dashboard 수동 데이터 새로고침
- Settings 수동 토큰 갱신
- Live Insights의 실시간 Instagram API 호출

빈 Dashboard는 Preview 안전모드에서 정상 상태일 수 있다. 환경변수가 없는 Preview 배포는 화면 확인만 허용되며, 최종 Instagram OAuth 버튼은 비활성화되어야 한다.

## 7. 동의 게이트

새 로그인 흐름은 모바일 기준으로 다음 순서를 따른다.

1. `/Login` 소개 화면
2. `/auth/instagram/start`에서 10분짜리 HttpOnly 브라우저 바인딩 쿠키 생성
3. 전체 페이지 약관/동의 화면
4. 보이는 필수 동의 3개를 모두 체크한 뒤 Instagram OAuth 시작
5. Meta 승인 후 `/auth/callback`
6. 브라우저 바인딩 검증과 Supabase RPC 성공 후 `cl_session` 생성, 바인딩 쿠키 삭제, `/Dashboard` 이동

보이는 필수 동의 3개:

- 만 14세 이상
- 서비스 이용약관
- 개인정보 수집 및 이용

Instagram 데이터 접근과 분석 고지는 개인정보 수집 및 이용 상세 안에 포함한다. OAuth `state`와 Supabase 감사 레코드는 기존 스키마를 유지하기 위해 내부 `instagram_permissions_accepted=true`를 계속 포함한다.

Preview OAuth 검증에 필요한 최종 동의 버전:

| 항목 | 버전 |
| --- | --- |
| Consent schema | `1` |
| Terms | `influencer-v1.2-2026-08-26` |
| Privacy | `privacy-2026-08-26-v3` |
| Instagram permissions | `instagram-permissions-2026-08-26` |

콜백은 다음 조건을 모두 만족할 때만 성공한다.

- state HMAC 서명 유효
- state TTL 유효
- 동의 스키마와 약관/개인정보/Instagram 권한 버전 유효
- 보이는 필수 동의 3개와 내부 Instagram 권한 감사 필드가 모두 true
- 동의 bundle hash 유효
- state의 브라우저 바인딩과 서명된 `cl_consent_binding` HttpOnly 쿠키가 일치
- Preview Supabase isolation 조건 유효
- `complete_instagram_onboarding` RPC 성공

콜백 실패 시 토큰이나 세션을 남기지 않는다.

## 8. 배포와 Smoke Test

1. 브랜치 확인

```bash
git branch --show-current
```

예상값:

```text
codex/vercel-preview
```

2. 로컬 테스트

```bash
uv run pytest -q
```

3. ASGI import 확인

```bash
uv run python -c 'import asgi; print(type(asgi.app).__name__)'
```

4. Vercel Preview 배포

```bash
vercel --target preview
```

5. 배포 후 확인

```bash
curl -i https://<vercel-preview-host>/healthz
```

예상 응답은 HTTP 200과 `{"status":"ok"}`이다. `/healthz`는 DB나 비밀값을 읽지 않는 liveness 전용이다.

6. UI 확인

- 보호된 Preview URL에서 `/Login` 접속
- 소개 화면 제목이 `반응을 읽고, 선택의 기준을 만듭니다.`인지 확인
- `Instagram으로 계속하기` 선택 후 전체 페이지 약관/동의 화면으로 이동하는지 확인
- 모바일 폭에서 줄간격, 터치 영역, 하단 CTA가 겹치지 않는지 확인
- 보이는 필수 동의 3개 전에는 최종 OAuth 버튼이 비활성화되어 있는지 확인
- 뒤로가기를 누르면 동의 상태가 초기화되는지 확인

7. OAuth 확인

- 보호된 Preview URL에서 `/Login` 접속
- 동의 화면에서 보이는 필수 동의 3개 선택
- 최종 Instagram OAuth 버튼 클릭
- Meta 테스트 계정으로 승인
- 콜백 URL이 `/auth/callback`인지 확인
- 성공 후 `/Dashboard`로 303 리다이렉트되는지 확인
- 브라우저 쿠키에 `cl_session`이 있고 `HttpOnly`, `Secure`, `SameSite=Lax`, `Max-Age=604800`인지 확인
- Preview Supabase의 `user_consents`에 1행이 저장되었고 보이는 3개 동의와 내부 `instagram_permissions_accepted` boolean이 모두 true인지 확인
- Preview 로그에 OAuth `code`, Instagram access token, Supabase key가 찍히지 않는지 확인

8. Dashboard 확인

- 기존 데이터가 있으면 읽기 전용으로 표시되는지 확인
- 데이터 새로고침 버튼이 비활성화되어 있는지 확인
- 빈 상태라면 Preview 안전모드 안내가 표시되는지 확인

9. 장시간 연결 확인

- Dashboard를 40분 이상 열어 둔다.
- 연결이 끊기거나 새로고침이 필요하면 재로그인 없이 `cl_session` 쿠키로 세션이 복원되는지 확인한다.

## 9. 롤백

Preview 검증 실패 시:

1. Vercel Preview 배포를 비활성화하거나 해당 deployment를 삭제한다.
2. Meta App Dashboard에서 Vercel Preview `/auth/callback` URI만 제거한다.
3. 기존 Streamlit 운영 URI `/Login`은 유지한다.
4. Preview Supabase 프로젝트는 폐기하거나, Preview DB에서 `supabase_schema.sql`로 만든 객체만 삭제한다.
5. 운영 Supabase에는 아무 작업도 하지 않는다.
6. GitHub 수동 workflow는 schedule이 없으므로 자동 실행 중단 작업은 없다.

## 10. 완료 기준

- Vercel Preview가 보호 설정 뒤에만 접근된다.
- `/healthz`가 200을 반환한다.
- `/Login` 소개 화면과 전체 페이지 동의 화면이 모바일에서 겹침 없이 표시된다.
- 보이는 필수 동의 3개 전에는 OAuth가 시작되지 않는다.
- OAuth가 `/auth/callback`에서 완료되고 `/Dashboard`로 이동한다.
- Preview Supabase에 동의 내역, 사용자, 토큰이 한 트랜잭션으로 저장된다.
- Preview에서 수집/토큰 갱신/Live Insights 호출이 막혀 있다.
- Dashboard가 기존 데이터를 읽거나 안전한 빈 상태를 보여준다.
- 40분 재연결 후에도 세션이 복원된다.
- 기존 Streamlit 운영 배포와 Meta `/Login` redirect가 그대로 유지된다.
