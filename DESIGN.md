# Design

## Source of truth

- Status: Active
- Last refreshed: 2026-08-27
- Primary product surfaces: `/Login` introduction, full-page consent, Instagram OAuth handoff
- Evidence reviewed: `pyproject.toml`, `src/ui/celeblife_login.py`, `src/consent.py`, `pages/2_🔐_Login.py`, `pages/4_🔒_Privacy.py`, `tests/test_login_ui_integration.py`, `.omx/artifacts/visual-ralph/instagram-consent/reference.png`, `.omx/artifacts/visual-ralph/instagram-consent/privacy-v3-top-390.png`, and `.omx/artifacts/visual-ralph/instagram-consent/privacy-v3-bottom-390.png`

## Brand

- Personality: calm, capable, concise, and creator-first
- Trust signals: Meta official login method, no Instagram password storage, explicit consent before redirect
- Avoid: inflated promises, long marketing copy, dense legal text before the user asks to expand it

## Product goals

- Goals: explain the value quickly, collect three visible required consents, and start OAuth only from the final consent CTA
- Non-goals: production legal approval, automated data collection during Preview, or redesigning authenticated screens
- Success signals: first CTA always opens consent; all three visible checks are required; back clears state including any legacy hidden consent key; the final CTA is reachable and readable on a phone

## Personas and jobs

- Primary personas: creators and celebrity commerce partners connecting an Instagram business account
- User jobs: understand why connection is useful, trust the handoff, review required terms, and connect without confusion
- Key contexts of use: mobile browser first, short attention span, potentially interrupted OAuth flow

## Information architecture

- Primary navigation: linear onboarding with an explicit back action
- Core routes/screens: `/Login` intro → `/auth/instagram/start` browser binding → `/Login?step=consent` → Instagram OAuth → `/auth/callback` → `/Dashboard`
- Content hierarchy: hook → one-line explanation → trust proof → local continue CTA; then CelebLife brand mark → consent heading → all-agree → three required rows, with detail buttons only on terms/privacy → final CTA. The consent screen does not show the `CELEBLIFE ONBOARDING` eyebrow below the logo.

## Design principles

- Consent cannot be implied or skipped; the introductory CTA is always same-origin and the OAuth handoff is bound to the browser that opened the consent screen.
- Mobile readability wins over fitting everything above the fold; legal detail opens in dismissible modals so the page itself stays short.
- Trust copy should explain real boundaries without claiming partnership or guaranteed results.
- Tradeoff: the consent page scrolls when needed so labels, line height, and touch targets remain comfortable.

## Visual language

- Color: existing CelebLife purple (`#7d4fde`) on white with restrained lavender surfaces; consent checkboxes and the final Instagram CTA use this purple for selected/active states, with lavender disabled states.
- Typography: existing Pretendard-first Korean font stack; the main hook is one line when it fits, otherwise it may wrap only after the comma so `선택의 기준을 만듭니다.` moves as a whole.
- Spacing/layout rhythm: consent-shell owns the 18-20px outer gutter, title-to-lead and lead-to-all-agree block gaps stay at 16px, consent items keep a 48px row step with 44px minimum touch targets, and the 60px primary action remains distinct
- Shape/radius/elevation: reuse the current rounded badges/buttons; consent content stays flat and focused
- Motion: no required motion; honor reduced-motion preferences
- Imagery/iconography: reuse existing CelebLife and Instagram assets from `assets/login/`; the consent page keeps the CelebLife brand mark visible at every breakpoint and omits the onboarding eyebrow to reduce top clutter

## Components

- Existing components to reuse: login illustration, trust badge, Instagram CTA styling, and Streamlit checkboxes
- New/changed components: full-page consent shell, same-document CSS `:target` policy popups for terms/privacy detail, compact detail triggers on legal rows only, all-agree synchronization, reset-on-back behavior, purple Streamlit final OAuth CTA, selected checkbox styling scoped to the consent shell, hidden Instagram-permission audit derivation from the accepted privacy/data-use handoff
- Variants and states: intro, consent incomplete, consent complete, credentialless Preview disabled, callback error, logged in
- Token/component ownership: `src/ui/celeblife_login.py`

