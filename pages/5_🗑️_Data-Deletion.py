"""Data Deletion Instructions page."""

import streamlit as st
from src.config import config

st.set_page_config(page_title="Data Deletion", page_icon="🗑️", layout="centered")

st.title("🗑️ 데이터 삭제 안내 / Data Deletion Instructions")

st.markdown("---")

# Section 1: Remove App from Instagram
st.subheader("1. Instagram에서 앱 제거 / Remove App from Instagram")
st.markdown("""
다음 단계에 따라 Instagram 설정에서 본 앱의 접근 권한을 제거할 수 있습니다:

Follow these steps to remove this app's access from your Instagram Settings:

**단계별 안내 / Step-by-step Instructions:**

1. **Instagram에 로그인**합니다 / **Log in to Instagram**
   - [instagram.com](https://www.instagram.com)으로 이동합니다

2. **설정 페이지로 이동**합니다 / **Go to Settings**
   - 프로필 → 설정 및 활동 → 웹사이트 권한
   - Profile → Settings and activity → Website permissions

3. **앱 및 웹사이트 설정**으로 이동합니다 / **Navigate to Apps and Websites**
   - **앱 및 웹사이트** 클릭
   - Click **Apps and Websites**

4. **본 앱을 찾아 제거**합니다 / **Find and remove this app**
   - 활성 앱 목록에서 **urlinsta** (또는 본 앱 이름)를 찾습니다
   - Find **urlinsta** (or this app's name) in the Active apps list
   - **제거** 버튼을 클릭합니다 / Click the **Remove** button
   - 확인 대화상자에서 제거를 확인합니다 / Confirm removal in the dialog
""")

st.markdown("---")

# Section 2: Request Data Deletion
st.subheader("2. 데이터 삭제 요청 / Request Data Deletion")
st.markdown(f"""
앱을 제거한 후, 저장된 데이터의 완전한 삭제를 요청할 수 있습니다:

After removing the app, you can request complete deletion of your stored data:

- **이메일 / Email:** {config.CONTACT_EMAIL}
- **제목 / Subject:** "데이터 삭제 요청 / Data Deletion Request"
- **본문에 포함할 내용 / Include in body:**
  - 인스타그램 사용자명 / Your Instagram username
  - 요청 내용: 모든 데이터 삭제 / Request: Delete all my data
""")

st.markdown("---")

# Section 3: What Gets Deleted
st.subheader("3. 삭제되는 데이터 / What Gets Deleted")
st.markdown("""
삭제 요청 시 다음 데이터가 영구적으로 삭제됩니다:

The following data will be permanently deleted upon request:

- **계정 정보** / Account information
  - 인스타그램 비즈니스 계정 ID, 사용자명, 표시 이름 / Instagram Business Account ID, username, display name

- **저장된 인사이트 데이터** / Stored insights data
  - 조회수, 도달, 참여 계정, 총 상호작용 등 모든 수집된 지표 / All collected metrics (views, reach, accounts engaged, total interactions, etc.)

- **오디언스 인구통계 데이터** / Audience demographic data
  - 도시, 국가, 연령, 성별 분포 데이터 / City, country, age, gender distribution data

- **인증 토큰** / Authentication tokens
  - Instagram 액세스 토큰 / Instagram access token
""")

st.markdown("---")

# Section 4: Deletion Timeline
st.subheader("4. 삭제 처리 기간 / Deletion Timeline")
st.markdown("""
- **Instagram 앱 제거 시:** 본 앱의 접근 권한이 **즉시** 중단됩니다
  / **Upon app removal:** This app's access is revoked **immediately**

- **데이터 삭제 요청 시:** 요청일로부터 **30일 이내**에 모든 데이터가 영구 삭제됩니다
  / **Upon deletion request:** All data will be permanently deleted within **30 days** of the request

- **삭제 완료 후:** 이메일로 삭제 완료 확인을 발송합니다
  / **After deletion:** A confirmation email will be sent upon completion
""")

st.markdown("---")

# Section 5: Contact
st.subheader("5. 문의 / Contact")
st.markdown(f"""
데이터 삭제에 관한 질문이 있으시면:

For questions about data deletion:

- **이메일 / Email:** {config.CONTACT_EMAIL}
- **개인정보 처리방침:** [개인정보 처리방침 페이지](/Privacy)를 참고하세요
  / **Privacy Policy:** See our [Privacy Policy page](/Privacy)
""")
