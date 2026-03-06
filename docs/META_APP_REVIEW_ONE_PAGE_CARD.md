# Meta App Review One-Page Card

운영자가 제출 직전에 **딱 한 장으로 확인**할 수 있는 요약 카드입니다.

---

## 0) 오늘 목표

- 목표: Meta 심사자가 앱에서 권한 사용 흐름을 재현할 수 있게 준비
- 기준: URL 접근 가능 + OAuth 정상 + 권한별 화면 증빙 + 스크린캐스트 확보

---

## 1) 5분 사전 점검

- [ ] 배포 URL 확인: `https://your-app.streamlit.app`
- [ ] `OAUTH_REDIRECT_URI`가 `https://your-app.streamlit.app/Login`와 완전 일치
- [ ] `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET` 설정 완료
- [ ] `CONTACT_EMAIL` 실제 메일로 설정

---

## 2) Meta 콘솔 필수값

### Settings -> Basic
- [ ] `App Domains`에 `your-app.streamlit.app`
- [ ] `Privacy Policy URL` = `https://your-app.streamlit.app/Privacy`
- [ ] `Data Deletion Instructions URL` = `https://your-app.streamlit.app/Data_Deletion`

### Instagram -> API setup with Instagram login
- [ ] `Valid OAuth Redirect URIs`에 `https://your-app.streamlit.app/Login`

---

## 3) 심사 재현 플로우 (2~3분 영상)

1. `/Login` 접속 -> Instagram 로그인/권한 승인
2. `/Dashboard`에서 지표/차트/오디언스 섹션 표시
3. `/Live_Insights`에서 프로필/인사이트/오디언스 섹션 표시
4. `/Privacy`, `/Data_Deletion` 공개 접근 확인

필수 권한 매핑:
- `instagram_business_basic` -> `/Login`, `/Live_Insights`
- `instagram_business_manage_insights` -> `/Dashboard`, `/Live_Insights`

---

## 4) 즉시 중단해야 하는 Fail 신호

- `redirect_uri mismatch`
- `/Privacy` 또는 `/Data_Deletion` 로그인 요구/에러
- `/Login`에서 state 검증 반복 실패
- 권한 사용 근거 화면이 영상에 안 잡힘

조치:
- 제출 중단 -> 콘솔/환경변수/도메인 재확인 -> 다시 촬영

---

## 5) 제출 메시지 초간단 템플릿

```text
Hello Meta App Review Team,

We addressed the feedback and prepared reproducible evidence.

Public URLs:
- Privacy: https://your-app.streamlit.app/Privacy
- Data Deletion: https://your-app.streamlit.app/Data_Deletion

Repro steps:
1) Open https://your-app.streamlit.app/Login
2) Grant requested permissions (instagram_business_basic, instagram_business_manage_insights)
3) Verify permission usage in /Dashboard and /Live_Insights

Screencast: <insert_link>

Thank you.
```

---

## 6) 운영 메모

- 문서 내 URL이 실서비스 도메인과 일치하는지 최종 확인하기
- 오디언스 데이터는 팔로워 100명 이상 필요 — 제출 노트에 포함
- 상세 절차는 `docs/META_APP_REVIEW_NEXT_STEPS.md` 참고
- 최소 체크리스트는 `docs/APP_REVIEW_CHECKLIST.md` 참고