## Policy detail modal contract

- Purpose: turn long legal copy into a readable mobile document viewer, not a raw paragraph dump. The exact legal wording in `src/consent.py` must remain unchanged; only HTML grouping, class names, spacing, and visual hierarchy may change.
- Surface: the existing same-document `:target` dialog pattern stays in place; do not add JavaScript, a frontend framework, a route transition, or a dependency.
- Modal frame: on phones up to 420px, render as a bottom sheet with `padding: 10px`, `width: 100%`, `max-height: 86dvh`, `border-radius: 20px 20px 16px 16px`, and a subtle 4px drag/scroll affordance above the title. On desktop/tablet, center the dialog at `width: min(100%, 640px)` and `max-height: min(82dvh, 760px)`.
- Header hierarchy: sticky modal header at the top of the scroll container. It should contain a small trust eyebrow (`필수 안내` or equivalent), the policy title (`개인정보 수집·이용` / `서비스 이용약관`), and for privacy only a metadata line `최종 업데이트: 2026년 8월 26일`. The close icon stays 40x40px, aligned to the optical center of the title block, with a visible focus ring.
- Document title treatment: inside the body, `셀럽라이프 개인정보처리방침` is the document title, not an ordinary paragraph. Render it as a compact heading row or title block with 18px mobile font, 800 weight, 1.42 line-height, and 0 bottom margin beyond the document-title block.
- Intro treatment: the two opening privacy-policy sentences form one intro block with a light lavender border/background, 14.5px mobile font, 1.72 line-height, 14px vertical padding, and 14px radius. It should feel like a summary note, not a separate card-heavy layout.
- Numbered sections: lines matching `1. ...` through `11. ...` start section groups. Render each section heading with a small purple number pill or left accent, 15px mobile font, 780 weight, 1.45 line-height, 22px top margin except the first section, and 10px bottom margin. Section headings must visually break the long document during fast scrolling.
- Subsection headings: standalone labels such as `회원 정보`, `Instagram 계정 정보`, `Instagram 인사이트 및 콘텐츠 성과정보`, `오디언스 통계정보`, `인증정보`, `Instagram에서 앱 연결 해제`, and `이메일을 통한 삭제 요청` render as subsection headings with 14px font, 740 weight, 14px top margin, and 6px bottom margin.
- List items: short data lines under a subsection or purpose paragraph render as list rows, not paragraphs separated by large blank space. Use 8px vertical gap, 1.58 line-height, and a restrained bullet/check marker. Examples include `이름`, `이메일 주소`, `조회수`, `Supabase: 데이터베이스 및 서비스 데이터 저장·관리`, and `회원 정보: 회원 탈퇴 시까지`.
- Body paragraphs: normal explanatory sentences use 14.5px mobile font, 1.72 line-height, `word-break: keep-all`, and 8-10px paragraph gap. Do not use the current 2.0 line-height for every line; it makes list content look loose.
- Contact fields: company/contact lines in section 10 may render as compact key-value rows, but labels and values must remain text-equivalent and selectable. The email may be a `mailto:` link only if it preserves the visible address.
- Footer controls: keep a sticky bottom close area inside the panel with a 52px primary close button on mobile and 48px on desktop. Add a subtle top border or shadow so users can tell the document scrolls behind it.
- Scroll affordance: the body should visibly sit between sticky header and sticky footer. The top/bottom captures at 390px must show that the user is inside a document, with section hierarchy visible at the top and a polished ending plus close control at the bottom.
- Terms modal: may be simpler than the privacy modal, but it still uses the same header/footer frame and readable paragraph styling. It must not look like a browser error page, Streamlit route, or unstyled markdown.
- Age consent: no detail trigger, no modal, and no hidden age-policy popup.

## Accessibility

