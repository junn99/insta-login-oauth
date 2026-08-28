"""Build the static CelebLife login shell served at /Login.

The Python login UI remains the source of truth for brand assets, copy, base
styling, icons, and consent modal body formatting. This generator adapts that
source into a standalone document for Vercel's static /Login route.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "Login" / "index.html"

sys.path.insert(0, str(ROOT))

from src.consent import CONSENT_KEYS  # noqa: E402
from src.ui import celeblife_login as ui  # noqa: E402


ERROR_MESSAGES = {
    "access_denied": "권한 요청이 취소되었습니다.",
    "callback_failed": "로그인 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "configuration_error": "Preview 로그인 설정이 완료되지 않았습니다.",
    "consent_persistence_failed": "동의 내역을 저장하지 못했습니다. 다시 시도해 주세요.",
    "expired_state": "로그인 동의 시간이 만료되었습니다. 다시 진행해 주세요.",
    "invalid_state": "로그인 세션이 유효하지 않거나 만료되었습니다.",
    "missing_code": "인증 코드가 없습니다. 다시 시도해 주세요.",
}
DEFAULT_ERROR_MESSAGE = "로그인을 완료하지 못했습니다."


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _remove_css_block(css: str, selector_prefix: str) -> str:
    start = css.find(selector_prefix)
    if start == -1:
        return css
    brace = css.find("{", start)
    if brace == -1:
        return css

    depth = 0
    for index in range(brace, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[:start] + css[index + 1 :]
    return css


def _static_brand_styles() -> str:
    logo_uri = ui._data_uri(ui.ASSET_DIR / "celeblife_logo_purple.png")
    symbol_uri = ui._data_uri(ui.ASSET_DIR / "celeblife_symbol_purple.png")
    styles = ui._STYLE_TEMPLATE.substitute(
        logo_uri=logo_uri,
        symbol_uri=symbol_uri,
        logo_ratio=ui.LOGO_ASPECT_RATIO,
        font_stack=ui.FONT_STACK,
    )
    styles = _strip_css_comments(styles)
    styles = _remove_css_block(styles, "#MainMenu,")
    styles = _remove_css_block(styles, ".block-container,")
    styles = styles.replace(
        """
    html,
    body,
    .stApp,
    [data-testid=\"stAppViewContainer\"] {
      width: 100% !important;
      min-height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      background: #ffffff !important;
    }
""",
        """
    html,
    body {
      width: 100%;
      min-height: 100%;
      margin: 0;
      padding: 0;
      background: #ffffff;
      color: rgb(38, 39, 48);
    }
""",
    )
    styles = styles.replace(
        """
    .cl-login-page .cl-card-footer {
      margin-top: auto;
      padding-top: 16px;
    }
""",
        """
    .cl-login-page .cl-card-footer {
      margin-top: auto;
      padding-top: 14px;
    }
