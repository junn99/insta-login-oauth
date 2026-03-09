# Meta App Review 완전 가이드

> **Instagram Login (Business Login) 전용** — Facebook Login이 아닙니다.
>
> 이 문서는 Meta App Review 제출부터 승인까지의 **전체 프로세스**를 다룹니다.
> 빠른 체크만 필요하면 → [`APP_REVIEW_CHECKLIST.md`](APP_REVIEW_CHECKLIST.md)
> 한 장 요약이 필요하면 → [`META_APP_REVIEW_ONE_PAGE_CARD.md`](META_APP_REVIEW_ONE_PAGE_CARD.md)

---

## 목차

1. [사전 준비물 / Prerequisites](#1-사전-준비물--prerequisites)
2. [Business Verification (⚠️ 2-4주 소요)](#2-business-verification-️-2-4주-소요--가장-먼저-시작)
3. [App Roles & 테스트 사용자](#3-app-roles--테스트-사용자)
4. [Meta 콘솔 설정](#4-meta-콘솔-설정)
5. [Development 모드 테스트](#5-development-모드-테스트)
6. [제출 전 API 활동 요건 (⚠️ 필수)](#6-제출-전-api-활동-요건-️-필수)
7. [Use Case 설명 작성 (⚠️ 제출 폼 필수)](#7-use-case-설명-작성-️-제출-폼-필수-항목)
8. [스크린캐스트 녹화](#8-스크린캐스트-녹화)
9. [Live 모드 전환 (⚠️ 제출 직전에)](#9-live-모드-전환-️-제출-직전에)
10. [제출 워크스루](#10-제출-워크스루)
11. [흔한 심사 탈락 사유 & 대응](#11-흔한-심사-탈락-사유--대응)
12. [반려 대응 템플릿](#12-반려-대응-템플릿)
13. [승인 후 유지 관리](#13-승인-후-유지-관리)

---

## 1. 사전 준비물 / Prerequisites

시작 전에 아래 항목이 모두 갖춰져 있어야 합니다.

### 계정/권한

- **Meta Developer 계정** — 앱 소유자(Admin) 또는 관리자(Developer) 권한
- **Instagram Business 또는 Creator 계정** (개인 계정 불가)
  - 팔로워 **100명 이상** 권장 (오디언스 인구통계 데이터에 필요)
  - 최소 **1개 이상 게시물** + 활동 이력 필요 (인사이트 데이터 생성 조건)

### 배포

- **Streamlit Cloud 배포 완료** — 배포 URL 확보 (예: `https://[YOUR-DOMAIN].streamlit.app`)
- 아래 라우트가 모두 접근 가능해야 함:
  - `/Login`, `/Dashboard`, `/Live_Insights`, `/Privacy`, `/Data_Deletion`

### 환경변수

6개 환경변수 설정 완료 (`.env.example` 참조):

```bash
INSTAGRAM_APP_ID=...
INSTAGRAM_APP_SECRET=...
OAUTH_REDIRECT_URI=https://[YOUR-DOMAIN].streamlit.app/Login
CONTACT_EMAIL=...
SUPABASE_URL=...
SUPABASE_KEY=...
```

Streamlit Cloud 사용 시: Settings → Secrets에 동일하게 입력

---

## 2. Business Verification (⚠️ 2-4주 소요 — 가장 먼저 시작)

### 왜 필요한가

2023년 2월부터 **Advanced Access** 권한을 받으려면 Business Verification이 필수입니다. Advanced Access 없이는 앱 역할에 추가된 사용자만 OAuth를 사용할 수 있습니다.

### 면제 조건

**본인 소유 계정만** 사용하고 Standard Access로 충분한 경우 Business Verification은 불필요합니다. 단, 일반 사용자에게 공개하려면 반드시 필요합니다.

### 진행 경로

1. **App Dashboard** → **Settings** → **Basic**
2. **"Business account"** 섹션 → **Meta Business Account 연결**
3. Business Settings에서 인증 시작

### 필요 서류

| 항목 | 설명 |
|------|------|
| 사업자등록증 | 사업자등록번호가 포함된 공식 서류 |
| 법인명 | 사업자등록증상 정식 명칭 |
| 주소 | 사업장 소재지 (서류와 일치) |
| 전화번호 | 법인 연락처 |
| 사업자등록번호 | 한국: 10자리 사업자등록번호 |

### 소요 시간

- 일반적으로 **2-4주** 소요
- 서류 보완 요청 시 추가 시간 필요
- **다른 준비와 병행 가능하므로 가장 먼저 시작할 것**

---

## 3. App Roles & 테스트 사용자

Development 모드에서는 **앱 역할(App Role)이 부여된 사용자만** OAuth 인증이 가능합니다. 심사 제출 전에 테스터를 추가해야 합니다.

### 역할 종류

| 역할 | 설명 |
|------|------|
| **Admin** | 앱 전체 관리 (설정 변경, 역할 관리, 삭제) |
| **Developer** | 앱 설정 보기, API 호출, 테스트 |
| **Tester** | OAuth 로그인만 가능 (설정 변경 불가) |
| **Analytics User** | 인사이트 데이터 조회만 가능 |

### 테스터 추가 방법

1. **App Dashboard** → **App Roles** → **Roles**
2. **Add People** 클릭
3. 테스터의 Facebook 계정 이메일 또는 이름 입력
4. 역할 선택 (보통 **Tester**)
5. 초대된 사람이 수락해야 활성화

### Instagram 테스트 계정 추가

1. **App Dashboard** → **Instagram** → **API setup**
2. **Step 7: Add Instagram Testers** 섹션
3. Instagram 사용자명 입력 → 초대
4. Instagram 앱에서 초대 수락: **설정** → **웹사이트** → **초대** → **수락**

### 제한

- Business Verification 완료 전: 테스터 **최대 50명**
- Business Verification 후: 제한 없음 (Advanced Access)

---

## 4. Meta 콘솔 설정

### 4.1 App Domains

- **경로**: App Dashboard → **Settings** → **Basic** → `App Domains`
- **값**: `[YOUR-DOMAIN].streamlit.app`
- 로컬 테스트 시 `localhost` 추가 가능 (제출 전 제거 권장)

### 4.2 Valid OAuth Redirect URIs

- **경로**: App Dashboard → **Instagram** → **API setup with Instagram login** → **Business login settings**
- **값**: `https://[YOUR-DOMAIN].streamlit.app/Login`
- `OAUTH_REDIRECT_URI` 환경변수와 **완전히 동일**해야 함 (스킴, 호스트, 경로, 대소문자 모두)
- 로컬 테스트용: `http://localhost:8501/Login` (제출 전 제거 권장)

### 4.3 Privacy Policy URL

- **경로**: App Dashboard → **Settings** → **Basic** → `Privacy Policy URL`
- **값**: `https://[YOUR-DOMAIN].streamlit.app/Privacy`
- **반드시 로그인 없이 공개 접근** 가능해야 함

### 4.4 Data Deletion Request URL

- **경로**: App Dashboard → **Instagram** → **Business login settings** → `Data deletion request URL`
- **값**: `https://[YOUR-DOMAIN].streamlit.app/Data_Deletion`
- **반드시 로그인 없이 공개 접근** 가능해야 함

### 설정 확인 팁

모든 URL 설정 후, 브라우저 **시크릿 모드**에서 각 URL을 직접 열어 접근 가능한지 확인하세요.

---

## 5. Development 모드 테스트

**제출 전에 Dev 모드에서 모든 기능이 정상 동작하는지 반드시 확인하세요.**

Development 모드에서는 앱 역할이 있는 사용자만 OAuth가 가능합니다 (섹션 3 참조).

### 테스트 순서

| 단계 | 페이지 | 확인 항목 |
|------|--------|-----------|
| 1 | `/Login` | Instagram OAuth 승인 → 성공 메시지 + 계정 정보 표시 |
| 2 | `/Dashboard` | 인사이트 수집 시작 → 지표/차트/오디언스 섹션 표시 |
| 3 | `/Live_Insights` | 프로필/인사이트/오디언스 3개 섹션 모두 실시간 데이터 표시 |
| 4 | `/Privacy` | 로그인 없이 접근 가능 (시크릿 모드에서 확인) |
| 5 | `/Data_Deletion` | 로그인 없이 접근 가능 (시크릿 모드에서 확인) |

### 문제 발생 시

이 단계에서 발생하는 모든 문제를 해결한 후 다음 단계로 진행하세요.
흔한 문제는 [섹션 11](#11-흔한-심사-탈락-사유--대응)을 참조하세요.

---

## 6. 제출 전 API 활동 요건 (⚠️ 필수)

### 규칙

제출 **30일 이내에** 각 권한당 최소 **1회** 성공적인 API 호출이 있어야 합니다. 이 조건이 충족되지 않으면 심사가 반려됩니다.

### 구체적 방법

| 권한 | 어떻게 호출하나 | 자동으로 호출되는 API |
|------|-----------------|----------------------|
| `instagram_business_basic` | `/Login`에서 OAuth 로그인 | `/me` 엔드포인트 자동 호출 |
| `instagram_business_manage_insights` | `/Dashboard` 또는 `/Live_Insights` 방문 | `/{ig-user-id}/insights` 엔드포인트 자동 호출 |

### 확인 방법

1. **App Dashboard** → **Activity Dashboard** (또는 **API Activity**)
2. 각 권한별 API 호출 로그 확인
3. 최근 30일 이내에 성공적 호출이 있는지 확인

### 주의

- 제출 당일 날짜 기준이 아닌, **심사 시점**에서 30일 이내를 확인합니다
- 심사에 1-2주 소요될 수 있으므로, **제출 직전에 한 번 더 로그인 + Dashboard 방문**을 권장합니다

---

## 7. Use Case 설명 작성 (⚠️ 제출 폼 필수 항목)

### 규칙

- 각 권한마다 **고유한 설명**이 필요합니다 (복붙 금지)
- 심사관이 확인하는 것: **스크린캐스트에 보이는 내용과 설명이 일치**하는지
- 영어로 작성 (Meta 심사관은 대부분 영어 사용)

### `instagram_business_basic` Use Case 템플릿

```text
Our app uses instagram_business_basic to retrieve the username, user ID,
profile picture, follower count, and media count of Instagram Business/Creator
accounts during OAuth onboarding. This data is displayed on the Login page
to confirm the correct account is connected, and stored to identify the user
in subsequent API calls. Without this permission, we cannot verify the identity
of the connecting account or display any user context within our dashboard.
```

### `instagram_business_manage_insights` Use Case 템플릿

```text
Our app uses instagram_business_manage_insights to retrieve account-level
metrics (views, reach, accounts engaged, total interactions) and audience
demographics (city, country, age, gender distributions) for connected
Instagram Business/Creator accounts. These metrics are displayed in our
Dashboard page as summary cards, time-series charts, and demographic
visualizations. The Live Insights page demonstrates real-time API calls
for each metric type. Without this permission, our core analytics dashboard
— the primary value proposition — cannot function.
```

### 작성 팁

- 앱이 **구체적으로 어떤 데이터**를 가져오는지 명시
- 그 데이터가 **어디에 표시**되는지 (어떤 페이지) 명시
- 이 권한이 **없으면 왜 안 되는지** 설명
- 모호한 표현 ("다양한 기능에 사용") 대신 구체적 기능 나열

---

## 8. 스크린캐스트 녹화

### 형식 요구사항

| 항목 | 요구사항 |
|------|----------|
| **파일 형식** | MP4 |
| **해상도** | 1080p (1920×1080) 이상 |
| **모니터 폭** | 1440px 이하 권장 (심사관이 글자를 읽을 수 있도록) |
| **오디오** | 불필요 (심사관이 음소거 상태로 검토) |
| **자막/주석** | 추가 권장 (동작 설명용 텍스트 오버레이) |
| **길이** | 2-3분, 끊김 없는 **1개** 영상 |

### 녹화 도구

- **OBS Studio** (무료, 크로스플랫폼)
- **QuickTime Player** (macOS 기본)
- **Camtasia** (유료, 자막 편집 용이)

### 반드시 보여야 할 것

- ✅ **로그아웃 상태에서 시작** (깨끗한 상태)
- ✅ **전체 OAuth 인증 플로우** (로그인 버튼 → Instagram 권한 승인 → 리다이렉트 복귀)
- ✅ **각 권한이 실제 사용되는 화면** (실제 데이터, mock 데이터 금지)
- ✅ **브라우저 주소창**이 항상 보여야 함 (URL 경로 확인용)

### 절대 보이면 안 되는 것

- ❌ App Secret
- ❌ 비밀번호 (Instagram, Meta 계정)
- ❌ API 키/토큰
- ❌ 환경변수 값

### 촬영 스크립트

#### 0:00 - 0:15 — 앱 공개 URL + 목적 소개

1. 브라우저 주소창에 배포 URL 표시
2. 사이드바에서 페이지 목록 보여주기

#### 0:15 - 0:45 — `/Login` OAuth 전체 플로우

1. `/Login` 페이지 이동
2. "Instagram으로 로그인" 클릭 → Instagram OAuth 화면으로 이동
3. 권한 승인 화면 (2개 권한 표시): `instagram_business_basic`, `instagram_business_manage_insights`
4. 승인 후 `/Login` 복귀 → 성공 메시지 + 계정 정보 표시

#### 0:45 - 1:20 — `/Dashboard` 권한 사용 증빙

1. `/Dashboard` 이동
2. 지표 카드, 시계열 차트, 오디언스 인구통계 섹션 스크롤
3. 권한 배지(`instagram_business_manage_insights`)가 화면에 보이도록

#### 1:20 - 2:00 — `/Live_Insights` 실시간 API 호출 증빙

1. `/Live_Insights` 이동
2. 3개 섹션 순서대로 보여주기:
   - **프로필 정보** (`instagram_business_basic`)
   - **비즈니스 인사이트** (`instagram_business_manage_insights`)
   - **오디언스 인구통계** (`instagram_business_manage_insights`)
3. 각 섹션의 **"API Details"** expander를 열어 호출 엔드포인트 표시

#### 2:00 - 2:20 — 정책 URL 증빙

1. `/Privacy` 이동 (로그인 없이 접근 가능함을 강조)
2. `/Data_Deletion` 이동 (로그인 없이 접근 가능함을 강조)

---

## 9. Live 모드 전환 (⚠️ 제출 직전에)

### 왜 필요한가

Development 모드에서는 앱 역할이 부여된 사용자만 OAuth 인증이 가능합니다. **심사관은 앱 역할이 없으므로**, Live 모드로 전환해야 심사관이 앱에 접근할 수 있습니다.

### 전환 경로

**App Dashboard** → **Settings** → **Basic** → **App Mode** → **Switch to Live**

### 전환 전 확인 사항

- [ ] Business Verification 완료 (Advanced Access 필요 시)
- [ ] Privacy Policy URL 설정 완료
- [ ] Data Deletion Request URL 설정 완료
- [ ] 모든 기능이 Dev 모드에서 정상 동작 확인 완료

### 주의사항

- **너무 일찍 전환하지 마세요** — 승인되지 않은 권한은 Live 모드에서도 제한됩니다
- **전환 후에는** 일반 사용자도 OAuth 접근이 가능합니다 (심사관 포함)
- Live 모드 전환은 **되돌릴 수 있습니다** (다시 Development 모드로 전환 가능)

---

## 10. 제출 워크스루

### 제출 경로

**App Dashboard** → **App Review** → **Permissions and Features**

### 단계별 진행

#### Step 1: 권한 선택

1. `instagram_business_basic` 선택 → **Request** 클릭
2. `instagram_business_manage_insights` 선택 → **Request** 클릭

> 💡 이 앱은 위 2개 권한만 필요합니다. 불필요한 권한을 요청하면 탈락 사유가 됩니다.

#### Step 2: Use Case 설명 입력

1. `instagram_business_basic` → [섹션 7](#7-use-case-설명-작성-️-제출-폼-필수-항목)의 템플릿 입력
2. `instagram_business_manage_insights` → 동일 섹션의 템플릿 입력

#### Step 3: 테스트 계정 정보 입력

- **Instagram 사용자명**: 테스트에 사용할 Instagram Business/Creator 계정 사용자명
- **비밀번호**: 해당 Instagram 계정 비밀번호

> ⚠️ 심사관이 직접 로그인하여 재현할 수 있도록 **실제 동작하는 테스트 계정**을 제공해야 합니다.

#### Step 4: 스크린캐스트 업로드

- [섹션 8](#8-스크린캐스트-녹화)에서 촬영한 MP4 파일 업로드

#### Step 5: 제출 노트 작성

```text
Test account details:
- Instagram username: [사용자명]
- Account type: Business/Creator
- Note: Audience demographics data requires 100+ followers.
  If the test account has fewer than 100 followers, the audience
  section may show limited data. All other metrics will display
  normally.

App URLs:
- Login: https://[YOUR-DOMAIN].streamlit.app/Login
- Dashboard: https://[YOUR-DOMAIN].streamlit.app/Dashboard
- Live Insights: https://[YOUR-DOMAIN].streamlit.app/Live_Insights
- Privacy Policy: https://[YOUR-DOMAIN].streamlit.app/Privacy
- Data Deletion: https://[YOUR-DOMAIN].streamlit.app/Data_Deletion
```

#### Step 6: Submit

- 모든 항목 입력 확인 후 **Submit** 클릭
- 심사 소요 시간: 보통 **1-5 영업일** (경우에 따라 2주까지)

---

## 11. 흔한 심사 탈락 사유 & 대응

| 탈락 사유 | 원인 | 해결 |
|-----------|------|------|
| **앱 접근 불가** | Development 모드 상태 | [Live 모드로 전환](#9-live-모드-전환-️-제출-직전에) |
| **API 활동 없음** | 30일 내 API 호출 기록 없음 | [로그인 → Dashboard 방문](#6-제출-전-api-활동-요건-️-필수)하여 호출 생성 |
| **권한 불일치** | 스크린캐스트 내용 ≠ Use Case 설명 | 설명과 영상을 교차 확인하여 일치시키기 |
| **일반적/모호한 설명** | 복붙 또는 추상적인 Use Case 설명 | [앱별 고유 설명](#7-use-case-설명-작성-️-제출-폼-필수-항목) 작성 |
| **Privacy URL 문제** | URL 깨짐/로그인 필요/빈 화면 | 시크릿 모드에서 직접 URL 접근 테스트 |
| **Business Verification 미완** | Advanced Access 요청 시 인증 미완 | 제출 전 [Business Verification](#2-business-verification-️-2-4주-소요--가장-먼저-시작) 완료 |
| **불필요 권한 요청** | 사용하지 않는 권한을 요청 | 2개 권한(`basic`, `manage_insights`)만 요청 |
| **테스트 계정 문제** | 잘못된 비밀번호/비활성 계정 | 제출 직전에 테스트 계정으로 직접 로그인 확인 |

### 추가 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `redirect_uri mismatch` | Meta 콘솔 등록값 ≠ `OAUTH_REDIRECT_URI` | Meta 콘솔에 정확한 URL 등록 (스킴/호스트/경로 완전 일치) |
| `invalid state` / state 검증 실패 | 리다이렉트 과정에서 state 유실 | 시크릿 모드에서 단일 탭으로 재시도 |
| 오디언스 데이터 없음 | 팔로워 100명 미만 | 팔로워 100명 이상 계정 사용, 제출 노트에 설명 |
| 인사이트 데이터 없음 | 신규 계정/활동 부족 | 게시물 올리고 하루 뒤 재시도 |

---

## 12. 반려 대응 템플릿

심사가 반려(rejected)된 경우, 아래 템플릿을 참고하여 재제출하세요.

```text
Hello Meta App Review Team,

Thank you for your feedback. We have addressed the reported issues.

1) Public policy URLs (accessible without login)
- Privacy Policy: https://[YOUR-DOMAIN].streamlit.app/Privacy
- Data Deletion Instructions: https://[YOUR-DOMAIN].streamlit.app/Data_Deletion

2) OAuth reproduction flow
1. Open https://[YOUR-DOMAIN].streamlit.app/Login
2. Click the Instagram login button and grant the requested permissions.
3. After redirect back to /Login, the connected Instagram Business account
   details are shown.

3) Permission usage proof
- /Dashboard: account metrics (views, reach, accounts engaged, total
  interactions), time-series charts, and audience demographics
- /Live_Insights: profile info (instagram_business_basic), business
  insights and audience demographics (instagram_business_manage_insights)

4) Permissions requested
- instagram_business_basic: Account profile info (username, user ID,
  profile picture, follower/media counts)
- instagram_business_manage_insights: Business insights (views, reach,
  engagement) and audience demographics (city, country, age, gender)

5) Evidence
- Updated screencast link: <insert_link>

Please let us know if any additional evidence is needed.

Best regards,
<App Owner Name>
```

### 재제출 팁

- 반려 사유를 **정확히 읽고** 해당 항목만 수정
- 스크린캐스트를 **새로 촬영** (이전 영상 재사용 지양)
- 재제출 전 **30일 이내 API 활동** 조건 재확인
- 반려 사유가 불명확하면 Meta 지원팀에 문의 가능

---

## 13. 승인 후 유지 관리

### Privacy Policy 유지

- 개인정보 처리방침 URL이 항상 접근 가능한 상태를 유지
- 앱 기능 변경 시 처리방침 내용도 업데이트
- Meta가 정기적으로 URL 접근성을 확인함

### API 사용량 모니터링

- **App Dashboard** → **Activity Dashboard**에서 API 호출량 확인
- Rate Limit 초과 시 앱 기능에 영향 (429 에러)
- 비정상적 호출 패턴은 앱 정지 사유가 될 수 있음

### 권한 변경 시 재심사

- 새로운 권한을 추가하려면 **App Review를 다시 제출**해야 함
- 기존 승인된 권한을 제거하는 것은 자유
- 권한 변경 없이 앱 기능 업데이트는 재심사 불필요

### 토큰 갱신

- Long-lived 토큰은 **60일** 유효
- 만료 전에 자동 갱신되는지 확인 (앱의 `refresh_tokens.py` job)
- 토큰 만료 시 사용자가 다시 OAuth 인증해야 함
- **Settings** 페이지에서 토큰 상태 확인 가능

### Data Deletion 요청 처리

- 사용자가 데이터 삭제를 요청하면 **합리적인 시간 내에 처리**
- Meta가 삭제 요청 처리 여부를 확인할 수 있음
- `/Data_Deletion` 페이지가 항상 접근 가능해야 함

---

## 부록: 자주 사용하는 경로 & 링크

### 앱 페이지

| 페이지 | 경로 | 용도 |
|--------|------|------|
| Login | `/Login` | OAuth 인증 |
| Dashboard | `/Dashboard` | 인사이트 대시보드 |
| Live Insights | `/Live_Insights` | 실시간 API 데모 |
| Privacy | `/Privacy` | 개인정보 처리방침 |
| Data Deletion | `/Data_Deletion` | 데이터 삭제 안내 |
| Settings | `/Settings` | 계정/토큰 관리 |

### Meta 콘솔 경로

| 설정 | 콘솔 경로 |
|------|----------|
| App Settings | App Dashboard → Settings → Basic |
| OAuth Redirect URIs | App Dashboard → Instagram → API setup → Business login settings |
| App Roles | App Dashboard → App Roles → Roles |
| App Review | App Dashboard → App Review → Permissions and Features |
| Activity Dashboard | App Dashboard → Activity Dashboard |
| App Mode (Dev/Live) | App Dashboard → Settings → Basic → App Mode |

### 요청하는 권한 2개

| 권한 | 용도 | 사용 페이지 |
|------|------|-------------|
| `instagram_business_basic` | 계정 기본 정보 (username, 팔로워 등) | Login, Dashboard, Live Insights |
| `instagram_business_manage_insights` | 인사이트 지표 + 오디언스 인구통계 | Dashboard, Live Insights |
