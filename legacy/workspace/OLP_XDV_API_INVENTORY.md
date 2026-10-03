# OLP XDV — Complete API Inventory

*Generated 2026-08-16 from codebase exploration*

---

## Overview

OLP XDV uses a **multi-source architecture with automatic failover** for every data type. Each pipeline data type (fixtures, results, odds, xG, live scores) has multiple redundant providers with circuit-breaker protection and priority-based failover. The architecture is deliberately keyless where possible — paid/quota-limited keys are last-resort fallbacks.

---

## 1. External Provider APIs (Network)

### 1.1 Fixtures Sources (Multi-source: 4 providers)

| Provider | Module | Priority | Auth | Purpose | Key Details |
|----------|--------|----------|------|---------|-------------|
| **TheSportsDB** | `data/thesportsdb_fixtures.py` | 10 (Primary) | Free key (optional test key "123") | Primary fixtures via season feed + eventsday fallback | Verified league IDs in `LEAGUE_IDS` dict; T2 trust tier (single-source) |
| **ESPN Scoreboard** | `data/espn_source.py` | 15 | **Key-free** | Redundancy for continental comps + leagues without TSDB ID | Slugs in `SLUGS` dict (probed live); covers Champions/Europa League, Austrian Bundesliga, HNL |
| **Odds-API Derived** | `pipeline/odds.py` → `fixtures_from_odds()` | 20 | Uses Odds API key | Fixture list derived from priced events (unblocks leagues w/o dedicated fixture source) | 6h cached list; only source for EFL Cup/UCL qualifiers |
| **API-Football** | `data/fixtures_source.py` | 30 (Paid fallback) | **Paid plan required** | Paid-plan fallback when all free sources fail | Free tier capped at 2022-2024; cannot see current season |

**Failover chain:** TheSportsDB → ESPN → Odds-API-derived → API-Football (paid)

---

### 1.2 Historical Results Sources (Multi-source: 4 providers)

| Provider | Module | Priority | Auth | Purpose | Key Details |
|----------|--------|----------|------|---------|-------------|
| **football-data.co.uk** | `data/football_data_source.py` | 10 (Primary) | **Key-free** (CSV downloads) | Primary history for domestic leagues | T1 trust; end-of-season CSVs only |
| **football-data.org** | `data/football_data_org_source.py` | 12 | Free registration (10 req/min, 100/day) | **P0 fix for promoted clubs** — live current-season results | Complements CSV; adds ≥4 matches for promoted clubs |
| **API-Football** | `data/api_football_results.py` | 15 | Free tier (2022-2024 only) / Paid | Fallback for uncovered leagues (HNL, continental) | Cross-league pool builder for continental comps |
| **TheSportsDB** | `data/thesportsdb_fixtures.py` → `load_results()` | 20 | Free key | Last-resort history for leagues neither FD nor API-FB cover | T2 trust; same feed as fixtures |

**Failover chain:** football-data.co.uk → football-data.org → API-Football → TheSportsDB

---

### 1.3 Live Odds Sources (Multi-source: 3 providers)

| Provider | Module | Priority | Auth | Purpose | Key Details |
|----------|--------|----------|------|---------|-------------|
| **The Odds API** | `pipeline/odds.py` | 10 (Primary) | **PAID key primary** (ODDS_API_KEY) + free backups | Live entry prices for CLV gate | UK+EU regions, h2h+totals = 2 credits/league; 500/mo free, paid key removes cap |
| **The Odds API (EU)** | `pipeline/odds.py` | 15 | Same key | Regional redundancy | Different bookmakers, same markets |
| **API-Football Odds** | `data/api_football_odds.py` | 20 | Free tier (100 req/day) | Fallback when Odds API quota exhausted | Same bookmakers, 1X2 + totals only |

**Quota management:** `QUOTA_FLOOR=40` for price pulls; `QUOTA_HARD_FLOOR=1` for fixture capture; auto-switches keys when floor hit; raises `QuotaExhausted` rather than silent failure.

**Bookmaker priority (Architect-reachable only):** bet365 → pinnacle → betfair_ex_uk → williamhill → betfair_ex_eu

---

### 1.4 Expected Goals (xG) Source

| Provider | Module | Priority | Auth | Coverage | Key Details |
|----------|--------|----------|------|----------|-------------|
| **Understat** | `data/xg_source.py` | 10 | **Key-free** | Big-5 leagues + RFPL only | Third independent engine (chance quality); falls back silently when league not covered |

