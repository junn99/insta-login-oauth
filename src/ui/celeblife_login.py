"""CelebLife Instagram OAuth login UI.

Mobile-first: the base stylesheet targets a 360px-wide phone and the desktop
split layout is layered on at >=961px. See
``celeblife_instagram_onboarding_ui/DESIGN_SYSTEM.md`` for the brand tokens.

Two Streamlit quirks are worked around here; both look like mistakes:

1. Every component selector is scoped under ``.cl-login-page``. The Streamlit
   theme styles markdown ``h1``-``h6``/``a`` through emotion classes
   (``.st-emotion-cache-xxxx h1``), which outranks a bare single-class selector
   -- including ``font-family: "Source Sans"``, a face with no Korean glyphs.
   The two-class scoping wins regardless of stylesheet order.

2. The headings are ``<p role="heading" aria-level>``, not ``<h1>``/``<h2>``.
   Streamlit renders every markdown heading through its ``CustomHeading``
   component, which spreads its own props *after* ours and so overwrites the
   ``id`` with a slug of the heading text -- for Korean text, slugify yields an
   empty string and it falls back to an ``xxhash`` digest. That silently breaks
   the ``aria-labelledby`` on both ``<section>`` elements, leaving them with no
   accessible name, and injects a wrapper plus a focusable "Link to heading"
   anchor into the tab order. There is no way to opt out from Python. Do not
   "restore" real heading tags without re-checking those two things.

Place this file at:
    src/ui/celeblife_login.py

Required assets:
    assets/login/celeblife_logo_purple.png
    assets/login/celeblife_symbol_purple.png
"""

from __future__ import annotations

import base64
import html
import re
import textwrap
from pathlib import Path
from string import Template

import streamlit as st

