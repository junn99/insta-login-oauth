"""CelebLife Instagram OAuth login UI.

Mobile-first: the base stylesheet targets a 360px-wide phone and the desktop
split layout is layered on at >=961px. See
``celeblife_instagram_onboarding_ui/DESIGN_SYSTEM.md`` for the brand tokens.

Every component selector is scoped under ``.cl-login-page`` on purpose. The
Streamlit theme styles markdown ``h1``-``h6``/``a`` through emotion classes
(``.st-emotion-cache-xxxx h1``), which outranks a bare single-class selector --
including ``font-family: "Source Sans"``, a face with no Korean glyphs. The
two-class scoping wins deterministically regardless of stylesheet order.

Place this file at:
    src/ui/celeblife_login.py

Required assets:
    assets/login/celeblife_logo_purple.png
    assets/login/celeblife_symbol_purple.png
"""

from __future__ import annotations

import base64
import html
import textwrap
from pathlib import Path
from string import Template

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT_DIR / "assets" / "login"

# Intrinsic size of celeblife_logo_purple.png, used for aspect-ratio so the
# logo can be drawn as a background image (inlined once) instead of two <img>.
LOGO_ASPECT_RATIO = "2047 / 499"

FONT_STACK = (
    '"Pretendard Variable", Pretendard, Inter, "Noto Sans CJK KR", '
    '"Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif'
)


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


def _instagram_icon(size: int) -> str:
    """Outline Instagram glyph. Uses currentColor, so it is safe to repeat."""

    return f"""
    <svg
      aria-hidden="true"
      class="cl-ig-glyph"
      width="{size}"
      height="{size}"
      viewBox="0 0 24 24"
      fill="none"
    >
      <rect x="3.25" y="3.25" width="17.5" height="17.5" rx="5.2"
        stroke="currentColor" stroke-width="1.8"/>
      <circle cx="12" cy="12" r="4.05" stroke="currentColor" stroke-width="1.8"/>
      <circle cx="17.45" cy="6.65" r="1.15" fill="currentColor"/>
    </svg>
    """


def _shield_icon() -> str:
    return """
    <svg aria-hidden="true" class="cl-shield" viewBox="0 0 24 24" fill="none">
      <path d="M12 3.1 19 6v5.45c0 4.24-2.7 7.87-7 9.45-4.3-1.58-7-5.21-7-9.45V6l7-2.9Z"
        stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>
      <path d="m8.8 12.05 2.05 2.05 4.5-4.6" stroke="currentColor"
        stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """


def _sparkle(modifier: str) -> str:
    return f"""
    <svg aria-hidden="true" class="cl-sparkle {modifier}" viewBox="0 0 42 42" fill="none">
      <path d="M21 1.5c1.35 11.87 7.63 18.15 19.5 19.5C28.63 22.35 22.35 28.63 21 40.5
        19.65 28.63 13.37 22.35 1.5 21 13.37 19.65 19.65 13.37 21 1.5Z" fill="currentColor"/>
    </svg>
    """


def _back_arrow() -> str:
    return """
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <path d="M16 10H4m0 0 5-5m-5 5 5 5" stroke="currentColor"
        stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    """