---

### 1.5 Live Scores Sources (Multi-source: 2 providers)

| Provider | Module | Priority | Auth | Purpose | Key Details |
|----------|--------|----------|------|---------|-------------|
| **ESPN Scoreboard** | `data/live_scores.py` | 10 | **Key-free** | Real-time in-play scores for client dashboard | Covers all WHITELISTED_LEAGUES |
| **API-Football** | `data/live_scores.py` | 15 | Paid plan | Fallback for paid-tier live scores | Same endpoint as fixtures |

---

### 1.6 Team Strength Ratings

| Provider | Module | Auth | Coverage | Key Details |
|----------|--------|------|----------|-------------|
| **ClubElo** | `data/clubelo_source.py` | **Key-free** | All clubs (stretch fallback) | ID414: keyless current-season Elo snapshot IS a rating; used when DC + carry-over both fail |

---

### 1.7 SportyBet Nigeria (Booking/Placement)

| Component | Module | Auth | Purpose | Key Details |
|-----------|--------|------|---------|-------------|
| **Requests Client** | `booking/sportybet_client.py` | None (public site) | Read fixtures + odds from sportybet.com/ng | BeautifulSoup parsing; 2s polite delay; caches fixtures 6h, odds 1min |
| **Playwright Cache Builder** | `booking/sportybet_fixtures.py` | None (browser automation) | SPA click-through for leagues requiring JS | Navigates real sidebar; builds JSON cache consumed by bridge |
| **Bridge** | `booking/bridge.py` | N/A | Connects cache to pipeline | Model-key matching (exact → normalized → SportyBet-name); resolves cache aliases |

---

## 2. Internal APIs (Module-to-Module)

### 2.1 Data Layer — Multi-Source Orchestration

| Module | Function | Purpose |
|--------|----------|---------|
| `data/multi_source.py` | `MultiSource.fetch()`, `build_multi_source()` | Generic failover framework: priority-ordered sources, circuit breakers, per-source retries |
| `data/multi_source_concrete.py` | `build_fixtures_multi_source()`, `build_results_multi_source()`, `build_odds_multi_source()`, `build_xg_multi_source()`, `build_current_results_multi_source()`, `build_live_scores_multi_source()` | Concrete factory functions wiring each data type's provider chain |

**Source interface:** `DataSource.fetch(**kwargs) -> dict` with `SourceNoData` exception for honest gaps.

---

### 2.2 Fixtures Pipeline

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `data/thesportsdb_fixtures.py` | `fetch_upcoming()`, `fetch_today()`, `load_results()`, `as_pairs()`, `map_team()` | TheSportsDB fixtures + results; team alias mapping (TEAM_ALIASES per league) |
| `data/espn_source.py` | `fetch_upcoming()`, `as_pairs()` | ESPN scoreboard fixtures; SLUGS map |
| `data/fixtures_source.py` | `fetch_upcoming()`, `as_pairs()` | API-Football fixtures (paid) |
| `pipeline/odds.py` | `fixtures_from_odds()` | Derive fixture list from odds feed |

---

### 2.3 Results Pipeline

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `data/football_data_source.py` | `load_league()`, `load_second_division()` | football-data.co.uk CSVs; UNCOVERED_LEAGUES list |
| `data/football_data_org_source.py` | `fetch_current_season_results()` | Live current-season results for promoted clubs |
| `data/api_football_results.py` | `load_results()`, `is_cross_league()` | API-Football historical; cross-league pool builder |
| `data/thesportsdb_fixtures.py` | `load_results()` | TheSportsDB historical (last resort) |

---

### 2.4 Odds Pipeline

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `pipeline/odds.py` | `fetch_odds()`, `check_quota()`, `index_by_fixture()`, `fixtures_from_odds()`, `map_team()` | The Odds API live prices; quota management; team alias mapping |
| `data/api_football_odds.py` | `fetch_odds()` | API-Football odds fallback |

---

