# Meta App Review: Next Steps Runbook (운영자 가이드)

이 문서는 Instagram Login으로 마이그레이션 후, **Meta App Review 제출을 위해 운영자가 해야 할 일**을 실행 순서로 정리한 런북입니다.

참고 문서:
- `docs/APP_REVIEW_CHECKLIST.md`
- `docs/PROJECT_GUIDE.md`

---

## 1) 목적과 범위

목적:
- Meta App Review(권한 심사) 제출 전에, **배포/설정/재현 자료(스크린캐스트) 준비**를 빠짐없이 수행
- 심사관이 그대로 따라해도 재현 가능한 상태(공개 URL, OAuth 동작, 정책 URL 접근성)를 확보

범위:
- 운영 절차(콘솔 설정/배포 후 점검/스크린캐스트 촬영/제출/반려 대응)

---

## 2) 시작 전 준비물

계정/권한:
- Meta Developer 계정(앱 소유자/관리자 권한)
- Instagram Business 또는 Creator 계정 (테스트용)

배포 URL:
- Streamlit Cloud 배포 URL (예: `https://your-app.streamlit.app`)
- 아래 페이지 라우트가 존재해야 합니다:
  - `/Login`
  - `/Dashboard`
  - `/Live_Insights`
  - `/Privacy`
  - `/Data_Deletion`

시크릿/환경변수:
- `INSTAGRAM_APP_ID`
- `INSTAGRAM_APP_SECRET`
- `OAUTH_REDIRECT_URI` (예: `https://your-app.streamlit.app/Login`)
- `SUPABASE_URL`, `SUPABASE_KEY`
- `CONTACT_EMAIL` (실제 연락처 메일)

도구:
- 화면 녹화 툴(스크린캐스트 1개 영상으로 권한 사용 증명)

---

## 3) 10분 사전 점검 (Quick Preflight Checklist)

1. 공개 정책 페이지 접근성
- 액션: 브라우저 시크릿 모드에서 아래 URL을 직접 열기
  - `https://your-app.streamlit.app/Privacy`
  - `https://your-app.streamlit.app/Data_Deletion`
- Pass: 로그인 없이 페이지가 즉시 렌더링됨(에러/빈 화면 없음)

2. OAuth 리다이렉트 URL 일치
- 액션: 배포 환경 변수 `OAUTH_REDIRECT_URI` 확인 + Meta 콘솔에 등록된 redirect URI 확인
- Pass: `OAUTH_REDIRECT_URI`와 Meta 콘솔의 등록 값이 **완전히 동일**

3. App Domains 포함 여부
- 액션: Meta App Dashboard -> Settings -> Basic -> `App Domains`
- Pass: `your-app.streamlit.app` 포함

4. 핵심 라우트 존재 확인
- 액션: 배포 URL에서 직접 열기
  - `/Login` — 로그인 버튼 보임
  - `/Dashboard` — 로그인 후 데이터 섹션 표시
  - `/Live_Insights` — 로그인 후 실시간 데이터 표시

---

## 4) 배포 후 실제 확인 절차 (Public URLs + OAuth E2E)

1. OAuth 로그인 E2E
- 액션:
  1) `/Login` 접속
  2) "Instagram으로 로그인" 클릭 → Instagram OAuth로 이동
  3) 권한 승인 화면에서 2개 권한이 표시되는지 확인 후 승인
  4) `/Login`으로 돌아와 성공 메시지 확인
- Pass: 승인 후 로그인 성공, Dashboard에서 데이터 표시

2. 권한-기능 매핑 확인(심사 핵심)
- `/Login`: `instagram_business_basic` — 계정 기본 정보
- `/Dashboard`: `instagram_business_manage_insights` — 지표, 차트, 오디언스
- `/Live_Insights`: 프로필 / 인사이트 / 오디언스 3개 섹션

---

## 5) Meta 콘솔 설정값 체크

1. Settings -> Basic
- `App Domains`: `your-app.streamlit.app`
- `Privacy Policy URL`: `https://your-app.streamlit.app/Privacy`
- `Data Deletion Instructions URL`: `https://your-app.streamlit.app/Data_Deletion`

2. Instagram -> API setup with Instagram login
- `Valid OAuth Redirect URIs`: `https://your-app.streamlit.app/Login`

---

## 6) 스크린캐스트 촬영 스크립트

