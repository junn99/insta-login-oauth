# urlinsta - 프로젝트 가이드

> Instagram Insights Dashboard / Meta App Review 대비 전체 정리

---

## 1. 시스템 전체 흐름

### 1.1 아키텍처

```
┌──────────────┐     OAuth      ┌──────────────┐
│   사용자      │ ──────────────► │  Instagram   │
│  (브라우저)   │ ◄────token───── │  OAuth 2.0   │
└──────┬───────┘                 │ (api.insta)  │
       │                         └──────────────┘
       │  Streamlit                      │
       ▼                                 │
┌──────────────┐     API 호출    ┌──────────────┐
│  Streamlit   │ ──────────────► │  Instagram   │
│  App (7페이지)│                 │  Graph API   │
└──────┬───────┘                 │ (graph.insta)│
       │                         └──────────────┘
       │  CRUD
       ▼
┌──────────────┐
│   Supabase   │  users, tokens, insights, audience_data, collection_log
│  (PostgreSQL)│
└──────────────┘
```

### 1.2 사용자 여정 (User Flow)

```
1. 사용자가 Login 페이지 방문
2. "Instagram으로 로그인" 버튼 클릭
3. Instagram OAuth 화면으로 리다이렉트 (2개 권한 요청)
4. 사용자가 권한 승인
5. Instagram이 code + state와 함께 redirect_uri로 리다이렉트
6. 앱이 code를 short-lived token으로 교환 (POST api.instagram.com)
7. short-lived token을 long-lived token (60일)으로 교환 (GET graph.instagram.com)
8. Instagram /me 엔드포인트로 계정 정보 조회
9. 계정 정보 + 토큰을 Supabase에 저장
10. Dashboard로 이동 → 첫 로그인 시 인사이트 자동 수집
11. 이후 6시간마다 백그라운드 자동 수집
```

### 1.3 페이지 구성

| 페이지 | 파일 | 역할 |
|--------|------|------|
| Home | `app.py` | 앱 소개, 로그인 상태 표시 |
| Dashboard | `pages/1_📊_Dashboard.py` | 인사이트 차트, 지표, 오디언스 |
| Login | `pages/2_🔐_Login.py` | Instagram OAuth 로그인 |
| Settings | `pages/3_⚙️_Settings.py` | 계정 관리, 토큰 갱신 |
| Privacy | `pages/4_🔒_Privacy.py` | 개인정보 처리방침 (Meta 필수) |
| Data Deletion | `pages/5_🗑️_Data_Deletion.py` | 데이터 삭제 안내 (Meta 필수) |
| Live Insights | `pages/6_🔍_Live_Insights.py` | 실시간 API 호출 데모 (심사용) |

### 1.4 요청하는 Instagram 권한 2개

| 권한 | 용도 | 사용 위치 |
|------|------|-----------|
| `instagram_business_basic` | 계정 기본 정보 (username, 팔로워 등) | Login, Dashboard, Live Insights |
| `instagram_business_manage_insights` | 인사이트 지표 + 오디언스 인구통계 | Dashboard, Live Insights |

---

## 2. OAuth 엔드포인트

| 단계 | URL | 메서드 |
|------|-----|--------|
| 인증 | `https://www.instagram.com/oauth/authorize` | GET (redirect) |
| 토큰 교환 | `https://api.instagram.com/oauth/access_token` | POST |
| Long-lived 토큰 | `https://graph.instagram.com/access_token` | GET |
| 토큰 갱신 | `https://graph.instagram.com/refresh_access_token` | GET |
| 계정 정보 | `https://graph.instagram.com/me` | GET |
| 인사이트 | `https://graph.instagram.com/{ig-user-id}/insights` | GET |

---

## 3. 당신이 해야 할 일 (순서대로)

### Phase 1: 환경 설정

#### 3.1 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참고):

```bash
# Instagram App Credentials (Meta 개발자 콘솔에서 확인)
INSTAGRAM_APP_ID=실제_앱_ID
INSTAGRAM_APP_SECRET=실제_앱_시크릿

# OAuth Redirect URI (Streamlit Cloud URL + /Login)
OAUTH_REDIRECT_URI=https://insta-app.streamlit.app/Login

# Contact Email
CONTACT_EMAIL=your_contact_email

# Supabase (supabase.com 대시보드 → Settings → API)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_secret_key
```

**Streamlit Cloud 사용 시:** Settings → Secrets에 같은 값 입력

#### 3.2 Supabase 스키마

`supabase_schema.sql` 파일을 Supabase SQL Editor에서 실행.

기존 DB가 있는 경우 마이그레이션:
```sql
ALTER TABLE users ALTER COLUMN facebook_page_id DROP NOT NULL;
ALTER TABLE users ALTER COLUMN facebook_page_id SET DEFAULT NULL;
-- 선택: 기존 page 토큰 정리
DELETE FROM tokens WHERE token_type = 'page';
```