### 2.5 Engine Layer

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `engine/dixon_coles.py` | `fit()`, `predict()`, `predict_adjusted()`, `unrated_reason()`, `content_hash()` | DC model fit + prediction; promoted-club level adjustment |
| `engine/elo.py` | `rate_through()`, `EloModel.probabilities()`, `divergence()` | ID82 Elo second opinion; seeded incremental update |
| `engine/cross_league.py` | `build_pool()`, `fit_cross_league()`, `fit_blend_weight()`, `continental_weight()`, `suggest_aliases()` | Continental pool for uncovered leagues; Elo blend weight optimizer |
| `engine/consensus.py` | `compute_consensus()` | Majority vote across DC/Elo/xG/market |
| `engine/markets.py` | `implied_1x2()`, `model_prob()`, `quote()`, `blend_toward_market()`, `DEPLOYABLE` | Market math: de-vig, EV, MES, deployable market list |
| `engine/mes.py` | `mes_numeric()`, `trigger_price()` | MES (Minimum Edge Score) calculation |
| `engine/recalibration.py` | `apply()`, `calibration_by_market()` | Market-specific calibration adjustments |
| `engine/leagues.py` | `WHITELISTED_LEAGUES`, `is_deploy_eligible()`, `build_deploy_shortlist()` | ID401 unified pool (18 leagues); no softness tiers |

---

### 2.6 Brain (Persistence)

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `brain/store.py` | `Brain.save_model_state()`, `load_model_state()`, `calibration_by_market()`, `log_leg()`, `clv_by_market()` | SQLite-backed content-hash model reuse; leg logging; CLV tracking |
| `clv/clv_logger.py` | `CLVLog.log()`, `settle_pending()` | Per-leg CLV with closing line |

---

### 2.7 Verification & Publish Gate

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `verification/id403.py` | `verify()`, `SourcedDatum`, `Tier` | Multi-factor verification (F2 quorum); T1/T2/T3 trust tiers |
| `webapp/schema.py` | `build_feed_payload()`, `trim_payload()`, `check_client_publish_gate()`, `read_feed()`, `read_booking_codes()` | Board JSON schema; client-safe trimming; publish gate (12/30 legs, mean CLV > 0, ARCHITECT_SIGNOFF=1); booking codes |

---

### 2.8 Output / Rendering

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `output/produce_bet.py` | `render_produce_bet()`, `render_fixture_block()`, `BoardFixture` | Telegram board text rendering |
| `output/telegram_webhook.py` | FastAPI webhook + daemon thread | Telegram bot receiver (Fast200 ack + background processing) |
| `webapp/render_v2.py` | `render_dashboard()` | Web dashboard HTML (pitch-night palette) |
| `webapp/export.py` | `export()` | Static site generator (site/ folder) — one render, two outlets |
| `webapp/produce.py` | `search_fixtures()`, `produce_selection()` | Admin preview with live odds attachment |

---

### 2.9 Orchestration

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `orchestrator.py` | `scan_one_league()`, `run_all_leagues()`, `pull_full_slate_and_team_state()` | Daily pipeline: pull → fit → scan → board → log |
| `run_daily.py` | `run_daily()` | Scheduled entry point (07:00 Task Scheduler) |

---

### 2.10 Booking Integration

| Module | Key Functions | Purpose |
|--------|--------------|---------|
| `booking/bridge.py` | `load_sportybet_fixtures()`, `attach_sportybet_odds()`, `verify_fixture_on_sportybet()`, `get_sportybet_odds_for_leg()`, `sportybet_fixtures_to_pairs()`, `refresh_sportybet_cache()` | Bridge SportyBet cache → pipeline |
| `booking/league_map.py` | `SPORTYBET_LEAGUES`, `resolve_bookmaker()` | OLP league ↔ SportyBet mapping |
| `booking/team_map.py` | `resolve_team()`, `_normalize()` | Team name resolution across sources |
| `booking/sportybet_fixtures.py` | `build_cache()` | Playwright SPA cache builder |

---

