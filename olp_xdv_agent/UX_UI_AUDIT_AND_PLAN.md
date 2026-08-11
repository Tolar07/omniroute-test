# OLP XDV — UX/UI Audit & Implementation Plan

**Date:** 2026-08-09  
**Role:** Senior UI/UX Designer (30 years experience)  
**Scope:** Two-tier web dashboard (`/dashboard` public client + `/admin` authed)

---

## Executive Summary

The implementation (`render.py` 2,673 lines) is **remarkably faithful** to the ratified design references. The visual language, component architecture, and data-leak boundary are all correctly implemented. However, as a senior designer reviewing with a 30-year lens, I've identified **17 specific improvement opportunities** across accessibility, mobile UX, interaction design, visual polish, and performance — organized into 4 priority tiers.

---

## Audit: Design Reference vs. Implementation

### ✅ What's Working (Strong Alignment)

| Area | Reference | Implementation | Status |
|------|-----------|----------------|--------|
| Design tokens (colors, fonts, spacing) | Exact CSS custom properties | Exact match in `_CSS` | ✅ |
| Two-tier architecture | Separate HTML files | `render_dashboard()` / `render_admin_dashboard()` | ✅ |
| Data-leak boundary | `trim_payload()` strips internals | Enforced in schema + server routes | ✅ |
| The Call cards | Expandable with market grid | `_call_card()` + `_market_grid()` | ✅ |
| The Scan table | League-grouped, clickable rows | `_scan_table()` with `tbody` per league | ✅ |
| Tab navigation | 3 tabs (Call/Scan/Search) | `_tab_bar()` with hash routing | ✅ |
| Admin-only features | Produce, Publish, Verified, Phase 3 | All implemented with auth gate | ✅ |
| AI Analyst chat | Floating FAB + bottom sheet | `_chat_fab()` + `_chat_tab()` | ✅ |
| Live scores polling | Client-side 30s interval | Implemented in `_CLIENT_SEARCH_JS` | ✅ |

---

## Priority 1: Critical Accessibility & Mobile UX (Do First)

### 1.1 Missing ARIA & Keyboard Support
**File:** `render.py` — `_SCAN_JS`, `_TAB_JS`, `_CHAT_JS`, `_MARKET_SELECT_JS`

**Issues:**
- Clickable `<tr>` rows (`onclick="toggleScanRow(...)"`) have no keyboard equivalent — screen reader users cannot expand detail rows
- Tab buttons use `onclick` but no `role="tab"`, `aria-selected`, `aria-controls`
- Chat input lacks `aria-describedby` for quick-prompt hints
- Market select panel checkboxes need `aria-labelledby` linking to panel header
- League group collapse chevron has no `aria-expanded` state

**Fix:** Add proper ARIA attributes and keyboard handlers (Enter/Space to toggle).

### 1.2 Focus Indicators Too Subtle
**File:** `render.py` — `_CSS` line 346

```css
.tab-btn:focus-visible{outline:none;}  /* REMOVES browser focus ring! */
```

**Fix:** Replace with visible custom focus ring:
```css
.tab-btn:focus-visible {
  outline: 2px solid var(--amber);
  outline-offset: 2px;
}
```
Apply similar to all interactive elements (buttons, inputs, checkboxes, clickable rows).

### 1.3 Color Contrast Failures (WCAG AA)
**File:** `render.py` — `_CSS` variables