### Phase 2: 로컬 테스트

#### 3.3 전체 플로우 테스트

| 단계 | 확인 항목 | 예상 결과 |
|------|-----------|-----------|
| 1 | 앱 메인 페이지 열기 | "설정 누락" 메시지 없이 정상 표시 |
| 2 | Login 페이지 → "Instagram으로 로그인" 클릭 | Instagram OAuth 화면으로 이동 |
| 3 | Instagram에서 권한 승인 | Login 페이지로 리다이렉트, 성공 메시지 |
| 4 | Dashboard 페이지 이동 | 자동으로 인사이트 수집 시작 |
| 5 | Live Insights 페이지 | 3개 섹션 모두 실시간 데이터 표시 |
| 6 | Privacy 페이지 | 한영 이중언어 개인정보 처리방침 |
| 7 | Data Deletion 페이지 | 한영 이중언어 삭제 안내 |

### Phase 3: Meta App Review 제출

#### 3.4 Meta 개발자 콘솔 설정

| 항목 | 값 |
|------|----|
| **Privacy Policy URL** | `https://insta-app.streamlit.app/Privacy` |
| **Data Deletion Instructions URL** | `https://insta-app.streamlit.app/Data_Deletion` |
| **앱 도메인** | `insta-app.streamlit.app` |

#### 3.5 App Review 제출

2개 권한을 제출:

| 권한 | 제출 시 필요 |
|------|-------------|
| `instagram_business_basic` | 스크린캐스트: 로그인 → 프로필 정보 표시 |
| `instagram_business_manage_insights` | 스크린캐스트: Dashboard 지표 + Live Insights + 오디언스 |

---

## 4. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| "앱이 설정되지 않았습니다" | 환경변수 누락 | `.env` 또는 Streamlit Secrets 확인 |
| Instagram 화면에서 에러 | `OAUTH_REDIRECT_URI` 불일치 | Meta 콘솔의 "Valid OAuth Redirect URIs"에 정확한 URL 등록 |
| 인사이트 데이터 없음 | 비즈니스 계정 활동 부족 | 게시물 올리고 하루 뒤 재시도 |
| 오디언스 데이터 없음 | 팔로워 100명 미만 | 팔로워 100명 이상 필요 |

---

## 5. 프로젝트 구조

```
insta-login-oauth/
├── app.py                          # 메인 앱 (홈페이지 + 스케줄러)
├── pyproject.toml                  # 의존성 정의
├── .env.example                    # 환경변수 템플릿
├── supabase_schema.sql             # DB 스키마
├── src/
│   ├── config.py                   # 환경변수 → Config 클래스
│   ├── models.py                   # Pydantic 모델 (User, Token, Insight 등)
│   ├── oauth.py                    # Instagram OAuth 전체 플로우
│   ├── database.py                 # Supabase CRUD 함수
│   ├── instagram_api.py            # Instagram Graph API 클라이언트
│   ├── insights_collector.py       # 인사이트 수집 로직
│   ├── rate_limiter.py             # API 요청 제한
│   └── permission_badge.py         # 권한 배지 표시 헬퍼
├── pages/
│   ├── 1_📊_Dashboard.py           # 인사이트 대시보드
│   ├── 2_🔐_Login.py              # OAuth 로그인
│   ├── 3_⚙️_Settings.py           # 계정/토큰 관리
│   ├── 4_🔒_Privacy.py            # 개인정보 처리방침
│   ├── 5_🗑️_Data_Deletion.py     # 데이터 삭제 안내
│   └── 6_🔍_Live_Insights.py      # 실시간 API 데모
├── jobs/
│   ├── collect_insights.py         # 정기 인사이트 수집 job
│   └── refresh_tokens.py           # 정기 토큰 갱신 job
└── docs/
    ├── PROJECT_GUIDE.md            # 이 문서
    ├── COMPLETE_APP_REVIEW_GUIDE.md # 심사 전체 워크스루 (13섹션)
    ├── APP_REVIEW_CHECKLIST.md     # 심사 체크리스트
    └── META_APP_REVIEW_ONE_PAGE_CARD.md  # 1장 요약
```

---

## 6. 기술 스택

| 영역 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | Streamlit | >= 1.31.0 |
| 데이터베이스 | Supabase (PostgreSQL) | - |
| API | Instagram Graph API | graph.instagram.com |
| 인증 | Instagram Login (OAuth 2.0) | api.instagram.com |
| 데이터 시각화 | Plotly + Pandas | >= 5.18.0 / >= 2.1.0 |
| 모델 | Pydantic | >= 2.5.0 |
| HTTP | Requests + Tenacity (재시도) | >= 2.31.0 / >= 8.2.0 |
| 스케줄러 | APScheduler | >= 3.10.0 |
| Python | CPython | >= 3.11 |
