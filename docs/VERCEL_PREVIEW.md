# Vercel Preview Runbook

> 목적: 기존 Streamlit 운영 배포와 운영 Supabase는 그대로 두고, `codex/vercel-preview` 브랜치를 Vercel 비공개 Preview와 별도 Preview Supabase에서 검증한다. 이 문서는 Production 전환 절차가 아니다.

## 1. 현재 배포 경계

| 항목 | 값 |
|------|-----|
| Git 브랜치 | `codex/vercel-preview` |
| Vercel 플랜 | Hobby |
| Python | `3.12` (`.python-version`) |
| 앱 런타임 | Streamlit `>=1.61,<1.62` ASGI |
| Vercel 엔트리포인트 | `asgi:app` (`pyproject.toml`) |
| ASGI 파일 | `asgi.py` |
| 추가 HTTP 라우트 | `/auth/instagram/start`, `/auth/callback`, `/auth/logout`, `/healthz` |
| DB 변경 | Preview Supabase에만 `migrations/002_add_consent_onboarding_transaction.sql` 적용 |
| 운영 전환 | 하지 않음 |

Vercel 설정 파일은 스키마만 두고 프레임워크 감지를 허용한다. Streamlit WebSocket 연결은 장시간 유지되지 않을 수 있으므로 Preview 검증 때 40분 이상 켜 둔 뒤 새로고침/재연결 동작을 확인한다.

Evidence boundary:

- `/healthz` 200은 Vercel 함수가 살아 있다는 증거다. DB, UI, OAuth 성공을 증명하지 않는다.
- `/Login` 화면 확인은 UI 렌더링 증거다. OAuth 콜백, Supabase 저장, 세션 생성을 증명하지 않는다.
- 실제 OAuth 성공은 Meta 테스트 계정으로 동의 후 `/auth/callback`에서 Supabase 트랜잭션이 완료되고 `/Dashboard`로 이동해야 증명된다.

## 2. Preview 환경 변수

Vercel Project의 Preview 환경에만 다음 값을 넣는다.

```text
INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET
OAUTH_REDIRECT_URI
CONTACT_EMAIL
SUPABASE_URL
SUPABASE_KEY
SUPABASE_PREVIEW_PROJECT_REF
SUPABASE_PRODUCTION_PROJECT_REF
SESSION_COOKIE_SECRET
PREVIEW_SAFE_MODE=true
```

`OAUTH_REDIRECT_URI`는 Vercel Preview URL 기준으로 정확히 아래 경로까지 포함한다.

```text
https://<vercel-preview-host>/auth/callback
```

기존 Streamlit 운영 배포의 Meta Redirect URI는 그대로 유지한다.

```text
https://<existing-streamlit-host>/Login
```

`SESSION_COOKIE_SECRET`은 32바이트 이상이어야 한다. 로컬 터미널에 값을 남기지 않으려면 생성값을 바로 Vercel CLI stdin으로 전달한다.

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' | vercel env add SESSION_COOKIE_SECRET preview --sensitive
```

길이만 로컬에서 확인할 때는 값을 출력하지 않는다.

```bash
python3 -c 'import secrets; value=secrets.token_urlsafe(48); assert len(value.encode()) >= 32; print(len(value.encode()))'
```

나머지 환경 변수도 `vercel env add <NAME> preview --sensitive`로 넣는다. 비밀값을 셸 히스토리에 남기지 않도록 파일 또는 stdin 입력을 사용한다.

Supabase Preview isolation:

- `SUPABASE_URL`은 Preview 전용 Supabase 프로젝트 URL이어야 한다.
- `SUPABASE_PREVIEW_PROJECT_REF`는 Preview 프로젝트 ref다.
- `SUPABASE_PRODUCTION_PROJECT_REF`는 운영 프로젝트 ref다.
- 두 ref 값은 서로 달라야 한다.
- `SUPABASE_URL`의 host는 `https://<SUPABASE_PREVIEW_PROJECT_REF>.supabase.co`와 정확히 일치해야 한다.

