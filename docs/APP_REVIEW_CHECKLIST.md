# Meta App Review Checklist (Min-Pass)

> 상세 가이드: [`docs/COMPLETE_APP_REVIEW_GUIDE.md`](COMPLETE_APP_REVIEW_GUIDE.md) — 처음 제출이라면 가이드를 먼저 읽으세요.

Use this as a reviewer-reproducible pre-submit check.

---

## Business Verification

- [ ] Business Verification 완료 (Advanced Access 필요 시, 2-4주 소요)
- [ ] Meta Business Account가 앱에 연결됨

## App Roles & 테스트 사용자

- [ ] 앱 역할에 테스터 추가 완료 (App Dashboard → App Roles → Roles)
- [ ] Instagram 테스터 추가 완료 (App Dashboard → Instagram → API setup → Step 7)
- [ ] 테스트 계정 정보 준비 (Instagram 사용자명 + 비밀번호)

## App Domains

- [ ] In Meta App Dashboard → Settings → Basic, set `App Domains` to include:
  - [ ] `insta-app.streamlit.app`
  - [ ] (Optional) `localhost` for local testing

## Valid OAuth Redirect URIs

- [ ] In Meta App Dashboard → Instagram → API setup with Instagram login → `Valid OAuth Redirect URIs`, add exact Streamlit callback URLs:
  - [ ] `https://insta-app.streamlit.app/Login`
  - [ ] `http://localhost:8501/Login` (local test, if used)
- [ ] Ensure app env `OAUTH_REDIRECT_URI` matches one registered URI exactly (including `/Login`, scheme, and host).

## Privacy Policy URL

- [ ] Set **Privacy Policy URL** to: `https://insta-app.streamlit.app/Privacy`
- [ ] URL is publicly accessible **without login**.

## Data Deletion Instructions URL

- [ ] Set **Data Deletion Instructions URL** to: `https://insta-app.streamlit.app/Data-Deletion`
- [ ] URL is publicly accessible **without login**.

## API 활동 요건

- [ ] 30일 이내 `instagram_business_basic` API 호출 1회 이상 완료 (Login → OAuth)
- [ ] 30일 이내 `instagram_business_manage_insights` API 호출 1회 이상 완료 (Dashboard 방문)
- [ ] Activity Dashboard에서 호출 기록 확인

## Use Case 설명

- [ ] `instagram_business_basic` Use Case 설명 작성 완료 (앱별 고유 설명)
- [ ] `instagram_business_manage_insights` Use Case 설명 작성 완료 (앱별 고유 설명)
- [ ] 스크린캐스트 내용과 Use Case 설명이 일치하는지 교차 확인

## 스크린캐스트

- [ ] 스크린캐스트 촬영 완료 (MP4, 1080p+, 2-3분)
- [ ] 로그아웃 상태에서 시작
- [ ] `instagram_business_basic` → `/Login` (OAuth grant) and `/Live_Insights` profile/basic account section.
- [ ] `instagram_business_manage_insights` → `/Dashboard` metrics/charts/audience and `/Live_Insights` business insights + audience demographics sections.
- [ ] Keep one continuous 2-3 minute recording showing login, permission grant, each mapped section, then `/Privacy` and `/Data-Deletion`.
- [ ] 브라우저 주소창(URL 경로)이 항상 보임
- [ ] App Secret, 비밀번호, API 키가 화면에 노출되지 않음
- [ ] Note: Audience demographics require 100+ followers. Include this in the submission notes if the test account has fewer followers.

## Live 모드 전환

- [ ] Live 모드 전환 완료 (App Dashboard → Settings → Basic → App Mode → Switch to Live)
- [ ] 전환 후 일반 사용자(심사관)가 OAuth 접근 가능한지 확인

## 최종 제출

- [ ] 제출 노트에 테스트 계정 정보 + 앱 URL 목록 포함
- [ ] Submit 클릭