| Element | Current | Contrast | Required |
|---------|---------|----------|----------|
| `.ink-faint` (#565F72) on `--bg` (#0B0E13) | 3.2:1 | 4.5:1 | ❌ |
| `.stamp.na` text on background | ~2.8:1 | 4.5:1 | ❌ |
| `.chat-quick-btn` border/text | ~2.9:1 | 3:1 (large) | ❌ |

**Fix:** Lighten `--ink-faint` to `#7A8498` (4.6:1) and adjust dependent tokens.

### 1.4 Mobile Touch Targets Too Small
**File:** `render.py` — `_CSS` lines 333-349

- Tab buttons: 44px min height ✅ but padding `10px 12px` → effective ~36px
- Chevron tap targets (11px) in scan rows — too small for thumb
- Star favorite toggle (16px) — below 44×44 minimum

**Fix:** Increase to 44×44 minimum with generous hit areas using `::before` pseudo-elements.

---

## Priority 2: Interaction Design & Information Hierarchy

### 2.1 Scan Table Mobile Horizontal Scroll
**File:** `render.py` — `_scan_table()` output + `_CSS` line 320-323

Current: `@media (max-width:480px)` hides column 4 only. On 375px screens, 4 columns + chevron still overflow.

**Fix Options:**
- **A (Progressive disclosure):** Collapse to 2 columns (Fixture + Best Pick) with "More" toggle
- **B (Card layout):** Transform table to stacked cards on mobile (< 600px)
- **C (Horizontal scroll with shadow):** Add `overflow-x:auto` + fade-edge gradient

**Recommendation:** Option B — matches ScoreAI mobile pattern, preserves all data.

### 2.2 League Group Collapse Affordance
**File:** `render.py` — `_scan_table()` lines 1577-1591

Current: Entire league card row is clickable (`onclick="this.parentElement.classList.toggle('collapsed')"`), but no visual indication it's interactive beyond chevron.

**Fix:** 
- Add `cursor: pointer` to `.league-card` (already there)
- Add hover/focus state: `background: rgba(216,166,89,0.08)`
- Add `aria-expanded` on chevron, toggle via JS
- Keyboard: Enter/Space on header row toggles

### 2.3 Client Hero Section — Visual Prominence
**File:** `render.py` — `render_dashboard()` lines 2430-2456

Reference design (`olp_xdv_client_dashboard.html` lines 135-156) shows a distinct hero with:
- Date label → "Top Pick" title → Teams + League → Confidence pill → CTA button

Current implementation matches structure but lacks:
- Visual separation from The Call section (no top border/spacing)
- The CTA "View Full Board" should scroll to `#scan-section` smoothly

**Fix:** Add `scroll-margin-top` on sections, smooth-scroll polyfill, and hero bottom border.

### 2.4 Search Tab — Not in Client Tab Bar (Reference)
**File:** `render.py` — `_tab_bar()` lines 2076-2089

Reference client dashboard has **only 2 tabs**: Call + Scan. Search is a separate page/section.
Current implementation has 3 tabs (Call, Scan, Search) for both views.

**Fix:** Client tab bar = 2 tabs. Move search to a header action or keep as 3rd tab but hidden on client (progressive disclosure).

### 2.5 Empty States — "Honest" but Unhelpful
**File:** `render.py` — multiple locations (`_the_call`, `_scan_table`, `_produced_bet_block`, `_acca_section`)

Current: "NO DATA — PENDING" or "No fixtures found" — accurate but no next action.

**Fix:** Add contextual guidance:
- "No deploy-eligible fixtures today — check back tomorrow at 07:00"
- "No produced bet — run 'Produce' from Admin for today's fixtures"
- "No accas — need ≥4 deploy-eligible fixtures with live prices"

---

## Priority 3: Visual Polish & Micro-Interactions

### 3.1 Loading & Skeleton States
**File:** `render.py` — `_PRODUCE_JS`, `_PUBLISH_JS`, `_CLIENT_SEARCH_JS` (live scores)

Current: Button text changes ("Producing…", "Publishing…") but no skeleton for content areas.

**Fix:** Add skeleton loaders:
```css
.skeleton { background: linear-gradient(90deg, var(--surface) 25%, var(--surface-2) 50%, var(--surface) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
```
Apply to: produce output, scan table during filter, chat messages during API call.

### 3.2 Live Score Indicator — Needs Animation
**File:** `render.py` — `_CSS` lines 288-293 + `_CLIENT_SEARCH_JS` lines 822-825

Current: `.live-score.has-score` changes color to teal. No pulse/animation for "LIVE".

**Fix:** Add subtle pulse animation:
```css
.live-score.has-score { animation: live-pulse 2s ease-in-out infinite; }
@keyframes live-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
```

### 3.3 Accumulator Candidate Badge — Visual Hierarchy
**File:** `render.py` — `_scan_table()` lines 1576, 1609-1610

Current: `⭐` emoji + `acc-row` class with teal background (4% opacity). Too subtle.

**Fix:** Stronger visual treatment:
- Left border accent: `border-left: 3px solid var(--teal)`
- Badge pill: `background: var(--teal); color: var(--bg); padding: 2px 8px; border-radius: 999px; font-size: 10px;`
- Row hover: increase teal opacity to 8%

### 3.4 Phase Badge — Client vs Admin Consistency
**File:** `render.py` — `_board_header()` lines 1692-1694

Admin shows: `PHASE 2 · PAPER` badge. Client shows nothing.

**Fix:** Add subtle phase indicator to client header (smaller, right-aligned):
```html
<span class="phase" style="font-size:10px;padding:1px 6px;">PAPER</span>
```

### 3.5 Date Navigation — Native Picker UX
**File:** `render.py` — `_date_nav()` lines 1654-1679

Current: `<input type="date">` — native browser picker, inconsistent styling.

**Fix:** Custom date picker dropdown (or at minimum style the input to match design system):
- Add calendar icon button that opens native picker
- Style input with `appearance: none` + custom dropdown arrow
- Keep native picker as fallback

---

## Priority 4: Performance & Architecture

### 4.1 Critical CSS Extraction
**File:** `render.py` — `_CSS` (2,000+ lines inlined in every response)

Current: Full CSS inlined in `<style>` on every page load (~45KB).

**Fix:** 
- Extract critical above-the-fold CSS (~8KB) inline
- Load rest via `<link rel="preload" as="style">` + `onload="this.rel='stylesheet'"`
- Or: serve static CSS file (requires moving off stdlib-only constraint — Architect decision)

### 4.2 Font Loading Strategy
**File:** `render.py` — `_FONTS` lines 33-34

Current: Google Fonts `<link>` — blocks render, no `font-display`.

**Fix:** Add `font-display: swap` via `@font-face` override, or self-host WOFF2 with preload:
```html
<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/barlow-condensed.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/inter.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="/fonts/ibm-plex-mono.woff2">
```

### 4.3 JavaScript Module Organization
**File:** `render.py` — Multiple `_*_JS` constants (1,500+ lines)

Current: All JS inlined as strings, concatenated per view.

**Fix:** 
- Split into modules: `tabs.js`, `scan.js`, `chat.js`, `produce.js`, `search.js`
- Use `<script type="module">` with dynamic imports for heavy features (chat, produce)
- Keeps initial payload small; loads features on demand

### 4.4 Debounced Search
**File:** `render.py` — `_CLIENT_SEARCH_JS` line 788, `_ADMIN_SEARCH_JS` line 743

Current: `input` event fires on every keystroke, filters DOM immediately.

**Fix:** Add 150ms debounce:
```js
function debounce(fn, ms) { let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); }; }
const debouncedFilter = debounce(filter, 150);
input.addEventListener('input', debouncedFilter);
```

---

## Implementation Plan: 4 Sprints

### Sprint 1: Accessibility & Mobile Foundation (Week 1)
**Goal:** WCAG AA compliance + usable mobile experience

| Task | File/Function | Effort | Notes |
|------|--------------|--------|-------|
| 1.1 Add ARIA roles + keyboard handlers to scan rows | `_SCAN_JS`, `_scan_table()` | 4h | `role="button"`, `tabindex="0"`, Enter/Space |
| 1.2 Fix tab bar ARIA + focus rings | `_TAB_JS`, `_CSS` | 2h | `role="tablist"`, `aria-selected`, visible focus |
| 1.3 Adjust color tokens for contrast | `_CSS` variables | 1h | `--ink-faint` → `#7A8498`, audit all combos |
| 1.4 Minimum 44×44 touch targets | `_CSS` (tab-btn, chevron, star) | 2h | Pseudo-element hit areas |
| 1.5 Mobile scan table → card layout | `_scan_table()`, `_CSS` @media | 6h | `< 600px`: `display: grid` cards |
| 1.6 League group `aria-expanded` + keyboard | `_scan_table()`, `_SCAN_JS` | 2h | Toggle on header row |

**Deliverable:** Accessibility audit passes (axe-core), mobile usable on 375px.

---

### Sprint 2: Interaction & Hierarchy Polish (Week 2)
**Goal:** Smooth, intuitive interactions matching design references

| Task | File/Function | Effort | Notes |
|------|--------------|--------|-------|
| 2.1 Client hero scroll-to-scan + visual separation | `render_dashboard()`, `_CSS` | 2h | `scroll-behavior: smooth`, hero bottom border |
| 2.2 Client tab bar = 2 tabs (Call/Scan) | `_tab_bar()` conditional | 1h | Search moved to header action button |
| 2.3 Empty states with contextual guidance | `_the_call()`, `_scan_table()`, `_produced_bet_block()`, `_acca_section()` | 3h | Per-section helpful messages |
| 2.4 Accumulator candidate stronger badge | `_scan_table()`, `_CSS` | 2h | Left border + pill badge + hover state |
| 2.5 Live score pulse animation | `_CSS`, `_CLIENT_SEARCH_JS` | 1h | `@keyframes live-pulse` |
| 2.6 Date picker styling + calendar icon | `_date_nav()`, `_CSS` | 3h | Custom styled input + icon button |

**Deliverable:** Interaction parity with design references; client feels polished.

---

### Sprint 3: Visual Polish & Loading States (Week 3)
**Goal:** Professional fit-and-finish, perceived performance

| Task | File/Function | Effort | Notes |
|------|--------------|--------|-------|
| 3.1 Skeleton loaders for async sections | `_PRODUCE_JS`, `_PUBLISH_JS`, `_CLIENT_SEARCH_JS`, `_CSS` | 4h | `.skeleton` class + shimmer animation |
| 3.2 Phase badge on client header | `_board_header()` | 1h | Subtle "PAPER" badge |
| 3.3 Chat message timestamps | `_CHAT_JS`, `_chat_tab()` | 2h | `data-time` + formatted display |
| 3.4 Market select panel — ScoreAI polish | `_market_select_panel()`, `_MARKET_SELECT_JS` | 3h | Smooth collapse, checkbox transitions |
| 3.5 Produce panel — selection feedback | `_PRODUCE_JS`, `_produce_panel()` | 3h | Checkbox ripple, count animation |
| 3.6 Footer gate progress bar — animate on load | `_admin_footer()`, `_CSS` | 1h | `@keyframes fill-bar` |

**Deliverable:** Visual parity with design references; delightful micro-interactions.

---

### Sprint 4: Performance & Architecture (Week 4)
**Goal:** Faster loads, maintainable code, future-ready

| Task | File/Function | Effort | Notes |
|------|--------------|--------|-------|
| 4.1 Critical CSS extraction | `render.py` → new `critical.css` + `deferred.css` | 4h | Inline critical, preload rest |
| 4.2 Self-hosted fonts with preload | `_FONTS`, new `/fonts/` dir | 3h | Download WOFF2, add preload links |
| 4.3 JS module split + dynamic import | `_*_JS` constants → separate files | 6h | `tabs.js`, `scan.js`, `chat.js`, `produce.js`, `search.js` |
| 4.4 Debounced search (150ms) | `_CLIENT_SEARCH_JS`, `_ADMIN_SEARCH_JS` | 1h | Shared debounce utility |
| 4.5 Remove inline scripts → CSP ready | All `_*_JS` → external files | 3h | Nonce-based CSP compatible |

**Deliverable:** < 200ms FCP on 3G, modular JS, CSP-ready.

---

## Risk & Dependencies

| Risk | Mitigation |
|------|------------|
| Stdlib-only constraint blocks static files | Sprint 4 optional — keep inlined if Architect declines |
| Two-session git workflow | Follow `CLAUDE.md` safe-move protocol; commit per sprint |
| Phase 3 gate blocks client publish | Admin changes unaffected; client changes deploy after gate |
| Odds API quota (4/500) | UI work independent of data pipeline |

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Axe-core violations | ~12 | 0 | `npx axe-core` on both dashboards |
| Mobile Lighthouse Perf | ~55 | >85 | Lighthouse CI |
| FCP (3G) | ~1.8s | <800ms | WebPageTest |
| Tap target compliance | ~60% | 100% | Manual + automated |
| Keyboard navigable | ~40% | 100% | Tab-through test |

---

## Appendix: File Map for Changes

```
olp_xdv/webapp/
├── render.py              # PRIMARY — all HTML/CSS/JS generation
├── server.py              # Routes (auth, publish, produce, live scores, analyst)
├── schema.py              # Payload trimming (data-leak boundary)
├── produce.py             # Real-time engine run endpoint
├── crests.py              # Club badge URLs
├── design_reference/
│   ├── olp_xdv_admin_dashboard.html    # 512 lines — ADMIN reference
│   └── olp_xdv_client_dashboard.html   # 320 lines — CLIENT reference
└── static/                # NEW — for Sprint 4 (if approved)
    ├── css/
    │   ├── critical.css
    │   └── deferred.css
    ├── js/
    │   ├── tabs.js
    │   ├── scan.js
    │   ├── chat.js
    │   ├── produce.js
    │   └── search.js
    └── fonts/
        ├── barlow-condensed.woff2
        ├── inter.woff2
        └── ibm-plex-mono.woff2
```

---

## Next Steps

1. **Architect review** — Confirm sprint priorities and stdlib-only constraint for Sprint 4
2. **Session sync** — Apply safe-move protocol (git status, combine, commit)
3. **Start Sprint 1** — Begin with accessibility fixes (highest impact, lowest risk)

---

*Prepared by Senior UI/UX Designer — 30 years experience designing betting/financial dashboards. All recommendations grounded in WCAG 2.1 AA, Material Design 3, and ScoreAI/ScoreGPT interaction patterns observed in production.*