`VERCEL_ENV=preview`에서 위 조건이 맞지 않으면 OAuth/DB 작업을 진행하지 않는다. 운영 Supabase URL이나 운영 service role key를 Preview 환경에 넣지 않는다.

## 3. Meta 설정

Meta App Dashboard에는 Vercel Preview 콜백을 추가한다.

```text
https://<vercel-preview-host>/auth/callback
```

기존 Streamlit 콜백은 삭제하지 않는다.

```text
https://<existing-streamlit-host>/Login
```

Preview 검증은 Meta 테스트 계정 또는 앱 역할이 있는 계정만 사용한다.

## 4. Vercel 접근 보호

Vercel Project의 Standard Protection에서 Preview 배포용 Vercel Authentication을 켠다. 이 설정이 되기 전에는 OAuth 검증을 진행하지 않는다.

확인 기준:

- Preview URL을 비로그인 브라우저에서 열면 Vercel 보호 화면이 먼저 나온다.
- 보호 통과 후 `/Login` 페이지가 보인다.
- 보호를 우회하는 공개 Preview URL을 공유하지 않는다.

## 5. Supabase Preview 준비

Preview OAuth는 별도 Preview Supabase에서만 검증한다. 운영 Supabase에는 이 섹션의 SQL을 실행하지 않는다.

`SUPABASE_KEY` 확인 기준:

- 새 형식: `sb_secret_...`이면 통과, `sb_publishable_...`이면 중단
- JWT 형식: payload의 `role`이 `service_role`이면 통과, `anon`이면 중단

Preview Supabase SQL Editor에서 기존 RLS 활성 상태와 정책을 먼저 읽기 전용으로 확인한다.

```sql
SELECT c.relname AS tablename, c.relrowsecurity AS rls_enabled
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('users', 'tokens', 'insights', 'audience_data', 'collection_log')
ORDER BY c.relname;

SELECT tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('users', 'tokens', 'insights', 'audience_data', 'collection_log')
ORDER BY tablename;
```

다섯 테이블 모두 `rls_enabled = true`여야 하고, 정책은 `roles = {service_role}`로 제한되어 있어야 한다. RLS가 꺼져 있거나 정책이 없거나 `{public}`/익명 접근 정책이 보이면 Preview OAuth를 중단하고 키/정책을 먼저 정리한다. 이 runbook에서는 `migrations/001_scope_rls_to_service_role.sql`을 실행하지 않는다.

### 5.1 Migration 002 적용

Preview Supabase SQL Editor에서 다음 파일을 실행한다.

```text
migrations/002_add_consent_onboarding_transaction.sql
```

이 마이그레이션의 역할:

- `user_consents` 테이블 생성
- `tokens(user_id, token_type)` 중복 방지 제약 추가
- OAuth 콜백에서 사용자, 동의 내역, 토큰을 하나의 트랜잭션으로 저장하는 `complete_instagram_onboarding` RPC 생성
- RPC 실행 권한을 service role로 제한

적용 전 확인:

```sql
SELECT user_id, token_type, COUNT(*) AS count
FROM public.tokens
GROUP BY user_id, token_type
HAVING COUNT(*) > 1;
```

행이 나오면 중단한다. 002는 중복 토큰을 자동 정리하지 않는다.

적용 후 smoke 확인:

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

`user_consents_table`은 `user_consents`, RPC는 1행, `tokens` unique constraint는 1개 이상이어야 한다.

Rollback은 Preview Supabase에서만 수행한다.

```sql
DROP FUNCTION IF EXISTS public.complete_instagram_onboarding(
  text,text,text,timestamptz,text,integer,text,text,text,boolean,boolean,boolean,
  boolean,timestamptz,text
);
DROP INDEX IF EXISTS public.idx_user_consents_user_accepted_at;
DROP TABLE IF EXISTS public.user_consents;
ALTER TABLE public.tokens DROP CONSTRAINT IF EXISTS tokens_user_type_unique;
```