- Target standard: practical WCAG 2.1 AA behavior for this Preview surface
- Keyboard/focus behavior: native Streamlit controls; visible focus on custom CTAs; terms/privacy triggers expose `aria-haspopup`/`aria-controls`, target a focusable dialog, and close back to the originating trigger without a server rerun; close icon, backdrop, and bottom close button must all return to the originating trigger anchor; age confirmation is a checkbox-only row
- Contrast/readability: dark text on white; consent title around 1.4, lead around 1.86 on mobile, checkbox labels around 1.54 on mobile, policy body paragraphs around 1.72 on mobile, policy lists around 1.58, and section headings around 1.45
- Screen-reader semantics: one level-one heading per state; modal has `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `aria-describedby` pointing at the document body or intro; visible control labels; decorative imagery hidden where appropriate
- Reduced motion and sensory considerations: existing reduced-motion media query remains active

## Responsive behavior

- Supported breakpoints/devices: phone baseline from 360px; short/landscape phone rules; desktop from 961px
- Layout adaptations: split illustration/form only on the intro desktop view; consent remains a centered single-column full page at every width; policy dialogs are bottom sheets on phones and centered document dialogs from tablet widths upward
- Touch/hover differences: compact minimum 44px consent rows, right-aligned 44px detail triggers on terms/privacy aligned to the first checkbox-label line, full-width age checkbox row, and 60px primary actions; hover styling only on hover-capable devices

## Interaction states

- Loading: existing spinner during callback processing
- Empty: unchecked consent with disabled final CTA
- Error: sanitized message and retry into the consent step
- Success: authenticated session then Dashboard redirect or legacy success state
- Disabled: credentialless Preview renders the flow but cannot generate or expose an OAuth URL
- Offline/slow network: no special state beyond native navigation/callback feedback in this Preview

## Content voice

- Tone: direct, reassuring, and free of hype
- Terminology: use `Instagram`, `연결`, `동의`, and `채널 데이터` consistently
- Microcopy rules: main hook is `반응을 읽고, 선택의 기준을 만듭니다.`; supporting copy is one sentence; legal versions are explicitly Preview drafts

## Implementation constraints

- Framework/styling system: no `package.json`; the UI is Streamlit 1.61 with scoped HTML/CSS in `src/ui/celeblife_login.py`; policy popups use same-document anchors and CSS `:target` so Preview detail clicks do not require a Streamlit rerun
- Design-token constraints: extend the existing `--cl-*` variables; do not add a new styling dependency
- Performance constraints: embed only existing small login assets; no client-side framework addition
- Compatibility constraints: preserve the legacy Streamlit callback while Vercel uses `/auth/callback`; keep `main` and production resources untouched during Preview work
- Test/screenshot expectations: AppTest contract suite covering zero consent expanders, no age detail trigger/modal, two anchor-driven popup contracts for terms/privacy, structured policy classes for document title/intro/sections/lists/footer, plus 360/390px intro, consent, popup-detail top and bottom captures and a desktop consent overlap check

## Policy modal acceptance criteria

- Privacy modal renders these distinct classes or equivalent stable hooks: document title, metadata, intro block, numbered section heading, subsection heading, list row, body paragraph, sticky header, sticky footer, close icon, and close button.
- The privacy text content remains byte-for-byte equivalent after stripping HTML tags and normalizing whitespace; no legal sentence is summarized, omitted, reordered, or rewritten.
- At 390px width, the top capture shows the modal title, update date, intro block, and the first numbered section without cramped overlap; the bottom capture shows section 10/11 or `부칙` content plus a sticky close control that does not cover text.
- All tappable controls in the modal are at least 40x40px visually and 44x44px hit area where possible.
- The age row still has no `상세 보기` link and no `cl-consent-modal-age-confirmed` output.
- Detail links do not navigate to a Vercel/Streamlit route; they open same-document dialogs via `href="#cl-consent-modal-..."`.

## Open questions

- [ ] Legal owner to approve terms, privacy, retention, and permissions wording before Production
- [ ] Product owner to decide whether optional marketing consent is needed in a later version
- [ ] Live Preview owner to verify Meta test-account OAuth and the separate Preview Supabase transaction