""",
    )
    return styles


def _static_consent_styles() -> str:
    return f"""
    <style>
    .cl-login-page[hidden],
    .cl-static-error-page[hidden] {{
      display: none !important;
    }}

    .cl-login-page.cl-consent-page {{
      position: relative;
      inset: auto;
      z-index: auto;
      display: block;
      min-height: 100vh;
      min-height: 100dvh;
      overflow: visible;
      background: #ffffff;
    }}

    .cl-consent-shell {{
      --cl-consent-gutter: 20px;
      --cl-consent-block-gap: 16px;
      --cl-consent-panel-bottom: 12px;
      width: min(100%, 560px);
      margin: 0 auto;
      padding:
        max(12px, env(safe-area-inset-top))
        var(--cl-consent-gutter)
        max(28px, env(safe-area-inset-bottom));
    }}

    .cl-consent-shell,
    .cl-consent-shell * {{
      box-sizing: border-box;
      font-family: {ui.FONT_STACK} !important;
    }}

    .cl-consent-back {{
      display: inline-flex;
      align-items: center;
      justify-content: flex-start;
      gap: 4px;
      min-height: 44px;
      margin: 0 0 4px;
      padding: 0 4px;
      border: 0;
      background: transparent;
      color: #514b5a;
      cursor: pointer;
      font-size: 16px;
      font-weight: 400;
      letter-spacing: 0;
      line-height: 1.6;
    }}

    .cl-consent-back svg {{
      width: 20px;
      height: 20px;
      flex: 0 0 auto;
    }}

    .cl-consent-back span {{
      font-size: 14px;
      font-weight: 400;
      line-height: 1.6;
    }}

    .cl-consent-page .cl-visual-panel {{
      display: none !important;
    }}

    .cl-consent-page .cl-form-panel {{
      width: min(100%, 560px);
      min-height: auto;
      margin: 0 auto;
      padding: max(20px, env(safe-area-inset-top)) 0 var(--cl-consent-panel-bottom);
    }}

    .cl-consent-page .cl-form-card {{
      max-width: none;
      min-height: auto;
      padding: 0;
      box-shadow: none;
    }}

    .cl-login-page.cl-consent-page .cl-form-card .cl-brand-mark {{
      display: block;
    }}

    .cl-consent-page .cl-consent-copy {{
      margin-top: 22px;
    }}

    .cl-consent-page .cl-form-title {{
      line-height: 1.4;
    }}

    .cl-consent-page .cl-lead {{
      margin-top: var(--cl-consent-block-gap);
      line-height: 1.8;
    }}

    .cl-consent-form {{
      display: grid;
      gap: 0;
      margin-top: 4px;
    }}

    .cl-consent-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: start;
      min-height: 48px;
      margin: 0;
    }}

    .cl-consent-row--single {{
      grid-template-columns: minmax(0, 1fr);
    }}

    .cl-consent-label {{
      display: flex;
      align-items: flex-start;
      min-height: 48px;
      gap: 12px;
      color: #17131f;
      cursor: pointer;
      font-size: 14px;
      font-weight: 400;
      letter-spacing: 0;
      line-height: 1.54;
      word-break: keep-all;
    }}

    .cl-consent-label input {{
      appearance: none;
      width: 13px;
      height: 13px;
      flex: 0 0 auto;
      margin: 4px 0 0 -1px;
      border: 1px solid #c9b6f4;
      border-radius: 2px;
      background: #ffffff;
      accent-color: #7d4fde;
    }}

    .cl-consent-label input:checked {{
      background:
        linear-gradient(45deg, transparent 58%, #ffffff 58% 72%, transparent 72%),
        linear-gradient(-45deg, transparent 50%, #ffffff 50% 64%, transparent 64%),
        #7d4fde;
      border-color: #7d4fde;
    }}

    .cl-consent-detail-link {{
      display: inline-flex;
      align-items: flex-start;
      justify-content: flex-end;
      min-height: 44px;
      padding: 0;
      color: #7d4fde;
      font-size: 14px;
      font-weight: 700;
      line-height: 1.52;
      text-decoration: none;
      white-space: nowrap;
    }}

    .cl-consent-submit {{
      position: relative;
      display: flex;
      width: 100%;
      min-height: 60px;
      align-items: center;
      justify-content: center;
      margin-top: 16px;
      padding: 4px 12px;
      border: 1px solid #7d4fde;
      border-radius: 12px;
      background: #7d4fde;
      box-shadow: 0 14px 28px rgba(125, 79, 222, 0.24);
      color: #ffffff;
      cursor: pointer;
      font-size: 15px;
      font-weight: 680;
      letter-spacing: -0.02em;
      line-height: 1.6;
      transition:
        transform 160ms ease,
        box-shadow 160ms ease,
        border-color 160ms ease,
        background 160ms ease;
    }}

    .cl-consent-submit:disabled {{
      border-color: rgba(125, 79, 222, 0.16);
      background: rgba(125, 79, 222, 0.1);
      box-shadow: none;
      color: rgba(80, 62, 117, 0.62);
      cursor: not-allowed;
      transform: none;
    }}

    .cl-static-error-page {{
      position: relative;
      min-height: 100vh;
      min-height: 100dvh;
      padding: 96px 16px 160px;
      background: #ffffff;
      color: rgb(38, 39, 48);
      font-family: {ui.FONT_STACK} !important;
    }}

    .cl-static-error-page,
    .cl-static-error-page * {{
      box-sizing: border-box;
      font-family: {ui.FONT_STACK} !important;
    }}

    .cl-static-chrome-button {{
      position: absolute;
      display: inline-flex;
      width: 28px;
      height: 28px;
      align-items: center;
      justify-content: center;
      border: 0;
      background: transparent;
      color: rgb(38, 39, 48);
      padding: 0;
    }}

    .cl-static-chrome-button svg {{
      width: 20px;
      height: 20px;
    }}

    .cl-static-chrome-button--left {{
      top: 16px;
      left: 18px;
    }}

    .cl-static-chrome-button--right {{
      top: 15.5px;
      right: 18px;
    }}

    .cl-static-error-title {{
      margin: 0;
      padding: 20px 0 16px;
      color: rgb(38, 39, 48);
      font-size: 44px;
      font-weight: 700;
      line-height: 1.2;
    }}

    .cl-static-error-alert {{
      min-height: 56px;
      margin: 0;
      padding: 16px;
      border-radius: 8px;
      background: rgba(255, 43, 43, 0.1);
      color: #bd4043;
      font-size: 16px;
      font-weight: 400;
      line-height: 1.5;
    }}

    .cl-static-error-retry {{
      display: flex;
      width: 100%;
      min-height: 40px;
      align-items: center;
      justify-content: center;
      margin-top: 16px;
      padding: 4px 12px;
      border: 1px solid rgba(38, 39, 48, 0.2);
      border-radius: 8px;
      background: #ffffff;
      color: rgb(38, 39, 48);
      font-size: 14px;
      font-weight: 400;
      line-height: 1.6;
      text-align: center;
      text-decoration: none;
    }}

    @media (min-width: 961px) {{
      .cl-static-error-page {{
        padding-right: 80px;
        padding-left: 80px;
      }}
    }}

    .cl-policy-modal,
    .cl-policy-modal * {{
      box-sizing: border-box;
      font-family: {ui.FONT_STACK} !important;
    }}

    .cl-policy-modal {{
      position: fixed;
      inset: 0;
      z-index: 9999;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 24px 18px;
    }}

    .cl-policy-modal:target {{
      display: flex;
    }}

    .cl-policy-modal__backdrop {{
      position: absolute;
      inset: 0;
      background: rgba(22, 18, 32, 0.46);
      backdrop-filter: blur(3px);
    }}

    .cl-policy-modal__panel {{
      position: relative;
      display: flex;
      width: min(100%, 640px);
      max-height: min(82dvh, 760px);
      flex-direction: column;
      overflow: hidden;
      padding: 0;
      border: 1px solid rgba(124, 79, 222, 0.16);
      border-radius: 20px;
      background: #ffffff;
      box-shadow: 0 22px 70px rgba(33, 26, 51, 0.2);
    }}

    .cl-policy-modal__header {{
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      flex: 0 0 auto;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 22px 16px;
      border-bottom: 1px solid rgba(124, 79, 222, 0.1);
      background: rgba(255, 255, 255, 0.98);
    }}

    .cl-policy-modal__eyebrow {{
      margin: 0 0 4px;
      color: #7d4fde;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.1em;
      line-height: 1.35;
    }}

    .cl-policy-modal__title {{
      margin: 0;
      color: #171321;
      font-size: 20px;
      font-weight: 800;
      line-height: 1.42;
    }}

    .cl-policy-modal__close-icon {{
      display: inline-flex;
      flex: 0 0 auto;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border-radius: 999px;
      background: #f7f3ff;
      color: #514b5a;
      font-size: 26px;
      line-height: 1;
      text-decoration: none;
    }}

    .cl-policy-modal__close-icon:focus-visible,
    .cl-policy-modal__close-button:focus-visible {{
      outline: 3px solid rgba(125, 79, 222, 0.28);
      outline-offset: 2px;
    }}

    .cl-policy-modal__body {{
      flex: 1 1 auto;
      min-height: 0;
      margin: 0;
      overflow-y: auto;
      padding: 18px 22px 20px;
      color: #514b5a;
      font-size: 14.5px;
      line-height: 1.72;
      word-break: keep-all;
      overscroll-behavior: contain;
    }}

    .cl-policy-modal__document-title {{
      margin: 0;
      color: #171321;
      font-size: 18px;
      font-weight: 800;
      line-height: 1.42;
    }}

    .cl-policy-modal__metadata {{
      margin: 6px 0 0;
      color: #7d7286;
      font-size: 12.5px;
      font-weight: 620;
      line-height: 1.5;
    }}

    .cl-policy-modal__document-subtitle {{
      margin: 8px 0 0;
      color: #5b5369;
      font-size: 14px;
      font-weight: 560;
      line-height: 1.6;
    }}

    .cl-policy-modal__metadata-row {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-top: 8px;
      padding: 9px 11px;
      border: 1px solid rgba(125, 79, 222, 0.1);
      border-radius: 12px;
      background: #fbfaff;
    }}

    .cl-policy-modal__metadata-row span {{
      color: #7d7286;
      font-weight: 700;
    }}

    .cl-policy-modal__metadata-row strong {{
      color: #2a2335;
      font-weight: 760;
      text-align: right;
    }}

    .cl-policy-modal__intro {{
      display: grid;
      gap: 8px;
      margin-top: 14px;
      padding: 14px;
      border: 1px solid rgba(125, 79, 222, 0.14);
      border-radius: 14px;
      background: #faf8ff;
    }}

    .cl-policy-modal__intro p {{
      margin: 0;
      color: #453d52;
      font-size: 14.5px;
      line-height: 1.72;
    }}

    .cl-policy-modal__section {{
      margin-top: 22px;
    }}

    .cl-policy-modal__section-heading {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin: 0 0 10px;
      color: #201a2d;
      font-size: 15px;
      font-weight: 780;
      line-height: 1.45;
    }}

    .cl-policy-modal__section-number {{
      display: inline-flex;
      min-width: 24px;
      height: 24px;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: rgba(125, 79, 222, 0.1);
      color: #7d4fde;
      font-size: 12px;
      font-weight: 850;
      line-height: 1;
    }}

    .cl-policy-modal__subheading {{
      margin: 14px 0 6px;
      color: #2a2335;
      font-size: 14px;
      font-weight: 740;
      line-height: 1.45;
    }}

    .cl-policy-modal__list,
    .cl-policy-modal__table-list {{
      display: grid;
      gap: 8px;
      margin: 8px 0 0;
      padding: 0;
      list-style: none;
    }}

    .cl-policy-modal__list-row {{
      position: relative;
      margin: 0;
      padding: 0 0 0 24px;
      color: #514b5a;
      font-size: 14px;
      line-height: 1.58;
      overflow-wrap: anywhere;
    }}

    .cl-policy-modal__list-row::before {{
      position: absolute;
      top: 0.72em;
      left: 7px;
      width: 5px;
      height: 5px;
      border-radius: 999px;
      background: #9b7cec;
      content: "";
    }}

    .cl-policy-modal__summary-grid {{
      display: grid;
      gap: 10px;
      margin-top: 12px;
    }}

    .cl-policy-modal__summary-card {{
      padding: 12px 13px;
      border: 1px solid rgba(125, 79, 222, 0.12);
      border-radius: 14px;
      background: linear-gradient(180deg, #ffffff 0%, #faf8ff 100%);
    }}

    .cl-policy-modal__summary-label {{
      margin: 0;
      color: #7d4fde;
      font-size: 12.5px;
      font-weight: 820;
      line-height: 1.4;
    }}

    .cl-policy-modal__summary-description {{
      margin: 5px 0 0;
      color: #443d50;
      font-size: 14px;
      line-height: 1.58;
    }}

    .cl-policy-modal__note {{
      margin: 12px 0 0;
      padding: 11px 12px;
      border-left: 3px solid #9b7cec;
      border-radius: 12px;
      background: #fbfaff;
      color: #5b5369;
      font-size: 13.5px;
      line-height: 1.64;
    }}

    .cl-policy-modal__table-row {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border: 1px solid rgba(43, 34, 63, 0.1);
      border-radius: 14px;
      background: #ffffff;
    }}

    .cl-policy-modal__table-cell {{
      display: grid;
      grid-template-columns: 64px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
    }}

    .cl-policy-modal__table-label {{
      color: #83798f;
      font-size: 12px;
      font-weight: 780;
      line-height: 1.5;
    }}

    .cl-policy-modal__table-value {{
      color: #342d3f;
      font-size: 13.5px;
      line-height: 1.58;
      overflow-wrap: anywhere;
    }}

    .cl-policy-modal__status-badge {{
      display: inline-flex;
      width: fit-content;
      min-height: 24px;
      align-items: center;
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(125, 79, 222, 0.1);
      color: #6e3ed2;
      font-size: 12px;
      font-weight: 820;
      line-height: 1.4;
    }}

    .cl-policy-modal__paragraph {{
      margin: 8px 0 0;
      font-size: 14.5px;
      line-height: 1.72;
    }}

    .cl-policy-modal__paragraph:last-child {{
      margin-bottom: 0;
    }}

    .cl-policy-modal__footer {{
      display: flex;
      flex: 0 0 auto;
      padding: 14px 22px 18px;
      border-top: 1px solid rgba(124, 79, 222, 0.1);
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 -12px 30px rgba(33, 26, 51, 0.06);
    }}

    .cl-policy-modal__close-button {{
      display: flex;
      width: 100%;
      min-height: 48px;
      align-items: center;
      justify-content: center;
      border-radius: 14px;
      background: #7d4fde;
      color: #ffffff;
      font-weight: 800;
      text-decoration: none;
    }}

    @media (hover: hover) {{
      .cl-consent-submit:not(:disabled):hover {{
        border-color: #6e3ed2;
        background: #6e3ed2;
        box-shadow: 0 16px 32px rgba(125, 79, 222, 0.3);
        transform: translateY(-1px);
      }}
    }}

    @media (max-width: 420px) {{
      .cl-consent-shell {{
        --cl-consent-gutter: 18px;
        padding-top: max(28px, env(safe-area-inset-top));
        padding-left: var(--cl-consent-gutter);
        padding-right: var(--cl-consent-gutter);
      }}

      .cl-consent-page .cl-form-panel {{
        padding: max(18px, env(safe-area-inset-top)) 0 var(--cl-consent-panel-bottom);
      }}

      .cl-consent-page .cl-form-title {{
        font-size: 25px;
        line-height: 1.42;
      }}

      .cl-consent-page .cl-lead {{
        font-size: 14.5px;
        line-height: 1.86;
      }}

      .cl-consent-label {{
        line-height: 1.54;
      }}

      .cl-consent-detail-link {{
        font-size: 13.5px;
      }}

      .cl-policy-modal {{
        align-items: flex-end;
        padding: 10px 10px max(10px, env(safe-area-inset-bottom));
      }}

      .cl-policy-modal__panel {{
        width: 100%;
        max-height: 86dvh;
        border-radius: 20px 20px 16px 16px;
      }}

      .cl-policy-modal__panel::before {{
        display: block;
        width: 38px;
        height: 4px;
        flex: 0 0 auto;
        margin: 8px auto 0;
        border-radius: 999px;
        background: rgba(45, 35, 66, 0.18);
        content: "";
      }}

      .cl-policy-modal__header {{
        padding: 12px 18px 14px;
      }}

      .cl-policy-modal__title {{
        font-size: 19px;
        line-height: 1.42;
      }}

      .cl-policy-modal__body {{
        padding: 16px 18px 18px;
        font-size: 14.5px;
        line-height: 1.72;
      }}

      .cl-policy-modal__footer {{
        padding: 12px 18px max(16px, env(safe-area-inset-bottom));
      }}

      .cl-policy-modal__close-button {{
        min-height: 52px;
      }}
    }}
    </style>
    """


def _static_styles() -> str:
    return _static_brand_styles() + _static_consent_styles()


def _intro() -> str:
    return f"""
    <main class="cl-login-page" data-view="intro">
      <section class="cl-visual-panel" aria-labelledby="cl-story-title">
        <div class="cl-story-inner">
          <div class="cl-brand-mark" role="img" aria-label="CelebLife"></div>
          <div class="cl-story-content">
            <div class="cl-connection-visual" aria-hidden="true">
              <div class="cl-halo"></div>
              <div class="cl-orbit cl-orbit-one"></div>
              <div class="cl-orbit cl-orbit-two"></div>
              <div class="cl-ig-tile">
                {ui._instagram_icon(82)}
                <span class="cl-tile-shine"></span>
              </div>
              <div class="cl-symbol-card"></div>
              <div class="cl-data-chip">
                <span class="cl-data-dot"></span>
                채널 데이터 연결
              </div>
              {ui._sparkle("cl-sparkle-one")}
              {ui._sparkle("cl-sparkle-two")}
            </div>
            <div class="cl-story-copy">
              <p class="cl-eyebrow">CELEBLIFE ONBOARDING</p>
              <p class="cl-story-title" id="cl-story-title" role="heading" aria-level="2">인스타그램을 연결해 주세요</p>
              <p class="cl-story-lead">
                채널 데이터를 바탕으로 셀럽님에게 꼭 맞는 판매 전략을 설계합니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section class="cl-form-panel" aria-labelledby="cl-form-title">
        <div class="cl-form-card">
          <div class="cl-brand-mark" role="img" aria-label="CelebLife"></div>

          <div class="cl-mobile-visual" aria-hidden="true">
            <div class="cl-ig-mini">{ui._instagram_icon(48)}</div>
            <span class="cl-link-line"></span>
            <div class="cl-symbol-mini"></div>
          </div>

          <div>
            <p class="cl-eyebrow">CELEBLIFE ONBOARDING</p>
            <p class="cl-form-title cl-hook-title" id="cl-form-title" role="heading" aria-level="1">
              <span class="cl-hook-line">반응을 읽고,</span>
              <span class="cl-hook-line">선택의 기준을 만듭니다.</span>
            </p>
            <p class="cl-lead">
              채널 데이터를 분석해 맞는 제품과 판매 방향을 제안합니다.
            </p>
          </div>

          <div class="cl-trust-block">
            <div class="cl-trust-badge">
              {ui._shield_icon()}
              <strong>Meta 공식 로그인 방식</strong>
              <span>안전한 연결</span>
            </div>
            <p class="cl-trust-copy">
              인스타그램 비밀번호는 셀럽라이프에 공유되거나 저장되지 않습니다.
              연결 권한은 언제든 직접 해제할 수 있어요.
            </p>
          </div>

          <div class="cl-actions">
            <a class="cl-instagram-button" href="/Login?step=consent" target="_self" data-action="show-consent">
              <span class="cl-instagram-icon">{ui._instagram_icon(21)}</span>
              <span>Instagram으로 계속하기</span>
              <svg aria-hidden="true" class="cl-button-arrow" viewBox="0 0 20 20" fill="none">
                <path d="m7.5 4.5 5 5.5-5 5.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </a>
          </div>

          <div class="cl-card-footer">
            <div class="cl-security-note">
              {ui._shield_icon()}
              <span>로그인 정보는 셀럽라이프에 저장되지 않아요.</span>
            </div>
          </div>
        </div>
      </section>
    </main>
    """


def _consent_rows() -> str:
    rows = [
        """
        <label class="cl-consent-label">
          <input type="checkbox" id="cl-consent-all" />
          <span>필수 항목에 모두 동의합니다.</span>
        </label>
        """
    ]
    visible_keys = {item.key for item in ui.CONSENT_ITEMS}

    for item in ui.CONSENT_ITEMS:
        safe_label = html.escape(item.label)
        detail = (
            f'<a class="cl-consent-detail-link" href="#{ui._consent_modal_id(item.key)}" '
            f'id="{ui._consent_trigger_id(item.key)}" role="button" aria-haspopup="dialog" '
            f'aria-controls="{ui._consent_modal_id(item.key)}">'
            "상세 보기</a>"
            if item.key in ui._CONSENT_DETAIL_KEYS
            else ""
        )
        row_class = "cl-consent-row" if detail else "cl-consent-row cl-consent-row--single"
        rows.append(
            f"""
            <div class="{row_class}">
              <label class="cl-consent-label">
                <input type="checkbox" name="{html.escape(item.key, quote=True)}" value="true" data-required="true" />
                <span>{safe_label}</span>
              </label>
              {detail}
            </div>
            """
        )

    for key in CONSENT_KEYS:
        if key not in visible_keys:
            rows.append(
                f'<input type="hidden" name="{html.escape(key, quote=True)}" value="true" data-static-consent="true" />'
            )
    return "\n".join(rows)


def _consent() -> str:
    return f"""
    <main class="cl-login-page cl-consent-page" data-view="consent" hidden>
      <div class="cl-consent-shell">
        <button class="cl-consent-back" type="button" data-action="show-intro" aria-label="이전으로">
          <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
            <path d="M15 6 9 12l6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>이전으로</span>
        </button>

        <section class="cl-form-panel" aria-labelledby="cl-consent-title">
          <div class="cl-form-card">
            <div class="cl-brand-mark" role="img" aria-label="CelebLife"></div>
            <div class="cl-consent-copy">
              <p class="cl-form-title" id="cl-consent-title" role="heading" aria-level="1">
                연결 전 동의가 필요해요
              </p>
              <p class="cl-lead">
                필수 동의를 확인한 뒤 Instagram 연결을 진행합니다.
              </p>
            </div>
          </div>
        </section>

        <form class="cl-consent-form" action="/auth/instagram/start" method="post" data-consent-form>
          {_consent_rows()}
          <button class="cl-consent-submit" type="submit" disabled>동의하고 Instagram으로 계속하기</button>
        </form>
      </div>
      {ui._consent_detail_modals()}
    </main>
    """


def _chrome_icon_collapsed_sidebar() -> str:
    return """
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="m7 6 5 6-5 6" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round"/>
      <path d="m12 6 5 6-5 6" stroke="currentColor" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """


def _chrome_icon_more() -> str:
    return """
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="5.5" r="1.7"/>
      <circle cx="12" cy="12" r="1.7"/>
      <circle cx="12" cy="18.5" r="1.7"/>
    </svg>
    """


def _static_error() -> str:
    return f"""
    <main class="cl-static-error-page" data-view="error" hidden>
      <button class="cl-static-chrome-button cl-static-chrome-button--left" type="button" aria-label="사이드바 펼치기">
        {_chrome_icon_collapsed_sidebar()}
      </button>
      <button class="cl-static-chrome-button cl-static-chrome-button--right" type="button" aria-label="더보기">
        {_chrome_icon_more()}
      </button>
      <h1 class="cl-static-error-title">🔐 인스타그램 로그인</h1>
      <p class="cl-static-error-alert" data-error-message role="alert"></p>
      <a class="cl-static-error-retry" href="/Login?step=consent">다시 동의하고 연결하기</a>
    </main>
    """


def _script() -> str:
    error_map = json.dumps(ERROR_MESSAGES, ensure_ascii=False)
    default_error = json.dumps(DEFAULT_ERROR_MESSAGE, ensure_ascii=False)
    return f"""
    <script>
    (() => {{
      const ERROR_MESSAGES = {error_map};
      const DEFAULT_ERROR_MESSAGE = {default_error};
      const intro = document.querySelector('[data-view="intro"]');
      const consent = document.querySelector('[data-view="consent"]');
      const errorView = document.querySelector('[data-view="error"]');
      const errorMessage = document.querySelector('[data-error-message]');
      const form = document.querySelector('[data-consent-form]');
      const all = document.querySelector('#cl-consent-all');
      const required = Array.from(document.querySelectorAll('input[data-required="true"]'));
      const submit = document.querySelector('.cl-consent-submit');
      let currentStep = null;

      function syncSubmit() {{
        const ok = required.every((box) => box.checked);
        submit.disabled = !ok;
        all.checked = ok;
      }}

      function authErrorCode() {{
        const params = new URLSearchParams(location.search);
        return params.has('auth_error') ? params.get('auth_error') : null;
      }}

      function showError(code) {{
        intro.hidden = true;
        consent.hidden = true;
        errorView.hidden = false;
        errorMessage.textContent = ERROR_MESSAGES[code] || DEFAULT_ERROR_MESSAGE;
      }}

      function updateErrorView() {{
        const code = authErrorCode();
        if (code !== null) {{
          showError(code);
          return true;
        }}
        errorView.hidden = true;
        errorMessage.textContent = '';
        return false;
      }}

      function show(step, replace = false, clearQuery = false) {{
        if (updateErrorView()) return;
        if (currentStep === step && !replace) return;
        currentStep = step;
        const isConsent = step === 'consent';
        intro.hidden = isConsent;
        consent.hidden = !isConsent;
        errorView.hidden = true;
        const params = clearQuery ? new URLSearchParams() : new URLSearchParams(location.search);
        if (isConsent) {{
          params.set('step', 'consent');
        }} else {{
          params.delete('step');
        }}
        const query = params.toString();
        const url = query ? `/Login?${{query}}` : '/Login';
        history[replace ? 'replaceState' : 'pushState']({{ step }}, '', url);
      }}

      document.addEventListener('click', (event) => {{
        const trigger = event.target.closest('[data-action]');
        if (!trigger) return;
        event.preventDefault();
        const action = trigger.dataset.action;
        show(action === 'show-consent' ? 'consent' : 'intro', false, action === 'show-intro');
      }});

      all.addEventListener('change', () => {{
        required.forEach((box) => {{ box.checked = all.checked; }});
        syncSubmit();
      }});

      required.forEach((box) => box.addEventListener('change', syncSubmit));

      form.addEventListener('submit', () => {{
        submit.disabled = true;
        submit.setAttribute('aria-busy', 'true');
      }});

      window.addEventListener('popstate', () => {{
        if (updateErrorView()) return;
        const step = new URLSearchParams(location.search).get('step');
        const isConsent = step === 'consent';
        currentStep = isConsent ? 'consent' : 'intro';
        intro.hidden = isConsent;
        consent.hidden = !isConsent;
        errorView.hidden = true;
      }});

      const errorCode = authErrorCode();
      if (errorCode !== null) {{
        showError(errorCode);
        syncSubmit();
        return;
      }}
      const step = new URLSearchParams(location.search).get('step');
      show(step === 'consent' ? 'consent' : 'intro', true);
      syncSubmit();
    }})();
    </script>
    """


def build() -> str:
    return ui._compact_html(
        f"""
        <!doctype html>
        <html lang="ko">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <meta name="robots" content="noindex, nofollow" />
            <title>CelebLife Instagram Login</title>
            {_static_styles()}
          </head>
          <body data-celeblife-static-login="true">
            {_intro()}
            {_consent()}
            {_static_error()}
            {_script()}
          </body>
        </html>
        """
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
