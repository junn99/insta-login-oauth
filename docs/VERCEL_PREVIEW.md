# Vercel Preview Runbook

> 목적: 기존 Streamlit 운영 배포는 그대로 두고, `codex/vercel-preview` 브랜치를 Vercel 비공개 Preview로 검증한다. 이 문서는 Production 전환 절차가 아니다.

## 1. 현재 배포 경계

| 항목 | 값 |
|------|-----|
| Git 브랜치 | `codex/vercel-preview` |
| Vercel 플랜 | Hobby |
| Python | `3.12` (`.python-version`) |
| 앱 런타임 | Streamlit `>=1.61,<1.62` ASGI |
| Vercel 엔트리포인트 | `asgi:app` (`pyproject.toml`) |
| ASGI 파일 | `asgi.py` |
| 추가 HTTP 라우트 | `/auth/callback`, `/auth/logout`, `/healthz` |
| DB 변경 | 없음 |
| 운영 전환 | 하지 않음 |

Vercel Hobby Function은 `vercel.json`에서 `maxDuration: 300`으로 설정되어 있다. Streamlit WebSocket 연결은 장시간 유지되지 않을 수 있으므로 Preview 검증 때 40분 이상 켜 둔 뒤 새로고침/재연결 동작을 확인한다.

## 2. Preview 환경 변수

Vercel Project의 Preview 환경에만 다음 값을 넣는다.

```text
INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET
OAUTH_REDIRECT_URI
CONTACT_EMAIL
SUPABASE_URL
SUPABASE_KEY
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

## 5. Supabase 사전 확인

DB 마이그레이션은 실행하지 않는다. 먼저 현재 키와 정책을 읽기 전용으로 확인한다.

`SUPABASE_KEY` 확인 기준:

- 새 형식: `sb_secret_...`이면 통과, `sb_publishable_...`이면 중단
- JWT 형식: payload의 `role`이 `service_role`이면 통과, `anon`이면 중단

Supabase SQL Editor에서 RLS 활성 상태와 정책을 읽기 전용으로 확인한다.

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

## 6. Preview 안전모드

`VERCEL_ENV=preview`이면 `PREVIEW_SAFE_MODE=false`가 들어가도 안전모드가 강제된다.

Preview에서 허용되는 작업:

- Instagram OAuth 콜백 처리
- `users` / `tokens` 기존 테이블에 사용자와 토큰 저장
- 기존 `insights` / `audience_data` 읽기
- `cl_session` HttpOnly 쿠키 생성과 삭제

Preview에서 막는 작업:

- 앱 프로세스 안의 APScheduler 시작
- Dashboard 첫 로그인 자동 수집
- Dashboard 수동 데이터 새로고침
- Settings 수동 토큰 갱신
- Live Insights의 실시간 Instagram API 호출

빈 Dashboard는 Preview 안전모드에서 정상 상태일 수 있다.

## 7. 수동 GitHub Workflow

워크플로우 파일은 `.github/workflows/manual-jobs.yml`이다.

동작:

- `workflow_dispatch`만 있다.
- `schedule`은 없다.
- `execute=false` 기본값에서는 테스트만 실행된다.
- `execute=true`이고 `job=collect` 또는 `job=refresh`일 때만 `preview-db` environment의 승인/시크릿을 사용한다.

GitHub는 workflow 파일이 기본 브랜치에 있어야 `workflow_dispatch`를 노출한다. 따라서 이 파일만 별도 PR/커밋으로 `main`에 반영하고, Vercel 앱 코드나 배포 설정은 Preview 검증 전 `main`에 합치지 않는다.

Preview 검증 중에는 실제 수집/갱신 job을 실행하지 않는다. 필요해지면 보호된 GitHub environment 승인 뒤 수동으로 한 번만 실행한다.

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

6. OAuth 확인

- 보호된 Preview URL에서 `/Login` 접속
- Instagram 로그인 버튼 클릭
- Meta 테스트 계정으로 승인
- 콜백 URL이 `/auth/callback`인지 확인
- 성공 후 `/Dashboard`로 303 리다이렉트되는지 확인
- 브라우저 쿠키에 `cl_session`이 있고 `HttpOnly`, `Secure`, `SameSite=Lax`, `Max-Age=604800`인지 확인
- Preview 로그에 OAuth `code`, Instagram access token, Supabase key가 찍히지 않는지 확인

7. Dashboard 확인

- 기존 데이터가 있으면 읽기 전용으로 표시되는지 확인
- 데이터 새로고침 버튼이 비활성화되어 있는지 확인
- 빈 상태라면 Preview 안전모드 안내가 표시되는지 확인

8. 장시간 연결 확인

- Dashboard를 40분 이상 열어 둔다.
- 연결이 끊기거나 새로고침이 필요하면 재로그인 없이 `cl_session` 쿠키로 세션이 복원되는지 확인한다.

## 9. 롤백

Preview 검증 실패 시:

1. Vercel Preview 배포를 비활성화하거나 해당 deployment를 삭제한다.
2. Meta App Dashboard에서 Vercel Preview `/auth/callback` URI만 제거한다.
3. 기존 Streamlit 운영 URI `/Login`은 유지한다.
4. Supabase 스키마는 변경하지 않았으므로 DB 롤백은 없다.
5. GitHub 수동 workflow는 schedule이 없으므로 자동 실행 중단 작업은 없다.

## 10. 완료 기준

- Vercel Preview가 보호 설정 뒤에만 접근된다.
- `/healthz`가 200을 반환한다.
- OAuth가 `/auth/callback`에서 완료되고 `/Dashboard`로 이동한다.
- Preview에서 수집/토큰 갱신/Live Insights 호출이 막혀 있다.
- Dashboard가 기존 데이터를 읽거나 안전한 빈 상태를 보여준다.
- 40분 재연결 후에도 세션이 복원된다.
- 기존 Streamlit 운영 배포와 Meta `/Login` redirect가 그대로 유지된다.
