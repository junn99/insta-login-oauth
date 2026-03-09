# Meta App Review One-Page Card

운영자가 제출 직전에 **딱 한 장으로 확인**할 수 있는 요약 카드입니다.

> 상세 가이드: [`docs/COMPLETE_APP_REVIEW_GUIDE.md`](COMPLETE_APP_REVIEW_GUIDE.md)
> 체크리스트: [`docs/APP_REVIEW_CHECKLIST.md`](APP_REVIEW_CHECKLIST.md)

---

## 0) 오늘 목표

- 목표: Meta 심사자가 앱에서 권한 사용 흐름을 재현할 수 있게 준비
- 기준: URL 접근 가능 + OAuth 정상 + 권한별 화면 증빙 + 스크린캐스트 확보

---

## 1) 사전 완료 확인 (⚠️ 며칠~주 전에 시작해야 하는 항목)

- [ ] **Business Verification** 완료 (2-4주 소요, 가장 먼저 시작)
- [ ] **앱 역할에 테스터** 추가 완료

---

## 2) 5분 사전 점검

- [ ] 배포 URL 확인: `https://insta-app.streamlit.app`
- [ ] `OAUTH_REDIRECT_URI`가 `https://insta-app.streamlit.app/Login`와 완전 일치
- [ ] `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET` 설정 완료
- [ ] `CONTACT_EMAIL` 실제 메일로 설정

---

## 3) Meta 콘솔 필수값

### Settings → Basic
- [ ] `App Domains`에 `insta-app.streamlit.app`
- [ ] `Privacy Policy URL` = `https://insta-app.streamlit.app/Privacy`

### Instagram → Business login settings
- [ ] `Valid OAuth Redirect URIs`에 `https://insta-app.streamlit.app/Login`
- [ ] `Data Deletion Request URL` = `https://insta-app.streamlit.app/Data_Deletion`

---

## 4) API 활동 확인 (30일 이내 필수)

- [ ] `/Login`에서 OAuth 로그인 완료 → `instagram_business_basic` 호출 기록 생성
- [ ] `/Dashboard` 방문 → `instagram_business_manage_insights` 호출 기록 생성
- [ ] Activity Dashboard에서 두 권한 모두 호출 기록 확인

---

## 5) 심사 재현 플로우 (2~3분 영상)

1. `/Login` 접속 → Instagram 로그인/권한 승인
2. `/Dashboard`에서 지표/차트/오디언스 섹션 표시
3. `/Live_Insights`에서 프로필/인사이트/오디언스 섹션 표시
4. `/Privacy`, `/Data_Deletion` 공개 접근 확인

필수 권한 매핑:
- `instagram_business_basic` → `/Login`, `/Live_Insights`
- `instagram_business_manage_insights` → `/Dashboard`, `/Live_Insights`

---

## 6) Live 모드 전환 (제출 직전)

- [ ] **App Mode** → **Switch to Live** (Settings → Basic)
- [ ] 전환 전 확인: Business Verification 완료, Privacy URL, Data Deletion URL 설정
- [ ] 전환 후: 심사관(일반 사용자)이 OAuth 접근 가능

---

## 7) 즉시 중단해야 하는 Fail 신호

- `redirect_uri mismatch`
- `/Privacy` 또는 `/Data_Deletion` 로그인 요구/에러
- `/Login`에서 state 검증 반복 실패
- 권한 사용 근거 화면이 영상에 안 잡힘
- 30일 이내 API 호출 기록 없음

조치:
- 제출 중단 → 콘솔/환경변수/도메인 재확인 → 다시 촬영

---

## 8) 운영 메모

- 문서 내 URL이 실서비스 도메인과 일치하는지 최종 확인하기
- 오디언스 데이터는 팔로워 100명 이상 필요 — 제출 노트에 포함
- Use Case 설명은 각 권한별 고유하게 작성 (복붙 금지) — 템플릿은 [가이드 섹션 7](COMPLETE_APP_REVIEW_GUIDE.md#7-use-case-설명-작성-️-제출-폼-필수-항목) 참조
- 반려 대응 템플릿은 [가이드 섹션 12](COMPLETE_APP_REVIEW_GUIDE.md#12-반려-대응-템플릿) 참조