## 3. Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DAILY PIPELINE (orchestrator.py)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FIXTURES                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ MultiSource (data/multi_source_concrete.py)                          │  │
│  │   TheSportsDB (T2) → ESPN (key-free) → Odds-derived → API-FB (paid)  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  HISTORICAL RESULTS                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ MultiSource                                                          │  │
│  │   football-data.co.uk (T1) → football-data.org (promoted fix)       │  │
│  │   → API-Football → TheSportsDB (T2)                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  MODEL FIT (Brain: content-hash reuse)                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Dixon-Coles (primary)                                                │  │
│  │   + Carry-over (prior season, promoted clubs)                       │  │
│  │   + ClubElo stretch fallback (ID414)                                │  │
│  │ Elo (second opinion, seeded incremental)                            │  │
│  │ xG / Understat (Big-5 only, third opinion)                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  PREDICTION & VERIFICATION                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ predict() → verification (ID403) → consensus → MES/EV               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  LIVE ODDS (for EV/CLV)                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ The Odds API (PAID primary) → API-Football fallback                 │  │
│  │ Bookmaker priority: bet365 → pinnacle → betfair_ex_uk → ...         │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  BOARD OUTPUT                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ render_produce_bet() → board_<date>.json                            │  │
│  │       │                                                              │  │
│  │       ├─→ Telegram bot (output/telegram_webhook.py)                 │  │
│  │       │                                                              │  │
│  │       └─→ Web feed (webapp/schema.build_feed_payload →              │  │
│  │            render_v2.render_dashboard → webapp/export.py → site/)   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  PUBLISH GATE (webapp/schema.py)                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ check_client_publish_gate(): ≥30 legs logged + mean CLV > 0%        │  │
│  │   + ARCHITECT_SIGNOFF=1 (env)                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Architectural Principles

| Principle | Implementation |
|-----------|----------------|
| **HR35 — Honest NO DATA** | Every gap returns `SourceNoData` / `NO DATA — PENDING`; never guessed |
| **Multi-source failover** | Every data type has priority chain with circuit breakers |
| **Content-hash model reuse** | Brain caches fits by content hash; identical data = identical params (BUG6 guarantee) |
| **One render, two outlets** | Telegram board text = raw board; Web feed = `build_feed_payload(raw)` → same content |
| **Auto-feed = auto-publish** | Daily board_<date>.json is single source of truth; no Approve gate |
| **Architect capital authority** | Phase 3 live but `config.assert_paper_only()` hard-fails; booking never clicks Place Bet |
| **ID401 unified pool** | 18 leagues, ONE combined board, no softness tiers, no deploy cap |
| **ID405 overridden** | All markets open (1X2, O/U 1.5/2.5, DC, BTTS); away wins may be recommended |

---

## 5. Environment Variables Required

| Variable | Purpose | Required |
|----------|---------|----------|
| `ODDS_API_KEY` | **Primary (PAID) The Odds API key** | Yes |
| `ODDS_API_KEY_BACKUP` | Free backup key (monthly reset) | Optional |
| `ODDS_API_KEY_TERTIARY` | Third backup key | Optional |
| `THESPORTSDB_KEY` | TheSportsDB personal key (avoids truncated test key) | Recommended |
| `FOOTBALL_DATA_ORG_KEY` | football-data.org free registration key | Recommended |
| `API_FOOTBALL_KEY` | API-Football key (paid for current season) | Optional |
| `ARCHITECT_SIGNOFF` | Publish gate flag ("1" to enable) | For Phase 3 |
| `PHASE_LABEL` | "PHASE 2 · PAPER" or "PHASE 3 · LIVE" | Set in config |

---

## 6. Rate Limits & Quota Management

| API | Limit | Management |
|-----|-------|------------|
| The Odds API (free) | 500 req/mo | `QUOTA_FLOOR=40`, `QUOTA_HARD_FLOOR=1`, key rotation |
| The Odds API (paid) | Per plan | Primary key; no practical limit |
| football-data.org | 10 req/min, 100/day | Cached; only for promoted-club gaps |
| API-Football (free) | 100 req/day, 2022-2024 only | Fallback only |
| TheSportsDB | Shared test key truncated | Personal key recommended |
| ESPN | Unlimited (key-free) | 6h cache per (league, day) |
| Understat | Unlimited (key-free) | Big-5 only; cached |
| ClubElo | Unlimited (key-free) | Stretch fallback only |
| SportyBet | No official limit | 2s polite delay; 6h fixture cache, 1min odds cache |

---

## 7. Trust Tiers (ID403 Verification)

| Tier | Label | Sources | Use Case |
|------|-------|---------|----------|
| **T1** | ✓ VERIFIED | football-data.co.uk (results), The Odds API (odds) | Calibration-grade; F2 quorum possible |
| **T2** | ○ SINGLE-SOURCE | TheSportsDB (fixtures/results), API-Football (free tier) | Board reference scan only |
| **T3** | ⚠ UNVERIFIED | Derived/estimated | Display only |

**F2 Quorum:** Requires TWO independent data *types* (e.g., results + odds), not two providers of the same type.

---

*End of inventory. For implementation details on any specific module, see the source files listed above.*