# CSS is kept out of the f-string so that braces need no escaping.
# string.Template only reacts to "$", which never appears in CSS.
_STYLE_TEMPLATE = Template(
    """
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css");

    #MainMenu,
    footer,
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
      display: none !important;
    }

    html,
    body,
    .stApp,
    [data-testid="stAppViewContainer"] {
      width: 100% !important;
      min-height: 100% !important;
      margin: 0 !important;
      padding: 0 !important;
      background: #ffffff !important;
    }

    .block-container,
    [data-testid="stAppViewBlockContainer"] {
      width: 100% !important;
      max-width: none !important;
      margin: 0 !important;
      padding: 0 !important;
    }

    /* ---------------------------------------------------------------
       Base = mobile (360px). Desktop is layered on at >=961px below.
       --------------------------------------------------------------- */

    .cl-login-page {
      --cl-purple: #7d4fde;
      --cl-purple-strong: #6e3ed2;
      --cl-purple-soft: #faf8ff;
      --cl-ink: #17131f;
      --cl-gray-600: #77717f;
      --cl-gray-500: #918b99;
      --cl-line: #e8e4ed;
      --cl-logo: url("$logo_uri");
      --cl-symbol: url("$symbol_uri");

      position: relative;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      min-height: 100dvh;
      color: var(--cl-ink);
      background:
        radial-gradient(circle at 50% 18%, rgba(125, 79, 222, 0.08), transparent 26%),
        #ffffff;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }

    /* Streamlit's theme sets font-family on markdown headings via emotion
       classes. "Source Sans" carries no Korean glyphs, so inheriting it turns
       the headline into tofu boxes. Force the brand stack across the subtree. */
    .cl-login-page,
    .cl-login-page * {
      font-family: $font_stack !important;
    }

    .cl-login-page *,
    .cl-login-page *::before,
    .cl-login-page *::after {
      box-sizing: border-box;
    }

    /* Strip the padding and underline Streamlit adds to markdown headings and
       links. Sizes, weights and margins are set per component below. */
    .cl-login-page h1,
    .cl-login-page h2,
    .cl-login-page p,
    .cl-login-page a {
      padding: 0 !important;
      text-decoration: none !important;
    }

    .cl-login-page a {
      -webkit-tap-highlight-color: transparent;
    }

    /* Story panel is desktop-only; it is not rendered at all on phones. */
    .cl-login-page .cl-visual-panel {
      display: none;
    }

    .cl-login-page .cl-form-panel {
      display: flex;
      flex: 1;
    }

    .cl-login-page .cl-form-card {
      display: flex;
      flex: 1;
      flex-direction: column;
      width: 100%;
      margin: 0 auto;
      padding:
        max(24px, env(safe-area-inset-top))
        max(20px, env(safe-area-inset-right))
        max(24px, env(safe-area-inset-bottom))
        max(20px, env(safe-area-inset-left));
    }

    .cl-login-page .cl-brand-mark {
      background-image: var(--cl-logo);
      background-repeat: no-repeat;
      background-position: left center;
      background-size: contain;
    }

    .cl-login-page .cl-form-card .cl-brand-mark {
      width: 132px;
      aspect-ratio: $logo_ratio;
    }

    /* --- compact connect graphic (mobile) --- */

    .cl-login-page .cl-mobile-visual {
      position: relative;
      display: flex;
      height: 112px;
      align-items: center;
      justify-content: center;
      margin-top: 14px;
    }

    .cl-login-page .cl-ig-mini,
    .cl-login-page .cl-symbol-mini {
      position: relative;
      z-index: 2;
      display: grid;
      place-items: center;
      background: #ffffff;
      box-shadow: 0 15px 32px rgba(77, 45, 137, 0.16);
    }

    .cl-login-page .cl-ig-mini {
      width: 80px;
      height: 80px;
      border: 6px solid rgba(255, 255, 255, 0.9);
      border-radius: 25px;
      background:
        radial-gradient(circle at 72% 76%, #ffc766 0 14%, transparent 37%),
        linear-gradient(145deg, #7d4fde 4%, #c53b9b 51%, #ed6b5d 77%, #f3ac48);
      color: #ffffff;
      transform: rotate(-5deg);
    }

    .cl-login-page .cl-symbol-mini {
      width: 58px;
      height: 58px;
      margin-left: 34px;
      border: 1px solid rgba(125, 79, 222, 0.12);
      border-radius: 19px;
    }

    .cl-login-page .cl-symbol-mini::before {
      width: 37px;
      height: 37px;
      background-image: var(--cl-symbol);
      background-repeat: no-repeat;
      background-position: center;
      background-size: contain;
      content: "";
    }

    .cl-login-page .cl-link-line {
      position: absolute;
      top: 56px;
      left: 50%;
      width: 58px;
      border-top: 2px dashed rgba(125, 79, 222, 0.3);
      transform: translateX(-50%);
    }

    /* --- copy --- */

    .cl-login-page .cl-eyebrow {
      margin: 15px 0 10px;
      color: var(--cl-purple);
      font-size: 11px;
      font-weight: 750;
      letter-spacing: 0.12em;
      line-height: 1.4;
    }

    .cl-login-page .cl-form-title {
      margin: 0;
      color: var(--cl-ink);
      font-size: clamp(27px, 7.2vw, 34px);
      font-weight: 760;
      letter-spacing: -0.045em;
      line-height: 1.28;
      text-wrap: balance;
      word-break: keep-all;
    }

    .cl-login-page .cl-lead {
      margin: 14px 0 0;
      color: var(--cl-gray-600);
      font-size: 14.5px;
      font-weight: 420;
      letter-spacing: -0.022em;
      line-height: 1.58;
      word-break: keep-all;
    }

    /* --- trust --- */

    .cl-login-page .cl-trust-block {
      margin-top: 22px;
    }

    .cl-login-page .cl-trust-badge {
      display: flex;
      width: 100%;
      min-height: 44px;
      align-items: center;
      gap: 8px;
      padding: 0 13px 0 11px;
      border: 1px solid var(--cl-line);
      border-radius: 10px;
      background: #ffffff;
      color: var(--cl-ink);
    }

    .cl-login-page .cl-shield {
      width: 20px;
      height: 20px;
      flex: 0 0 auto;
      color: var(--cl-purple);
    }

    .cl-login-page .cl-trust-badge strong {
      font-size: 14px;
      font-weight: 690;
      letter-spacing: -0.025em;
    }

    .cl-login-page .cl-trust-badge span {
      margin-left: auto;
      padding-left: 8px;
      border-left: 1px solid var(--cl-line);
      color: var(--cl-gray-500);
      font-size: 12px;
      font-weight: 500;
    }

    .cl-login-page .cl-trust-copy {
      margin: 11px 0 0;
      color: var(--cl-gray-600);
      font-size: 14px;
      font-weight: 420;
      letter-spacing: -0.02em;
      line-height: 1.58;
      word-break: keep-all;
    }

    /* --- actions --- */

    .cl-login-page .cl-actions {
      margin-top: 24px;
    }

    .cl-login-page .cl-instagram-button,
    .cl-login-page .cl-privacy-link {
      position: relative;
      display: flex;
      width: 100%;
      min-height: 54px;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      cursor: pointer;
      font-size: 15px;
      letter-spacing: -0.02em;
      transition:
        transform 160ms ease,
        box-shadow 160ms ease,
        border-color 160ms ease,
        background 160ms ease;
    }

    .cl-login-page .cl-instagram-button {
      gap: 11px;
      border: 1px solid var(--cl-purple);
      background: var(--cl-purple);
      box-shadow: 0 12px 26px rgba(125, 79, 222, 0.2);
      color: #ffffff;
      font-weight: 680;
    }

    .cl-login-page .cl-instagram-icon {
      display: grid;
      place-items: center;
    }

    .cl-login-page .cl-button-arrow {
      position: absolute;
      right: 17px;
      width: 20px;
      height: 20px;
      opacity: 0.72;
    }

    .cl-login-page .cl-privacy-link {
      margin-top: 11px;
      border: 0;
      background: transparent;
      color: #6d4bc0;
      font-weight: 560;
    }

    .cl-login-page .cl-instagram-button:active,
    .cl-login-page .cl-privacy-link:active {
      transform: scale(0.99);
    }

    .cl-login-page .cl-instagram-button:focus-visible,
    .cl-login-page .cl-privacy-link:focus-visible,
    .cl-login-page .cl-back-link:focus-visible {
      outline: 3px solid rgba(125, 79, 222, 0.27);
      outline-offset: 3px;
    }

    /* --- footer pinned to the bottom of the first viewport --- */

    .cl-login-page .cl-card-footer {
      margin-top: auto;
      padding-top: 16px;
    }

    .cl-login-page .cl-security-note {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      color: var(--cl-gray-500);
      font-size: 12px;
      font-weight: 450;
      letter-spacing: -0.02em;
      text-align: center;
    }

    .cl-login-page .cl-security-note .cl-shield {
      width: 16px;
      height: 16px;
      color: #a989eb;
    }

    .cl-login-page .cl-back-link {
      display: inline-flex;
      min-height: 44px;
      align-items: center;
      gap: 9px;
      color: #76717d;
      font-size: 15px;
      font-weight: 480;
    }

    .cl-login-page .cl-back-link svg {
      width: 20px;
      height: 20px;
      transition: transform 180ms ease;
    }

    .cl-login-page .cl-form-card .cl-back-link {
      justify-content: center;
      width: 100%;
      margin-top: 2px;
    }

    /* ---------------------------------------------------------------
       >=421px : roomier phones
       --------------------------------------------------------------- */

    @media (min-width: 421px) {
      .cl-login-page .cl-form-card {
        max-width: 560px;
        padding-right: max(24px, env(safe-area-inset-right));
        padding-left: max(24px, env(safe-area-inset-left));
      }

      .cl-login-page .cl-form-card .cl-brand-mark {
        width: 142px;
      }

      .cl-login-page .cl-mobile-visual {
        height: 132px;
        margin-top: 24px;
      }

      .cl-login-page .cl-ig-mini {
        width: 92px;
        height: 92px;
        border-radius: 28px;
      }

      .cl-login-page .cl-symbol-mini {
        width: 66px;
        height: 66px;
        margin-left: 42px;
        border-radius: 22px;
      }

      .cl-login-page .cl-symbol-mini::before {
        width: 42px;
        height: 42px;
      }

      .cl-login-page .cl-link-line {
        top: 66px;
        width: 72px;
      }

      .cl-login-page .cl-eyebrow {
        margin-top: 22px;
      }

      .cl-login-page .cl-lead {
        font-size: 15px;
      }

      .cl-login-page .cl-trust-badge {
        display: inline-flex;
        width: auto;
      }

      .cl-login-page .cl-trust-badge span {
        margin-left: 0;
      }
    }

    /* ---------------------------------------------------------------
       >=961px : desktop split layout
       --------------------------------------------------------------- */

    @media (min-width: 961px) {
      .cl-login-page {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: grid;
        grid-template-columns: minmax(0, 1.06fr) minmax(520px, 0.94fr);
        overflow: auto;
        background: #ffffff;
      }

      .cl-login-page .cl-form-card .cl-brand-mark,
      .cl-login-page .cl-mobile-visual,
      .cl-login-page .cl-form-card .cl-eyebrow,
      .cl-login-page .cl-card-footer {
        display: none;
      }

      .cl-login-page .cl-visual-panel {
        position: relative;
        display: block;
        min-height: 100vh;
        min-height: 100dvh;
        background:
          radial-gradient(circle at 50% 46%, rgba(125, 79, 222, 0.07), transparent 36%),
          #f8f7fb;
      }

      .cl-login-page .cl-visual-panel::after {
        position: absolute;
        inset: 0 0 0 auto;
        width: 1px;
        background: rgba(67, 48, 99, 0.05);
        content: "";
      }

      .cl-login-page .cl-story-inner {
        position: relative;
        width: min(100%, 680px);
        min-height: 100%;
        margin: 0 auto;
        padding: clamp(28px, 4vh, 48px) 56px 34px;
      }

      .cl-login-page .cl-visual-panel .cl-brand-mark {
        width: 166px;
        aspect-ratio: $logo_ratio;
      }

      .cl-login-page .cl-story-content {
        position: absolute;
        top: 51%;
        left: 50%;
        width: calc(100% - 112px);
        transform: translate(-50%, -50%);
      }

      .cl-login-page .cl-connection-visual {
        position: relative;
        width: 292px;
        height: 242px;
        margin: 0 auto 32px;
      }

      .cl-login-page .cl-halo {
        position: absolute;
        top: 16px;
        left: 27px;
        width: 238px;
        height: 205px;
        border-radius: 48%;
        background:
          radial-gradient(circle at 50% 48%, rgba(125, 79, 222, 0.22),
            rgba(125, 79, 222, 0.06) 50%, transparent 72%);
        filter: blur(2px);
      }

      .cl-login-page .cl-orbit {
        position: absolute;
        border: 1px solid rgba(125, 79, 222, 0.16);
        border-radius: 999px;
        transform: rotate(-14deg);
      }

      .cl-login-page .cl-orbit-one {
        top: 18px;
        left: 20px;
        width: 247px;
        height: 190px;
      }

      .cl-login-page .cl-orbit-two {
        top: 38px;
        left: 44px;
        width: 199px;
        height: 151px;
        border-style: dashed;
      }

      .cl-login-page .cl-ig-tile {
        position: absolute;
        top: 38px;
        left: 66px;
        display: grid;
        width: 142px;
        height: 142px;
        place-items: center;
        overflow: hidden;
        border: 8px solid rgba(255, 255, 255, 0.9);
        border-radius: 38px;
        background:
          radial-gradient(circle at 68% 72%, #ffcc66 0 13%, transparent 35%),
          radial-gradient(circle at 30% 102%, #f8a63a 0 24%, transparent 48%),
          linear-gradient(145deg, #7d4fde 2%, #c83d9a 51%, #ed6c5f 78%, #f9b24b 100%);
        box-shadow:
          0 26px 48px rgba(88, 52, 155, 0.23),
          0 8px 18px rgba(88, 52, 155, 0.14);
        color: #ffffff;
        transform: rotate(-4deg);
      }

      .cl-login-page .cl-tile-shine {
        position: absolute;
        top: -54px;
        left: -72px;
        width: 170px;
        height: 60px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.22);
        transform: rotate(-35deg);
      }

      .cl-login-page .cl-symbol-card {
        position: absolute;
        top: 17px;
        right: 21px;
        display: grid;
        width: 68px;
        height: 68px;
        place-items: center;
        border: 1px solid rgba(125, 79, 222, 0.12);
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 16px 30px rgba(72, 43, 129, 0.15);
        transform: rotate(7deg);
      }

      .cl-login-page .cl-symbol-card::before {
        width: 44px;
        height: 44px;
        background-image: var(--cl-symbol);
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        content: "";
      }

      .cl-login-page .cl-data-chip {
        position: absolute;
        bottom: 20px;
        left: 24px;
        display: flex;
        min-height: 44px;
        align-items: center;
        gap: 9px;
        padding: 0 16px;
        border: 1px solid rgba(125, 79, 222, 0.12);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.96);
        box-shadow: 0 14px 30px rgba(72, 43, 129, 0.12);
        color: #4b386f;
        font-size: 13px;
        font-weight: 650;
        letter-spacing: -0.02em;
        transform: rotate(-3deg);
      }

      .cl-login-page .cl-data-dot {
        width: 8px;
        height: 8px;
        border: 2px solid #c7b0f6;
        border-radius: 50%;
        background: var(--cl-purple);
        box-shadow: 0 0 0 4px #f0e9ff;
      }

      .cl-login-page .cl-sparkle {
        position: absolute;
        color: #b996ff;
      }

      .cl-login-page .cl-sparkle-one {
        top: 12px;
        left: 36px;
        width: 22px;
      }

      .cl-login-page .cl-sparkle-two {
        right: 47px;
        bottom: 38px;
        width: 13px;
        color: #e2d4ff;
      }

      .cl-login-page .cl-story-copy {
        text-align: center;
      }

      .cl-login-page .cl-story-copy .cl-eyebrow {
        margin: 0 0 12px;
      }

      .cl-login-page .cl-story-title {
        margin: 0;
        color: var(--cl-ink);
        font-size: clamp(28px, 2.45vw, 38px);
        font-weight: 750;
        letter-spacing: -0.042em;
        line-height: 1.22;
        word-break: keep-all;
      }

      .cl-login-page .cl-story-copy p {
        margin: 12px 0 0;
        color: var(--cl-gray-600);
        font-size: 16px;
        font-weight: 420;
        letter-spacing: -0.025em;
        line-height: 1.65;
        word-break: keep-all;
      }

      .cl-login-page .cl-visual-panel .cl-back-link {
        position: absolute;
        bottom: 30px;
        left: 56px;
      }

      .cl-login-page .cl-form-panel {
        min-height: 100vh;
        min-height: 100dvh;
        align-items: center;
        justify-content: center;
      }

      .cl-login-page .cl-form-card {
        flex: 0 0 auto;
        max-width: 500px;
        padding: 48px 38px;
      }

      .cl-login-page .cl-form-title {
        font-size: clamp(26px, 2.05vw, 32px);
        line-height: 1.26;
      }

      .cl-login-page .cl-lead {
        margin-top: 16px;
        font-size: 15.5px;
        line-height: 1.65;
      }

      .cl-login-page .cl-trust-block {
        margin-top: 26px;
      }

      .cl-login-page .cl-trust-badge {
        min-height: 40px;
      }

      .cl-login-page .cl-trust-copy {
        margin-top: 13px;
      }

      .cl-login-page .cl-actions {
        margin-top: 28px;
      }
    }

    /* ---------------------------------------------------------------
       Short phones: keep the CTA inside the first viewport.
       --------------------------------------------------------------- */

    @media (max-height: 720px) and (max-width: 960px) {
      .cl-login-page .cl-mobile-visual {
        height: 92px;
        margin-top: 6px;
        transform: scale(0.8);
      }

      .cl-login-page .cl-eyebrow {
        margin-top: 6px;
      }

      .cl-login-page .cl-form-title {
        font-size: 25px;
      }

      .cl-login-page .cl-lead {
        margin-top: 10px;
        line-height: 1.5;
      }

      .cl-login-page .cl-trust-block {
        margin-top: 14px;
      }

      .cl-login-page .cl-actions {
        margin-top: 16px;
      }

      .cl-login-page .cl-card-footer {
        padding-top: 8px;
      }

      .cl-login-page .cl-form-card {
        padding-bottom: max(16px, env(safe-area-inset-bottom));
      }

      .cl-login-page .cl-form-card .cl-back-link {
        min-height: 38px;
        margin-top: 0;
      }
    }

    /* ---------------------------------------------------------------
       Landscape phones. Too short for the connect graphic and the pinned
       footer; drop both so the CTA stays in the first screen.
       --------------------------------------------------------------- */

    @media (max-height: 500px) and (max-width: 960px) {
      .cl-login-page .cl-mobile-visual,
      .cl-login-page .cl-card-footer {
        display: none;
      }

      .cl-login-page .cl-form-card {
        max-width: 640px;
        padding-top: max(14px, env(safe-area-inset-top));
        padding-bottom: max(14px, env(safe-area-inset-bottom));
      }

      .cl-login-page .cl-form-card .cl-brand-mark {
        width: 118px;
      }

      .cl-login-page .cl-eyebrow {
        margin: 10px 0 6px;
      }

      .cl-login-page .cl-form-title {
        font-size: 22px;
      }

      .cl-login-page .cl-lead {
        margin-top: 8px;
        font-size: 14px;
        line-height: 1.45;
      }

      .cl-login-page .cl-trust-block {
        margin-top: 10px;
      }

      .cl-login-page .cl-trust-copy {
        margin-top: 8px;
      }

      .cl-login-page .cl-actions {
        margin-top: 12px;
      }

      .cl-login-page .cl-privacy-link {
        min-height: 44px;
        margin-top: 6px;
      }
    }

    /* Hover effects only where a real pointer exists, so a tap does not
       leave the CTA stuck in its hover state on touch devices. */
    @media (hover: hover) {
      .cl-login-page .cl-instagram-button:hover {
        border-color: var(--cl-purple-strong);
        background: var(--cl-purple-strong);
        box-shadow: 0 15px 30px rgba(125, 79, 222, 0.28);
        transform: translateY(-1px);
      }

      .cl-login-page .cl-privacy-link:hover {
        background: var(--cl-purple-soft);
      }

      .cl-login-page .cl-back-link:hover {
        color: var(--cl-purple);
      }

      .cl-login-page .cl-back-link:hover svg {
        transform: translateX(-3px);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .cl-login-page *,
      .cl-login-page *::before,
      .cl-login-page *::after {
        transition-duration: 0.01ms !important;
      }
    }
    </style>
    """
)


