"""CelebLife Instagram OAuth login UI.

Place this file at:
    src/ui/celeblife_login.py

Required assets:
    assets/login/celeblife_logo_purple.png
    assets/login/celeblife_instagram_illustration.png
"""

from __future__ import annotations

import base64
import html
import textwrap
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT_DIR / "assets" / "login"


def _data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"UI asset not found: {path}")

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    mime_type = mime_types.get(path.suffix.lower())
    if not mime_type:
        raise ValueError(f"Unsupported UI asset type: {path.suffix}")

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _compact_html(markup: str) -> str:
    """Remove Markdown-sensitive indentation and blank lines from raw HTML."""

    return "\n".join(
        line.strip()
        for line in textwrap.dedent(markup).splitlines()
        if line.strip()
    )


def render_login_page(
    oauth_url: str,
    *,
    back_url: str = "/",
    privacy_url: str = "/Privacy",
) -> None:
    """Render the full-screen CelebLife Instagram OAuth entry page."""

    logo_uri = _data_uri(ASSET_DIR / "celeblife_logo_purple.png")
    illustration_uri = _data_uri(
        ASSET_DIR / "celeblife_instagram_illustration.png"
    )

    safe_oauth_url = html.escape(oauth_url, quote=True)
    safe_back_url = html.escape(back_url, quote=True)
    safe_privacy_url = html.escape(privacy_url, quote=True)

    st.markdown(
        _compact_html(
            f"""
        <style>
          #MainMenu,
          footer,
          header[data-testid="stHeader"],
          [data-testid="stToolbar"],
          [data-testid="stSidebar"],
          [data-testid="collapsedControl"] {{
            display: none !important;
          }}

          html,
          body,
          .stApp,
          [data-testid="stAppViewContainer"] {{
            width: 100% !important;
            min-height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
          }}

          .block-container,
          [data-testid="stAppViewBlockContainer"] {{
            width: 100% !important;
            max-width: none !important;
            margin: 0 !important;
            padding: 0 !important;
          }}

          * {{
            box-sizing: border-box;
          }}

          .cl-login-page {{
            position: fixed;
            inset: 0;
            z-index: 9999;
            display: grid;
            grid-template-columns: 50% 50%;
            width: 100vw;
            min-height: 100dvh;
            overflow: auto;
            color: #17141c;
            background: #ffffff;
            font-family:
              Inter,
              "Noto Sans CJK KR",
              "Noto Sans KR",
              "Apple SD Gothic Neo",
              Arial,
              sans-serif;
            -webkit-font-smoothing: antialiased;
          }}

          .cl-visual-panel {{
            position: relative;
            min-height: 100dvh;
            overflow: hidden;
            background:
              radial-gradient(
                circle at 52% 50%,
                rgba(190, 167, 248, 0.16) 0,
                rgba(190, 167, 248, 0.06) 31%,
                transparent 58%
              ),
              linear-gradient(
                180deg,
                #faf8ff 0%,
                #f5f1fd 46%,
                #f0ebfc 100%
              );
            border-right: 1px solid rgba(108, 67, 201, 0.045);
          }}

          .cl-brand {{
            position: absolute;
            z-index: 4;
            top: clamp(34px, 5.35vh, 53px);
            left: clamp(38px, 5.05vw, 80px);
          }}

          .cl-brand img {{
            display: block;
            width: clamp(205px, 16.5vw, 262px);
            height: auto;
            object-fit: contain;
          }}

          .cl-hero {{
            position: absolute;
            z-index: 3;
            top: clamp(236px, 29vh, 288px);
            left: clamp(64px, 11.15vw, 177px);
          }}

          .cl-illustration {{
            display: block;
            width: clamp(360px, 29vw, 460px);
            height: auto;
            margin: 0 0 clamp(14px, 1.8vh, 18px);
            object-fit: contain;
            user-select: none;
          }}

          .cl-hero-title {{
            margin: 0;
            color: #14121a;
            font-size: clamp(42px, 3.55vw, 56px);
            line-height: 1.08;
            font-weight: 800;
            letter-spacing: -0.055em;
            word-break: keep-all;
          }}

          .cl-hero-copy {{
            margin: clamp(8px, 1.3vh, 13px) 0 0;
            color: #7f7889;
            font-size: clamp(16px, 1.25vw, 20px);
            line-height: 1.5;
            letter-spacing: -0.025em;
            word-break: keep-all;
          }}

          .cl-back-link {{
            position: absolute;
            z-index: 4;
            left: clamp(38px, 5.05vw, 80px);
            bottom: clamp(24px, 6.8vh, 68px);
            display: inline-flex;
            align-items: center;
            gap: 10px;
            color: #5f5373;
            font-size: 17px;
            font-weight: 600;
            text-decoration: none;
          }}

          .cl-form-panel {{
            display: flex;
            min-height: 100dvh;
            align-items: center;
            justify-content: flex-start;
            padding: 48px 52px 48px clamp(72px, 6.05vw, 96px);
            background:
              radial-gradient(
                circle at 72% 13%,
                rgba(190, 170, 245, 0.055),
                transparent 28%
              ),
              #ffffff;
          }}

          .cl-form-card {{
            width: min(100%, 512px);
            transform: translate(30px, 18px);
          }}

          .cl-form-title {{
            margin: 0;
            color: #15121b;
            font-size: clamp(27px, 1.93vw, 31px);
            line-height: 1.32;
            font-weight: 800;
            letter-spacing: -0.045em;
            word-break: keep-all;
          }}

          .cl-form-description {{
            margin: 24px 0 36px;
            color: #777180;
            font-size: 17px;
            line-height: 1.78;
            letter-spacing: -0.026em;
            word-break: keep-all;
          }}

          .cl-meta-badge {{
            display: inline-flex;
            min-height: 46px;
            align-items: center;
            gap: 9px;
            padding: 0 15px;
            border: 1px solid #e4dcf6;
            border-radius: 12px;
            color: #4f3978;
            background: #f5f1ff;
            font-size: 16px;
            font-weight: 700;
          }}

          .cl-meta-infinity {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-top: -2px;
            color: #1368e8;
            font-family: Arial, sans-serif;
            font-size: 30px;
            font-weight: 700;
            line-height: 1;
            letter-spacing: -0.12em;
          }}

          .cl-security-copy {{
            margin: 19px 0 38px;
            color: #746e7c;
            font-size: 16px;
            line-height: 1.75;
            letter-spacing: -0.025em;
            word-break: keep-all;
          }}

          .cl-instagram-button {{
            display: flex;
            width: 100%;
            min-height: 64px;
            align-items: center;
            justify-content: center;
            gap: 14px;
            padding: 0 22px;
            border: 1px solid #8d63e9;
            border-radius: 13px;
            color: #7546df;
            background: #ffffff;
            box-shadow: 0 12px 28px rgba(107, 65, 195, 0.075);
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.02em;
            text-decoration: none;
          }}

          .cl-instagram-button:hover {{
            border-color: #7546df;
            background: #fbf9ff;
          }}

          .cl-instagram-icon {{
            width: 29px;
            height: 29px;
            flex: 0 0 auto;
          }}

          .cl-privacy-link {{
            display: block;
            width: fit-content;
            margin: 28px auto 0;
            color: #7546df;
            font-size: 16px;
            font-weight: 650;
            text-decoration: none;
          }}

          @media (max-width: 1080px) {{
            .cl-login-page {{
              position: relative;
              grid-template-columns: 1fr;
            }}

            .cl-visual-panel {{
              min-height: 780px;
            }}

            .cl-brand {{
              top: 32px;
              left: 36px;
            }}

            .cl-hero {{
              top: 205px;
              left: 50%;
              width: min(90%, 600px);
              transform: translateX(-50%);
            }}

            .cl-illustration {{
              width: min(440px, 100%);
            }}

            .cl-back-link {{
              left: 36px;
              bottom: 32px;
            }}

            .cl-form-panel {{
              min-height: auto;
              justify-content: center;
              padding: 80px 28px 100px;
            }}

            .cl-form-card {{
              transform: none;
            }}
          }}

          @media (max-width: 620px) {{
            .cl-visual-panel {{
              min-height: 570px;
            }}

            .cl-brand {{
              top: 23px;
              left: 24px;
            }}

            .cl-brand img {{
              width: 183px;
            }}

            .cl-hero {{
              top: 150px;
              width: calc(100% - 48px);
            }}

            .cl-illustration {{
              width: 330px;
              margin: 0 auto 8px;
            }}

            .cl-hero-title {{
              font-size: 38px;
            }}

            .cl-hero-copy {{
              font-size: 16px;
            }}

            .cl-back-link {{
              left: 24px;
              bottom: 24px;
            }}

            .cl-form-panel {{
              padding: 60px 24px 80px;
            }}

            .cl-form-title {{
              font-size: 27px;
            }}

            .cl-form-description,
            .cl-security-copy {{
              font-size: 15px;
            }}
          }}
        </style>

        <main class="cl-login-page">
          <section class="cl-visual-panel">
            <div class="cl-brand">
              <img src="{logo_uri}" alt="CelebLife">
            </div>

            <div class="cl-hero">
              <img
                class="cl-illustration"
                src="{illustration_uri}"
                alt="인스타그램 계정과 CelebLife 연결"
              >
              <h1 class="cl-hero-title">인스타그램 로그인</h1>
              <p class="cl-hero-copy">
                CelebLife에 필요한 권한을 연결하세요
              </p>
            </div>

            <a class="cl-back-link" href="{safe_back_url}" target="_self">
              <span>←</span>
              <span>뒤로</span>
            </a>
          </section>

          <section class="cl-form-panel">
            <div class="cl-form-card">
              <h2 class="cl-form-title">
                인스타그램에 로그인하고<br>
                CelebLife에 필요한 권한을 허용해주세요
              </h2>

              <p class="cl-form-description">
                연결 후 인스타그램 계정 데이터를 바탕으로 인사이트를<br>
                분석할 수 있어요. 데이터는 항상 사용자가 직접 제어하며,<br>
                동의 없이 어떤 작업도 진행되지 않습니다.
              </p>

              <div class="cl-meta-badge">
                <span class="cl-meta-infinity">∞</span>
                <span>Meta 공식파트너</span>
              </div>

              <p class="cl-security-copy">
                이 연결은 Meta의 공식 API를 사용합니다.<br>
                인스타그램 비밀번호를 CelebLife에 직접 입력하지 않으며,<br>
                권한은 언제든 해제할 수 있습니다.
              </p>

              <a
                class="cl-instagram-button"
                href="{safe_oauth_url}"
                target="_blank"
                rel="noopener noreferrer"
              >
                <svg
                  class="cl-instagram-icon"
                  viewBox="0 0 32 32"
                  fill="none"
                  aria-hidden="true"
                >
                  <defs>
                    <linearGradient
                      id="clIgGradient"
                      x1="4"
                      y1="28"
                      x2="28"
                      y2="4"
                    >
                      <stop stop-color="#FFD36C"/>
                      <stop offset=".28" stop-color="#FF8A43"/>
                      <stop offset=".54" stop-color="#E84791"/>
                      <stop offset=".78" stop-color="#A74DE2"/>
                      <stop offset="1" stop-color="#6556E8"/>
                    </linearGradient>
                  </defs>
                  <rect
                    x="4.5"
                    y="4.5"
                    width="23"
                    height="23"
                    rx="7"
                    stroke="url(#clIgGradient)"
                    stroke-width="3"
                  />
                  <circle
                    cx="16"
                    cy="16"
                    r="5.3"
                    stroke="url(#clIgGradient)"
                    stroke-width="3"
                  />
                  <circle
                    cx="23.3"
                    cy="8.8"
                    r="1.8"
                    fill="url(#clIgGradient)"
                  />
                </svg>
                <span>인스타그램으로 계속하기</span>
              </a>

              <a
                class="cl-privacy-link"
                href="{safe_privacy_url}"
                target="_self"
              >
                개인정보 및 권한 안내
              </a>
            </div>
          </section>
        </main>
        """
        ),
        unsafe_allow_html=True,
    )