from src.consent import CONSENT_ITEMS, all_required_accepted

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
      --cl-gray-500: #75707d;
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
      word-break: keep-all;
    }

    .cl-login-page .cl-hook-title {
      display: flex;
      flex-wrap: wrap;
      column-gap: 0.24em;
    }

    .cl-login-page .cl-hook-line {
      display: inline-block;
      white-space: nowrap;
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

    .cl-login-page button.cl-instagram-button {
      appearance: none;
      font-family: inherit;
    }

    .cl-login-page .cl-instagram-button[disabled],
    .cl-login-page .cl-instagram-button[aria-disabled="true"] {
      cursor: not-allowed;
      opacity: 0.74;
      transform: none;
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
    .cl-login-page .cl-privacy-link:focus-visible {
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
        /* Definite height, not just min-height: .cl-story-inner below resolves
           min-height: 100% against this, and a percentage against an auto-height
           parent is not reliably resolved outside Chromium. */
        height: 100vh;
        height: 100dvh;
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

      /* Must NOT be ".cl-story-copy p": that is (0,2,1) and would outrank the
         (0,2,0) .cl-story-title and .cl-eyebrow rules sharing this container. */
      .cl-login-page .cl-story-lead {
        margin: 12px 0 0;
        color: var(--cl-gray-600);
        font-size: 16px;
        font-weight: 420;
        letter-spacing: -0.025em;
        line-height: 1.65;
        word-break: keep-all;
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

    @media (max-height: 720px) and (max-width: 960.98px) {
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

    }

    /* ---------------------------------------------------------------
       Landscape phones. Too short for the connect graphic and the pinned
       footer; drop both so the CTA stays in the first screen.
       --------------------------------------------------------------- */

    @media (max-height: 500px) and (max-width: 960.98px) {
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

      .cl-login-page .cl-instagram-button[disabled]:hover,
      .cl-login-page .cl-instagram-button[aria-disabled="true"]:hover {
        border-color: var(--cl-purple);
        background: var(--cl-purple);
        box-shadow: 0 12px 26px rgba(125, 79, 222, 0.2);
        transform: none;
      }

      .cl-login-page .cl-privacy-link:hover {
        background: var(--cl-purple-soft);
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
    oauth_url: str | None,
    *,
    back_url: str = "/",
    privacy_url: str = "/Privacy",
    oauth_disabled: bool = False,
    continue_url: str | None = "/Login?step=consent",
) -> None:
    """Render the full-screen CelebLife Instagram OAuth entry page."""

    _ = back_url  # Kept for callers; the login screen no longer renders a back action.
    # The entry CTA is intentionally local. Even if an older caller still passes
    # an OAuth URL, the consent screen must remain the only route to Instagram.
    _ = oauth_url
    cta_url = (
        "/auth/instagram/start"
        if continue_url == "/auth/instagram/start"
        else "/Login?step=consent"
    )
    logo_uri = _data_uri(ASSET_DIR / "celeblife_logo_purple.png")
    symbol_uri = _data_uri(ASSET_DIR / "celeblife_symbol_purple.png")

    safe_cta_url = html.escape(cta_url or "", quote=True)
    _ = privacy_url

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
            <div class="cl-ig-mini">{_instagram_icon(48)}</div>
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
            {_instagram_cta(safe_cta_url, oauth_disabled=oauth_disabled)}
          </div>

          <div class="cl-card-footer">
            <div class="cl-security-note">
              {_shield_icon()}
              <span>로그인 정보는 셀럽라이프에 저장되지 않아요.</span>
            </div>
          </div>
        </div>
      </section>
    </main>
    """

    st.markdown(_compact_html(styles + markup), unsafe_allow_html=True)


def _sync_all_consent() -> None:
    st.session_state.pop("cl_oauth_handoff_url", None)
    all_key = "cl_consent_all"
    item_keys = [f"cl_consent_{item.key}" for item in CONSENT_ITEMS]

    if st.session_state.get(all_key):
        for key in item_keys:
            st.session_state[key] = True
    else:
        for key in item_keys:
            st.session_state[key] = False


def _sync_individual_consent() -> None:
    st.session_state.pop("cl_oauth_handoff_url", None)
    all_key = "cl_consent_all"
    item_keys = [f"cl_consent_{item.key}" for item in CONSENT_ITEMS]
    st.session_state[all_key] = all(bool(st.session_state.get(key)) for key in item_keys)


def _reset_consent_state() -> None:
    st.session_state.pop("cl_oauth_handoff_url", None)
    st.session_state["cl_consent_all"] = False
    for item in CONSENT_ITEMS:
        st.session_state[f"cl_consent_{item.key}"] = False
    st.session_state["cl_consent_instagram_permissions_accepted"] = False


_CONSENT_DETAIL_TITLES = {
    "terms_accepted": "서비스 이용약관",
    "privacy_accepted": "개인정보 수집·이용",
}

_CONSENT_DETAIL_KEYS = frozenset(_CONSENT_DETAIL_TITLES)

_PRIVACY_SECTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_PRIVACY_SUBSECTION_HEADINGS = frozenset(
    {
        "회원 정보",
        "Instagram 계정 정보",
        "Instagram 인사이트 및 콘텐츠 성과정보",
        "오디언스 통계정보",
        "인증정보",
        "Instagram에서 앱 연결 해제",
        "이메일을 통한 삭제 요청",
    }
)

_PRIVACY_LIST_INTRO_LINES = frozenset(
    {
        "셀럽라이프 회원가입 및 서비스 제공을 위해 다음 정보를 처리합니다.",
        "Instagram OAuth를 통해 Instagram 계정을 연결하는 경우 다음 정보를 처리할 수 있습니다.",
        "Instagram에서 제공하는 권한 범위 내에서 다음과 같은 정보를 처리할 수 있습니다.",
        "수집된 정보는 다음 목적으로 이용됩니다.",
        "AI 분석은 다음과 같은 목적으로 사용됩니다.",
        "셀럽라이프는 서비스 운영을 위해 다음과 같은 외부 서비스를 이용할 수 있습니다.",
        "다만 다음의 경우에는 예외로 할 수 있습니다.",
        "회사는 이용자의 개인정보를 보호하기 위해 다음과 같은 보안조치를 적용합니다.",
        "이용자는 자신의 개인정보에 대하여 다음과 같은 요청을 할 수 있습니다.",
    }
)

_TERMS_TITLE_PREFIX = "셀럽라이프 인플루언서 서비스 이용약관"
_TERMS_ARTICLE_RE = re.compile(r"^제(\d+)조\s*\((.+)\)$")
_TERMS_APPENDIX_RE = re.compile(r"^별표\s*(\d+)\s*\|\s*(.+)$")
_TERMS_META_PREFIXES = ("운영 서비스:", "운영 사업자:", "작성 기준일:")
_TERMS_STATUS_BADGES = frozenset({"인정", "증빙 시 인정", "불인정"})
_TERMS_SUMMARY_LABELS = (
    "소싱 제품 보호",
    "기존 일정 예외",
    "선행 독점·전속 예외",
    "단순 제안은 예외 아님",
    "노쇼·일방 취소",
    "우회 거래 손해배상",
)
_TERMS_NAMED_LIST_HEADINGS = frozenset({"입증자료 예시"})


def _consent_modal_id(item_key: str) -> str:
    return f"cl-consent-modal-{item_key.replace('_', '-')}"


def _consent_trigger_id(item_key: str) -> str:
    return f"cl-consent-trigger-{item_key.replace('_', '-')}"


def _consent_detail_link(item_key: str) -> str:
    modal_id = html.escape(_consent_modal_id(item_key), quote=True)
    trigger_id = html.escape(_consent_trigger_id(item_key), quote=True)
    return (
        f'<a class="cl-consent-detail-link" id="{trigger_id}" href="#{modal_id}" '
        f'role="button" aria-haspopup="dialog" aria-controls="{modal_id}">'
        "상세 보기"
        "</a>"
    )


def _line_is_privacy_list_row(line: str) -> bool:
    if line in _PRIVACY_SUBSECTION_HEADINGS:
        return False
    if _PRIVACY_SECTION_RE.match(line) or line == "부칙":
        return False
    if line in _PRIVACY_LIST_INTRO_LINES:
        return False
    if line.startswith("본 ") or line.startswith("주식회사 "):
        return False
    if "다." in line or "니다." in line or "합니다." in line or "습니다." in line:
        return False
    return len(line) <= 34 or ":" in line


def _privacy_policy_body_html(body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) < 4:
        return _paragraph_detail_body_html(body)

    title, updated_at, *remaining = lines
    parts = [
        '<article class="cl-policy-modal__document cl-policy-modal__document--privacy">',
        '<div class="cl-policy-modal__document-title">'
        f"{html.escape(title)}"
        "</div>",
        '<p class="cl-policy-modal__metadata">'
        f"{html.escape(updated_at)}"
        "</p>",
        '<div class="cl-policy-modal__intro">',
        f"<p>{html.escape(remaining[0])}</p>",
        f"<p>{html.escape(remaining[1])}</p>",
        "</div>",
    ]

    list_rows: list[str] = []

    def flush_list() -> None:
        if not list_rows:
            return
        parts.append('<ul class="cl-policy-modal__list">')
        parts.extend(
            '<li class="cl-policy-modal__list-row">'
            f"{html.escape(row)}"
            "</li>"
            for row in list_rows
        )
        parts.append("</ul>")
        list_rows.clear()

    for line in remaining[2:]:
        section_match = _PRIVACY_SECTION_RE.match(line)
        if section_match:
            flush_list()
            section_no, section_title = section_match.groups()
            parts.append(
                '<p class="cl-policy-modal__section-heading cl-policy-modal__section">'
                f'<span class="cl-policy-modal__section-number">{html.escape(section_no)}</span>'
                f"<span>{html.escape(section_title)}</span>"
                "</p>"
            )
            continue

        if line == "부칙":
            flush_list()
            parts.append(
                '<p class="cl-policy-modal__section-heading cl-policy-modal__section cl-policy-modal__section--appendix">'
                '<span class="cl-policy-modal__section-number">부칙</span>'
                "<span>시행일</span>"
                "</p>"
            )
            continue

        if line in _PRIVACY_SUBSECTION_HEADINGS:
            flush_list()
            parts.append(
                '<p class="cl-policy-modal__subheading">'
                f"{html.escape(line)}"
                "</p>"
            )
            continue

        if _line_is_privacy_list_row(line):
            list_rows.append(line)
            continue

        flush_list()
        parts.append(
            '<p class="cl-policy-modal__paragraph">'
            f"{html.escape(line)}"
            "</p>"
        )

    flush_list()
    parts.append("</article>")
    return "".join(parts)


def _terms_pipe_cells(line: str) -> list[str] | None:
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if len(cells) != 3 or any(not cell for cell in cells):
        return None
    return cells


def _terms_pipe_table_row_html(line: str, headers: tuple[str, str, str]) -> str | None:
    cells = _terms_pipe_cells(line)
    if cells is None:
        return None

    def cell_html(label: str, value: str) -> str:
        safe_value = html.escape(value)
        if value in _TERMS_STATUS_BADGES:
            safe_value = (
                '<span class="cl-policy-modal__status-badge">'
                f"{safe_value}"
                "</span>"
            )
        return (
            '<span class="cl-policy-modal__table-cell">'
            f'<span class="cl-policy-modal__table-label">{html.escape(label)}</span>'
            f'<span class="cl-policy-modal__table-value">{safe_value}</span>'
            "</span>"
        )

    return (
        '<li class="cl-policy-modal__table-row">'
        + cell_html(headers[0], cells[0])
        + cell_html(headers[1], cells[1])
        + cell_html(headers[2], cells[2])
        + "</li>"
    )


def _terms_is_list_row(line: str) -> bool:
    return bool(line.startswith(("-", "•", "·")) or re.match(r"^\d+[.)]\s+", line))


def _terms_policy_body_html(body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines or not lines[0].startswith(_TERMS_TITLE_PREFIX):
        return _paragraph_detail_body_html(body)

    title = lines[0]
    subtitle = lines[1] if len(lines) > 1 else ""
    parts = [
        '<article class="cl-policy-modal__document cl-policy-modal__document--terms">',
        '<div class="cl-policy-modal__document-title">'
        f"{html.escape(title)}"
        "</div>",
    ]
    if subtitle and not subtitle.startswith(_TERMS_META_PREFIXES):
        parts.append(
            '<p class="cl-policy-modal__document-subtitle">'
            f"{html.escape(subtitle)}"
            "</p>"
        )
        content_lines = lines[2:]
    else:
        content_lines = lines[1:]

    list_rows: list[str] = []
    summary_rows: list[tuple[str, str]] = []
    table_rows: list[str] = []
    table_headers: tuple[str, str, str] = ("항목", "기준", "상태")
    in_summary = False
    pending_summary_label: str | None = None

    def flush_list() -> None:
        if not list_rows:
            return
        parts.append('<ul class="cl-policy-modal__list">')
        parts.extend(
            '<li class="cl-policy-modal__list-row">'
            f"{html.escape(row)}"
            "</li>"
            for row in list_rows
        )
        parts.append("</ul>")
        list_rows.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        parts.append('<ul class="cl-policy-modal__table-list">')
        parts.extend(table_rows)
        parts.append("</ul>")
        table_rows.clear()

    def flush_summary() -> None:
        if not summary_rows:
            return
        parts.append('<div class="cl-policy-modal__summary-grid">')
        for label, description in summary_rows:
            parts.append(
                '<div class="cl-policy-modal__summary-card">'
                f'<p class="cl-policy-modal__summary-label">{html.escape(label)}</p>'
                f'<p class="cl-policy-modal__summary-description">{html.escape(description)}</p>'
                "</div>"
            )
        parts.append("</div>")
        summary_rows.clear()

    for line in content_lines:
        table_cells = _terms_pipe_cells(line)
        if table_cells and set(table_cells) & {"처리 원칙", "산정 기준", "기존 확정 인정"}:
            flush_list()
            flush_summary()
            table_headers = (table_cells[0], table_cells[1], table_cells[2])
            continue

        if table_cells:
            table_html = _terms_pipe_table_row_html(line, table_headers)
            flush_list()
            flush_summary()
            if table_html:
                table_rows.append(table_html)
            continue

        if line.startswith(_TERMS_META_PREFIXES):
            flush_list()
            flush_table()
            flush_summary()
            key, value = line.split(":", 1)
            parts.append(
                '<p class="cl-policy-modal__metadata cl-policy-modal__metadata-row">'
                f'<span>{html.escape(key.strip())}</span>'
                f'<strong>{html.escape(value.strip())}</strong>'
                "</p>"
            )
            continue

        if line == "중요 조항 요약":
            flush_list()
            flush_table()
            flush_summary()
            in_summary = True
            pending_summary_label = None
            parts.append(
                '<p class="cl-policy-modal__section-heading cl-policy-modal__section">'
                '<span class="cl-policy-modal__section-number">요약</span>'
                "<span>중요 조항 요약</span>"
                "</p>"
            )
            continue

        article_match = _TERMS_ARTICLE_RE.match(line)
        appendix_match = _TERMS_APPENDIX_RE.match(line)
        if article_match or appendix_match or line == "부칙":
            flush_list()
            flush_table()
            flush_summary()
            in_summary = False
            pending_summary_label = None
            if article_match:
                article_no, article_title = article_match.groups()
                parts.append(
                    '<p class="cl-policy-modal__section-heading cl-policy-modal__section cl-policy-modal__section--article">'
                    f'<span class="cl-policy-modal__section-number">제{html.escape(article_no)}조</span>'
                    f"<span>{html.escape(article_title)}</span>"
                    "</p>"
                )
            elif appendix_match:
                appendix_no, appendix_title = appendix_match.groups()
                parts.append(
                    '<p class="cl-policy-modal__section-heading cl-policy-modal__section cl-policy-modal__section--appendix">'
                    f'<span class="cl-policy-modal__section-number">별표 {html.escape(appendix_no)}</span>'
                    f"<span>{html.escape(appendix_title)}</span>"
                    "</p>"
                )
            else:
                parts.append(
                    '<p class="cl-policy-modal__section-heading cl-policy-modal__section cl-policy-modal__section--appendix">'
                    '<span class="cl-policy-modal__section-number">부칙</span>'
                    "<span>시행일</span>"
                    "</p>"
                )
            continue

        if in_summary and line.startswith("※"):
            flush_summary()
            pending_summary_label = None
            parts.append(
                '<p class="cl-policy-modal__note">'
                f"{html.escape(line)}"
                "</p>"
            )
            continue

        if in_summary and line in _TERMS_SUMMARY_LABELS:
            flush_summary()
            pending_summary_label = line
            continue

        if in_summary and pending_summary_label:
            summary_rows.append((pending_summary_label, line))
            pending_summary_label = None
            if len(summary_rows) == len(_TERMS_SUMMARY_LABELS):
                flush_summary()
            continue

        if in_summary and ":" in line:
            label, description = line.split(":", 1)
            summary_rows.append((label.strip(), description.strip()))
            if len(summary_rows) == len(_TERMS_SUMMARY_LABELS):
                flush_summary()
            continue

        flush_summary()
        flush_table()
        if line in _TERMS_NAMED_LIST_HEADINGS:
            flush_list()
            parts.append(
                '<p class="cl-policy-modal__subheading">'
                f"{html.escape(line)}"
                "</p>"
            )
            continue

        if _terms_is_list_row(line):
            list_rows.append(line.lstrip("-•· ").strip())
            continue

        flush_list()
        parts.append(
            '<p class="cl-policy-modal__paragraph">'
            f"{html.escape(line)}"
            "</p>"
        )

    flush_summary()
    flush_table()
    flush_list()
    parts.append("</article>")
    return "".join(parts)


def _paragraph_detail_body_html(body: str) -> str:
    paragraphs: list[str] = []
    current_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            if current_lines:
                paragraphs.append(
                    '<p class="cl-policy-modal__paragraph">'
                    + "<br>".join(current_lines)
                    + "</p>"
                )
                current_lines = []
            continue
        current_lines.append(html.escape(stripped))
    if current_lines:
        paragraphs.append(
            '<p class="cl-policy-modal__paragraph">'
            + "<br>".join(current_lines)
            + "</p>"
        )
    return "".join(paragraphs)


def _consent_detail_body_html(item_key: str, body: str) -> str:
    if item_key == "terms_accepted":
        return _terms_policy_body_html(body)
    if item_key == "privacy_accepted":
        return _privacy_policy_body_html(body)
    return _paragraph_detail_body_html(body)


def _consent_detail_modals() -> str:
    modals: list[str] = []
    for item in CONSENT_ITEMS:
        if item.key not in _CONSENT_DETAIL_KEYS:
            continue
        modal_id = html.escape(_consent_modal_id(item.key), quote=True)
        trigger_id = html.escape(_consent_trigger_id(item.key), quote=True)
        safe_title = html.escape(_CONSENT_DETAIL_TITLES[item.key])
        safe_body = _consent_detail_body_html(item.key, item.body)
        modals.append(
            f"""
            <section class="cl-policy-modal" id="{modal_id}" role="dialog"
              aria-modal="true" aria-labelledby="{modal_id}-title"
              aria-describedby="{modal_id}-description" tabindex="-1">
              <a class="cl-policy-modal__backdrop" href="#{trigger_id}" aria-label="닫기"></a>
              <div class="cl-policy-modal__panel">
                <div class="cl-policy-modal__header">
                  <div>
                    <p class="cl-policy-modal__eyebrow">필수 안내</p>
                    <p class="cl-policy-modal__title" id="{modal_id}-title"
                      role="heading" aria-level="2">{safe_title}</p>
                  </div>
                  <a class="cl-policy-modal__close-icon" href="#{trigger_id}" aria-label="닫기">×</a>
                </div>
                <div class="cl-policy-modal__body" id="{modal_id}-description">{safe_body}</div>
                <div class="cl-policy-modal__footer">
                  <a class="cl-policy-modal__close-button" href="#{trigger_id}">확인했어요</a>
                </div>
              </div>
            </section>
            """
        )
    return "\n".join(modals)


def render_consent_page(
    oauth_url: str | None,
    *,
    privacy_url: str = "/Privacy",
    oauth_disabled: bool = False,
) -> None:
    """Render the required consent step before the Instagram OAuth redirect."""

    logo_uri = _data_uri(ASSET_DIR / "celeblife_logo_purple.png")
    symbol_uri = _data_uri(ASSET_DIR / "celeblife_symbol_purple.png")
    styles = _STYLE_TEMPLATE.substitute(
        logo_uri=logo_uri,
        symbol_uri=symbol_uri,
        logo_ratio=LOGO_ASPECT_RATIO,
        font_stack=FONT_STACK,
    )

    consent_styles = """
        <style>
        .cl-login-page.cl-consent-page {
          position: relative !important;
          inset: auto !important;
          z-index: auto !important;
          display: block !important;
          min-height: auto !important;
          overflow: visible !important;
          background: #ffffff !important;
        }
        .st-key-cl-consent-shell {
          --cl-consent-gutter: 20px;
          --cl-consent-block-gap: 16px;
          --cl-consent-panel-bottom: 12px;
          --cl-consent-shell-gap: 4px;
          max-width: 560px;
          margin: 0 auto;
          gap: var(--cl-consent-shell-gap) !important;
          padding:
            max(12px, env(safe-area-inset-top))
            var(--cl-consent-gutter)
            max(28px, env(safe-area-inset-bottom));
        }
        #root .stApp .st-key-cl-consent-shell,
        #root .stApp .st-key-cl-consent-shell * {
          font-family: __CONSENT_FONT_STACK__ !important;
        }
        #root .stApp .st-key-cl-consent-shell [data-testid="stIconMaterial"] {
          font-family: "Material Symbols Rounded" !important;
        }
        #root .stApp .st-key-cl_consent_back button {
          width: auto;
          min-height: 44px !important;
          padding: 0 4px !important;
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
          color: #514b5a !important;
        }
        .cl-consent-page .cl-visual-panel { display: none !important; }
        .cl-consent-page .cl-form-panel {
          width: min(100%, 560px) !important;
          min-height: auto !important;
          margin: 0 auto !important;
          padding: max(20px, env(safe-area-inset-top)) 0 var(--cl-consent-panel-bottom) !important;
        }
        .cl-consent-page .cl-form-card {
          max-width: none !important;
          min-height: auto !important;
          padding: 0 !important;
          box-shadow: none !important;
        }
        .cl-login-page.cl-consent-page .cl-form-card .cl-brand-mark {
          display: block !important;
        }
        .cl-consent-page .cl-consent-copy {
          margin-top: 22px;
        }
        .cl-consent-page .cl-form-title { line-height: 1.4 !important; }
        .cl-consent-page .cl-lead {
          margin-top: var(--cl-consent-block-gap) !important;
          line-height: 1.8 !important;
        }
        .st-key-cl-consent-shell [data-testid="stMarkdownContainer"]:has(.cl-consent-page) {
          margin-bottom: 0 !important;
        }
        .st-key-cl-consent-shell .stCheckbox {
          min-height: 44px;
          margin: 0 !important;
        }
        .st-key-cl-consent-shell .stCheckbox label {
          align-items: flex-start;
          min-height: 44px;
        }
        .st-key-cl-consent-shell .stElementContainer {
          margin-bottom: 0 !important;
        }
        .st-key-cl-consent-shell .stCheckbox label p {
          line-height: 1.52;
          margin: 0;
          word-break: keep-all;
        }
        .st-key-cl-consent-shell [data-testid="stCheckbox"] input[type="checkbox"] {
          accent-color: #7d4fde !important;
        }
        .st-key-cl-consent-shell [data-testid="stCheckbox"] label > div:first-of-type {
          border-color: rgba(125, 79, 222, 0.42) !important;
        }
        .st-key-cl-consent-shell [data-testid="stCheckbox"] label > div:first-of-type svg {
          color: #ffffff !important;
        }
        .st-key-cl-consent-shell [data-testid="stCheckbox"] label[data-selected] > div:first-of-type {
          border-color: #7d4fde !important;
          background-color: #7d4fde !important;
        }
        .st-key-cl-consent-shell [data-testid="stCheckbox"] label[data-focus-visible] > div:first-of-type {
          box-shadow: 0 0 0 3px rgba(125, 79, 222, 0.22) !important;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_item_"] {
          margin-bottom: 0;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_item_"] .stHorizontalBlock {
          align-items: flex-start;
          flex-wrap: nowrap !important;
          gap: 8px !important;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_item_"] .stHorizontalBlock > [data-testid="stColumn"]:first-child {
          flex: 1 1 auto !important;
          min-width: 0 !important;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_item_"] .stHorizontalBlock > [data-testid="stColumn"]:last-child {
          flex: 0 0 auto !important;
          min-width: auto !important;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_detail_"] .stButton {
          display: flex;
          justify-content: flex-end;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_detail_"] [data-testid="stMarkdownContainer"] p {
          display: flex;
          align-items: flex-start;
          justify-content: flex-end;
          margin: 0 !important;
        }
        .st-key-cl-consent-shell [class*="st-key-cl_consent_detail_"] [data-testid="stMarkdownContainer"] {
          margin: 0 !important;
        }
        .st-key-cl-consent-shell .cl-consent-detail-link {
          display: inline-flex;
          align-items: flex-start;
          justify-content: flex-end;
          min-height: 44px;
          box-sizing: border-box;
          padding: 0 !important;
          color: #7d4fde !important;
          font-weight: 700;
          line-height: 1.52;
          text-decoration: none !important;
          white-space: nowrap;
        }
        .cl-policy-modal,
        .cl-policy-modal * {
          font-family: __CONSENT_FONT_STACK__ !important;
        }
        .cl-policy-modal {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: none;
          align-items: center;
          justify-content: center;
          padding: 24px 18px;
        }
        .cl-policy-modal:target {
          display: flex;
        }
        .cl-policy-modal__backdrop {
          position: absolute;
          inset: 0;
          background: rgba(22, 18, 32, 0.46);
          backdrop-filter: blur(3px);
        }
        .cl-policy-modal__panel {
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
        }
        .cl-policy-modal__header {
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
        }
        .cl-policy-modal__eyebrow {
          margin: 0 0 4px;
          color: #7d4fde;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.1em;
          line-height: 1.35;
        }
        .cl-policy-modal__title {
          margin: 0;
          color: #171321;
          font-size: 20px;
          font-weight: 800;
          line-height: 1.42;
        }
        .cl-policy-modal__close-icon {
          display: inline-flex;
          flex: 0 0 auto;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 999px;
          background: #f7f3ff;
          color: #514b5a !important;
          font-size: 26px;
          line-height: 1;
          text-decoration: none !important;
        }
        .cl-policy-modal__close-icon:focus-visible,
        .cl-policy-modal__close-button:focus-visible {
          outline: 3px solid rgba(125, 79, 222, 0.28);
          outline-offset: 2px;
        }
        .cl-policy-modal__body {
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
        }
        .cl-policy-modal__document-title {
          margin: 0;
          color: #171321;
          font-size: 18px;
          font-weight: 800;
          line-height: 1.42;
        }
        .cl-policy-modal__metadata {
          margin: 6px 0 0;
          color: #7d7286;
          font-size: 12.5px;
          font-weight: 620;
          line-height: 1.5;
        }
        .cl-policy-modal__document-subtitle {
          margin: 8px 0 0;
          color: #5b5369;
          font-size: 14px;
          font-weight: 560;
          line-height: 1.6;
        }
        .cl-policy-modal__metadata-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          margin-top: 8px;
          padding: 9px 11px;
          border: 1px solid rgba(125, 79, 222, 0.1);
          border-radius: 12px;
          background: #fbfaff;
        }
        .cl-policy-modal__metadata-row span {
          color: #7d7286;
          font-weight: 700;
        }
        .cl-policy-modal__metadata-row strong {
          color: #2a2335;
          font-weight: 760;
          text-align: right;
        }
        .cl-policy-modal__intro {
          display: grid;
          gap: 8px;
          margin-top: 14px;
          padding: 14px;
          border: 1px solid rgba(125, 79, 222, 0.14);
          border-radius: 14px;
          background: #faf8ff;
        }
        .cl-policy-modal__intro p {
          margin: 0;
          color: #453d52;
          font-size: 14.5px;
          line-height: 1.72;
        }
        .cl-policy-modal__section {
          margin-top: 22px;
        }
        .cl-policy-modal__section-heading {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin: 0 0 10px;
          color: #201a2d;
          font-size: 15px;
          font-weight: 780;
          line-height: 1.45;
        }
        .cl-policy-modal__section-number {
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
        }
        .cl-policy-modal__subheading {
          margin: 14px 0 6px;
          color: #2a2335;
          font-size: 14px;
          font-weight: 740;
          line-height: 1.45;
        }
        .cl-policy-modal__list {
          display: grid;
          gap: 8px;
          margin: 8px 0 0;
          padding: 0;
          list-style: none;
        }
        .cl-policy-modal__list-row {
          position: relative;
          margin: 0;
          padding: 0 0 0 24px !important;
          color: #514b5a;
          font-size: 14px;
          line-height: 1.58;
          overflow-wrap: anywhere;
        }
        .cl-policy-modal__list-row::before {
          position: absolute;
          top: 0.72em;
          left: 7px;
          width: 5px;
          height: 5px;
          border-radius: 999px;
          background: #9b7cec;
          content: "";
        }
        .cl-policy-modal__summary-grid {
          display: grid;
          gap: 10px;
          margin-top: 12px;
        }
        .cl-policy-modal__summary-card {
          padding: 12px 13px;
          border: 1px solid rgba(125, 79, 222, 0.12);
          border-radius: 14px;
          background: linear-gradient(180deg, #ffffff 0%, #faf8ff 100%);
        }
        .cl-policy-modal__summary-label {
          margin: 0;
          color: #7d4fde;
          font-size: 12.5px;
          font-weight: 820;
          line-height: 1.4;
        }
        .cl-policy-modal__summary-description {
          margin: 5px 0 0;
          color: #443d50;
          font-size: 14px;
          line-height: 1.58;
        }
        .cl-policy-modal__note {
          margin: 12px 0 0;
          padding: 11px 12px;
          border-left: 3px solid #9b7cec;
          border-radius: 12px;
          background: #fbfaff;
          color: #5b5369;
          font-size: 13.5px;
          line-height: 1.64;
        }
        .cl-policy-modal__table-list {
          display: grid;
          gap: 10px;
          margin: 10px 0 0;
          padding: 0;
          list-style: none;
        }
        .cl-policy-modal__table-row {
          display: grid;
          gap: 8px;
          padding: 12px;
          border: 1px solid rgba(43, 34, 63, 0.1);
          border-radius: 14px;
          background: #ffffff;
        }
        .cl-policy-modal__table-cell {
          display: grid;
          grid-template-columns: 64px minmax(0, 1fr);
          gap: 10px;
          align-items: start;
        }
        .cl-policy-modal__table-label {
          color: #83798f;
          font-size: 12px;
          font-weight: 780;
          line-height: 1.5;
        }
        .cl-policy-modal__table-value {
          color: #342d3f;
          font-size: 13.5px;
          line-height: 1.58;
          overflow-wrap: anywhere;
        }
        .cl-policy-modal__status-badge {
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
        }
        .cl-policy-modal__paragraph {
          margin: 8px 0 0;
          font-size: 14.5px;
          line-height: 1.72;
        }
        .cl-policy-modal__paragraph:last-child {
          margin-bottom: 0;
        }
        .cl-policy-modal__footer {
          display: flex;
          flex: 0 0 auto;
          padding: 14px 22px 18px;
          border-top: 1px solid rgba(124, 79, 222, 0.1);
          background: rgba(255, 255, 255, 0.98);
          box-shadow: 0 -12px 30px rgba(33, 26, 51, 0.06);
        }
        .cl-policy-modal__close-button {
          display: flex;
          width: 100%;
          align-items: center;
          justify-content: center;
          min-height: 48px;
          border-radius: 14px;
          font-weight: 800;
          text-decoration: none !important;
          color: #ffffff !important;
          background: #7d4fde;
        }
        .st-key-cl_consent_submit_disabled .stButton > button,
        .st-key-cl_consent_submit_link [data-testid="stLinkButton"] > a {
          position: relative;
          display: flex;
          width: 100%;
          min-height: 60px;
          align-items: center;
          justify-content: center;
          margin-top: 12px;
          border: 1px solid #7d4fde;
          border-radius: 12px;
          background: #7d4fde;
          box-shadow: 0 14px 28px rgba(125, 79, 222, 0.24);
          color: #ffffff !important;
          cursor: pointer;
          font-size: 15px;
          font-weight: 680;
          letter-spacing: -0.02em;
          text-decoration: none !important;
          transition:
            transform 160ms ease,
            box-shadow 160ms ease,
            border-color 160ms ease,
            background 160ms ease;
        }
        .st-key-cl_consent_submit_link [data-testid="stLinkButton"] > a:visited {
          color: #ffffff !important;
        }
        .st-key-cl_consent_submit_link [data-testid="stLinkButton"] > a:active {
          transform: scale(0.99);
        }
        .st-key-cl_consent_submit_link [data-testid="stLinkButton"] > a:focus-visible {
          outline: 3px solid rgba(125, 79, 222, 0.28);
          outline-offset: 3px;
        }
        #root .stApp .st-key-cl_consent_submit_disabled .stButton > button {
          border-color: rgba(125, 79, 222, 0.16) !important;
          background: rgba(125, 79, 222, 0.1) !important;
          box-shadow: none !important;
          color: rgba(80, 62, 117, 0.62) !important;
          cursor: not-allowed !important;
          transform: none !important;
        }
        @media (hover: hover) {
          .st-key-cl_consent_submit_link [data-testid="stLinkButton"] > a:hover {
            border-color: #6e3ed2;
            background: #6e3ed2;
            box-shadow: 0 16px 32px rgba(125, 79, 222, 0.3);
            transform: translateY(-1px);
          }
        }
        @media (max-width: 420px) {
          .st-key-cl-consent-shell {
            --cl-consent-gutter: 18px;
            padding-left: var(--cl-consent-gutter);
            padding-right: var(--cl-consent-gutter);
          }
          .cl-consent-page .cl-form-panel {
            padding: max(18px, env(safe-area-inset-top)) 0 var(--cl-consent-panel-bottom) !important;
          }
          .cl-consent-page .cl-form-title {
            font-size: 25px !important;
            line-height: 1.42 !important;
          }
          .cl-consent-page .cl-lead {
            font-size: 14.5px !important;
            line-height: 1.86 !important;
          }
          .st-key-cl-consent-shell .stCheckbox label p {
            line-height: 1.54;
          }
          .st-key-cl-consent-shell .cl-consent-detail-link {
            font-size: 13.5px !important;
          }
          .cl-policy-modal {
            align-items: flex-end;
            padding: 10px 10px max(10px, env(safe-area-inset-bottom));
          }
          .cl-policy-modal__panel {
            width: 100%;
            max-height: 86dvh;
            border-radius: 20px 20px 16px 16px;
          }
          .cl-policy-modal__panel::before {
            display: block;
            width: 38px;
            height: 4px;
            flex: 0 0 auto;
            margin: 8px auto 0;
            border-radius: 999px;
            background: rgba(45, 35, 66, 0.18);
            content: "";
          }
          .cl-policy-modal__header {
            padding: 12px 18px 14px;
          }
          .cl-policy-modal__title {
            font-size: 19px;
            line-height: 1.42;
          }
          .cl-policy-modal__body {
            padding: 16px 18px 18px;
            font-size: 14.5px;
            line-height: 1.72;
          }
          .cl-policy-modal__footer {
            padding: 12px 18px max(16px, env(safe-area-inset-bottom));
          }
          .cl-policy-modal__close-button {
            min-height: 52px;
          }
        }
        </style>
        """
    st.markdown(
        _compact_html(
            styles + consent_styles.replace("__CONSENT_FONT_STACK__", FONT_STACK)
        ),
        unsafe_allow_html=True,
    )

    with st.container(key="cl-consent-shell"):
        if st.button(
            "이전으로",
            key="cl_consent_back",
            type="tertiary",
            icon=":material/arrow_back:",
        ):
            _reset_consent_state()
            st.query_params.clear()
            st.rerun()

        st.markdown(
            _compact_html(
                """
                <main class="cl-login-page cl-consent-page">
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
                </main>
                """
            ),
            unsafe_allow_html=True,
        )

        st.checkbox(
            "필수 항목에 모두 동의합니다.",
            key="cl_consent_all",
            on_change=_sync_all_consent,
        )

        consent_values: dict[str, bool] = {}
        for item in CONSENT_ITEMS:
            checkbox_key = f"cl_consent_{item.key}"
            with st.container(key=f"cl_consent_item_{item.key}"):
                if item.key in _CONSENT_DETAIL_KEYS:
                    label_column, detail_column = st.columns(
                        [4, 1],
                        gap="small",
                        vertical_alignment="top",
                    )
                    with label_column:
                        consent_values[item.key] = st.checkbox(
                            item.label,
                            key=checkbox_key,
                            on_change=_sync_individual_consent,
                        )
                    with detail_column:
                        with st.container(key=f"cl_consent_detail_{item.key}"):
                            st.markdown(
                                _consent_detail_link(item.key),
                                unsafe_allow_html=True,
                            )
                else:
                    consent_values[item.key] = st.checkbox(
                        item.label,
                        key=checkbox_key,
                        on_change=_sync_individual_consent,
                    )

        st.markdown(
            _compact_html(_consent_detail_modals()),
            unsafe_allow_html=True,
        )

        accepted = all_required_accepted(consent_values)
        final_disabled = not accepted or oauth_disabled or not oauth_url

        if final_disabled:
            st.button(
                "동의하고 Instagram으로 계속하기",
                key="cl_consent_submit_disabled",
                disabled=True,
                use_container_width=True,
            )
            if oauth_disabled:
                st.caption("Preview 설정이 없어 화면 확인만 가능합니다.")
        else:
            st.link_button(
                "동의하고 Instagram으로 계속하기",
                oauth_url,
                key="cl_consent_submit_link",
                type="primary",
                use_container_width=True,
            )

def _instagram_cta(safe_oauth_url: str, *, oauth_disabled: bool) -> str:
    icon = _instagram_icon(21)
    arrow = """
      <svg aria-hidden="true" class="cl-button-arrow" viewBox="0 0 20 20" fill="none">
        <path d="m7.5 4.5 5 5.5-5 5.5" stroke="currentColor"
          stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    """

    if oauth_disabled:
        return f"""
            <button
              class="cl-instagram-button"
              type="button"
              aria-disabled="true"
              disabled
            >
              <span class="cl-instagram-icon">{icon}</span>
              <span>Instagram으로 계속하기</span>
              {arrow}
            </button>
        """

    return f"""
            <a
              class="cl-instagram-button"
              href="{safe_oauth_url}"
              target="_self"
            >
              <span class="cl-instagram-icon">{icon}</span>
              <span>Instagram으로 계속하기</span>
              {arrow}
            </a>
    """