원칙:
- 끊김 없는 1개 영상(2~3분)
- 화면에 권한 배지/섹션 제목이 보이도록 촬영

### 0:00 - 0:15 (앱 공개 URL + 목적 소개)
1) 브라우저 주소창에 배포 URL을 보여줌
2) 사이드바에서 페이지 목록 표시

### 0:15 - 0:45 (/Login OAuth 흐름)
1) `/Login` 이동
2) "Instagram으로 로그인" 클릭 → Instagram OAuth로 이동
3) 권한 승인 화면 (2개 권한: `instagram_business_basic`, `instagram_business_manage_insights`)
4) 승인 후 `/Login`에서 성공 메시지 + 계정 정보

### 0:45 - 1:20 (/Dashboard 권한 사용 증빙)
1) `/Dashboard` 이동
2) 지표/차트/오디언스 섹션 스크롤
3) 권한 배지가 화면에 보이도록

### 1:20 - 2:00 (/Live_Insights 실시간 API 호출 증빙)
1) `/Live_Insights` 이동
2) 다음 섹션을 순서대로:
   - 프로필 정보 (`instagram_business_basic`)
   - 비즈니스 인사이트 (`instagram_business_manage_insights`)
   - 오디언스 인구통계 (`instagram_business_manage_insights`)
3) 각 섹션의 "API Details" expander 열어서 호출 엔드포인트 보여주기

### 2:00 - 2:20 (정책 URL 증빙)
1) `/Privacy` 이동 (로그인 없이 접근 가능함을 강조)
2) `/Data_Deletion` 이동

---

## 7) 제출 전 최종 체크리스트 (Go/No-Go)

아래가 모두 체크되면 제출(Go), 하나라도 Fail이면 No-Go:

- [ ] `/Privacy` 로그인 없이 접근 가능
- [ ] `/Data_Deletion` 로그인 없이 접근 가능
- [ ] Meta 콘솔 `App Domains` 설정 완료
- [ ] Meta 콘솔 `Valid OAuth Redirect URIs` 설정 완료
- [ ] `OAUTH_REDIRECT_URI` 일치
- [ ] `/Login` -> OAuth 승인 -> 복귀 성공
- [ ] `/Dashboard`와 `/Live_Insights`에서 권한 사용 증빙 명확
- [ ] 스크린캐스트에 주소창(경로)이 보임

---

## 8) 자주 막히는 이슈와 해결

1) redirect_uri mismatch
- 원인: Meta 콘솔 등록값 vs `OAUTH_REDIRECT_URI` 불일치
- 해결: Meta 콘솔에 정확한 URL 등록

2) invalid state / state 검증 실패
- 원인: 리다이렉트 과정에서 state 유실
- 해결: 시크릿 모드에서 단일 탭으로 재시도

3) 오디언스 데이터 없음
- 원인: 팔로워 100명 미만
- 해결: 팔로워 100명 이상 계정 사용, 제출 노트에 설명 포함

4) 인사이트 데이터 없음
- 원인: 신규 계정/활동 부족
- 해결: 게시물 올리고 하루 뒤 재시도

---

## 9) 제출 후 반려 대응 템플릿

```text
Hello Meta App Review Team,

Thank you for your feedback. We have addressed the reported issues.

1) Public policy URLs (accessible without login)
- Privacy Policy: https://your-app.streamlit.app/Privacy
- Data Deletion Instructions: https://your-app.streamlit.app/Data_Deletion

2) OAuth reproduction flow
1. Open https://your-app.streamlit.app/Login
2. Click the Instagram login button and grant the requested permissions.
3. After redirect back to /Login, the connected Instagram Business account details are shown.

3) Permission usage proof
- /Dashboard: metrics, charts, and audience demographics
- /Live_Insights: profile info, business insights, audience demographics

4) Permissions requested
- instagram_business_basic: Account profile info
- instagram_business_manage_insights: Business insights and audience demographics

5) Evidence
- Updated screencast link: <insert_link>

Please let us know if any additional evidence is needed.

Best regards,
<App Owner Name>
```

---

### 부록: 운영자가 자주 쓰는 링크/경로

- Login: `/Login`
- Dashboard: `/Dashboard`
- Live Insights: `/Live_Insights`
- Privacy: `/Privacy`
- Data Deletion: `/Data_Deletion`