Rollback 뒤에는 OAuth 콜백이 실패하는 것이 정상이다. 다시 검증하려면 002를 재적용한다.

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

빈 Dashboard는 Preview 안전모드에서 정상 상태일 수 있다.

환경변수가 없는 Preview 배포는 UI 확인만 허용된다. 이 경우 `/Login`과 동의 화면은 렌더링되지만 최종 Instagram OAuth 버튼은 비활성화되어야 한다. 이 상태는 화면 검토용이며 OAuth 성공 증거가 아니다.

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
- 이용약관
- 개인정보 수집 및 이용

Instagram 데이터 접근·분석 고지는 개인정보 수집·이용 상세 안에 포함한다. OAuth `state`와 Supabase 감사 레코드는 기존 스키마를 유지하기 위해 `instagram_permissions_accepted=true`를 계속 포함한다.

OAuth `state`에는 서명된 동의 스냅샷이 포함되어야 한다. 콜백은 다음 조건을 모두 만족할 때만 성공한다.

- state HMAC 서명 유효
- state TTL 유효
- 동의 스키마와 약관/개인정보/Instagram 권한 버전 유효
- 보이는 필수 동의 3개와 내부 Instagram 권한 감사 필드가 모두 true
- 동의 bundle hash 유효
- state의 브라우저 바인딩과 서명된 `cl_consent_binding` HttpOnly 쿠키가 일치
- Preview Supabase isolation 조건 유효
- `complete_instagram_onboarding` RPC 성공

콜백 실패 시 토큰이나 세션을 남기지 않는다.

## 8. 법무/카피 경계

Preview의 약관/개인정보/Instagram 권한 문구는 검증용 draft다. 화면 구조와 동작 검증에는 사용할 수 있지만, Production 전환 전에는 법무/개인정보 검토를 받아야 한다.

현재 Preview 동의 버전:

| 항목 | 버전 |
|------|------|
| Consent schema | `1` |
| Terms | `preview-2026-08-26` |
| Privacy | `preview-2026-08-26` |
| Instagram permissions | `preview-2026-08-26` |

## 9. 수동 GitHub Workflow

워크플로우 파일은 `.github/workflows/manual-jobs.yml`이다.

동작:

- `workflow_dispatch`만 있다.
- `schedule`은 없다.
- `execute=false` 기본값에서는 테스트만 실행된다.
- `execute=true`이고 `job=collect` 또는 `job=refresh`일 때만 `preview-db` environment의 승인/시크릿을 사용한다.

GitHub는 workflow 파일이 기본 브랜치에 있어야 `workflow_dispatch`를 노출한다. 따라서 이 파일만 별도 PR/커밋으로 `main`에 반영하고, Vercel 앱 코드나 배포 설정은 Preview 검증 전 `main`에 합치지 않는다.

Preview 검증 중에는 실제 수집/갱신 job을 실행하지 않는다. 필요해지면 보호된 GitHub environment 승인 뒤 수동으로 한 번만 실행한다.

## 10. 배포와 Smoke Test

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
- 본문이 한 줄 카피로 줄었는지 확인
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

## 11. 롤백

Preview 검증 실패 시:

1. Vercel Preview 배포를 비활성화하거나 해당 deployment를 삭제한다.
2. Meta App Dashboard에서 Vercel Preview `/auth/callback` URI만 제거한다.
3. 기존 Streamlit 운영 URI `/Login`은 유지한다.
4. Preview Supabase에만 5.1의 rollback SQL을 실행한다.
5. 운영 Supabase에는 아무 작업도 하지 않는다.
6. GitHub 수동 workflow는 schedule이 없으므로 자동 실행 중단 작업은 없다.

## 12. 완료 기준

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