def render_login_page(
    oauth_url: str,
    *,
    back_url: str = "/",
    privacy_url: str = "/Privacy",
) -> None:
    """Render the full-screen CelebLife Instagram OAuth entry page."""

    logo_uri = _data_uri(ASSET_DIR / "celeblife_logo_purple.png")
    symbol_uri = _data_uri(ASSET_DIR / "celeblife_symbol_purple.png")

    safe_oauth_url = html.escape(oauth_url, quote=True)
    safe_back_url = html.escape(back_url, quote=True)
    safe_privacy_url = html.escape(privacy_url, quote=True)

    styles = _STYLE_TEMPLATE.substitute(
        logo_uri=logo_uri,
        symbol_uri=symbol_uri,
        logo_ratio=LOGO_ASPECT_RATIO,
        font_stack=FONT_STACK,
    )

    markup = f"""
    <main class="cl-login-page">
      <section class="cl-visual-panel" aria-labelledby="cl-story-title">
        <div class="cl-story-inner">
          <div class="cl-brand-mark" role="img" aria-label="CelebLife"></div>

          <div class="cl-story-content">
            <div class="cl-connection-visual" aria-hidden="true">
              <div class="cl-halo"></div>
              <div class="cl-orbit cl-orbit-one"></div>
              <div class="cl-orbit cl-orbit-two"></div>

              <div class="cl-ig-tile">
                {_instagram_icon(82)}
                <span class="cl-tile-shine"></span>
              </div>

              <div class="cl-symbol-card"></div>

              <div class="cl-data-chip">
                <span class="cl-data-dot"></span>
                채널 데이터 연결
              </div>

              {_sparkle("cl-sparkle-one")}
              {_sparkle("cl-sparkle-two")}
            </div>

            <div class="cl-story-copy">
              <p class="cl-eyebrow">CELEBLIFE ONBOARDING</p>
              <h2 class="cl-story-title" id="cl-story-title">인스타그램을 연결해 주세요</h2>
              <p>
                채널 데이터를 바탕으로 셀럽님에게 꼭 맞는 판매 전략을 설계합니다.
              </p>
            </div>
          </div>

          <a class="cl-back-link" href="{safe_back_url}" target="_self">
            {_back_arrow()}
            <span>이전으로</span>
          </a>
        </div>
      </section>

      <section class="cl-form-panel" aria-labelledby="cl-form-title">
        <div class="cl-form-card">
          <div class="cl-brand-mark" role="img" aria-label="CelebLife"></div>

          <div class="cl-mobile-visual" aria-hidden="true">
            <div class="cl-ig-mini">{_instagram_icon(48)}</div>
            <span class="cl-link-line"></span>
            <div class="cl-symbol-mini"></div>
          </div>

          <div class="cl-heading-group">
            <p class="cl-eyebrow">CELEBLIFE ONBOARDING</p>
            <h1 class="cl-form-title" id="cl-form-title">
              인스타그램에 로그인하고<br>
              셀럽라이프와 연결해 주세요
            </h1>
            <p class="cl-lead">
              연결된 채널의 콘텐츠와 반응 데이터를 분석해 셀럽님의 팬덤에 가장 잘 맞는
              제품과 판매 전략을 설계합니다. 명시적인 동의 없이 어떠한 작업도
              진행하지 않아요.
            </p>
          </div>

          <div class="cl-trust-block">
            <div class="cl-trust-badge">
              {_shield_icon()}
              <strong>Meta 공식 로그인 방식</strong>
              <span>안전한 연결</span>
            </div>
            <p class="cl-trust-copy">
              인스타그램 비밀번호는 셀럽라이프에 공유되거나 저장되지 않습니다.
              연결 권한은 언제든 직접 해제할 수 있어요.
            </p>
          </div>

          <div class="cl-actions">
            <a
              class="cl-instagram-button"
              href="{safe_oauth_url}"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span class="cl-instagram-icon">{_instagram_icon(21)}</span>
              <span>Instagram으로 계속하기</span>
              <svg aria-hidden="true" class="cl-button-arrow" viewBox="0 0 20 20" fill="none">
                <path d="m7.5 4.5 5 5.5-5 5.5" stroke="currentColor"
                  stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </a>

            <a class="cl-privacy-link" href="{safe_privacy_url}" target="_self">
              개인정보 및 권한 안내
            </a>
          </div>

          <div class="cl-card-footer">
            <div class="cl-security-note">
              {_shield_icon()}
              <span>로그인 정보는 셀럽라이프에 저장되지 않아요.</span>
            </div>
            <a class="cl-back-link" href="{safe_back_url}" target="_self">
              {_back_arrow()}
              <span>이전으로</span>
            </a>
          </div>
        </div>
      </section>
    </main>
    """

    st.markdown(_compact_html(styles + markup), unsafe_allow_html=True)
