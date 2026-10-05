# Workspace Synchronized State Ledger

## Active Locks

- None

## Recent Workspace Changes

- 2026-08-20: Initialized shared session state ledger.
- 2026-08-20: Submodule `olp_xdv_agent/olp_xdv` has uncommitted changes (new commits, modified content, untracked content).
- 2026-08-20: New untracked files: `CLAUDE.md`, `docs/` directory.
- 2026-08-20 17:03: Supervisor Agent updated — added multi-session sync protocol ownership to `.claude/agents/olp-xdv-supervisor.md`
- 2026-08-20 17:03: Sync protocol deployed — created `CLAUDE.md` (root) and `docs/STATE.md` for autonomous multi-session coordination
- 2026-08-20 17:03: BUG-20260819-001 (SPL referee) resolved — PARTIAL acceptance per HR35 documented
- 2026-08-20 17:03: BUG-20260819-003 (Agent 3→4 latency) resolved — preload imports in `olp_xdv_pipeline.py`
- 2026-08-20 17:03: Commit `fc97790` — fix: SPL referee PARTIAL acceptance + Agent 3→4 latency fix

- 2026-10-03: **All OLP XDV copies merged into one line** — Tolar07/framework PR #47 (`claude/unify-lineages`): cloud `main` + laptop `elo-persistence` (incl. this workspace's old `93c9337`) + PR #1 + PR #6 + `olpxdv_framework/` (now `legacy/olpxdv_framework/` in the framework repo, removed from this root). Main's code wins every shared file; details in `docs/LINEAGE_MERGE_2026-10-03.md` in that repo.
- 2026-10-03: Submodule `olp_xdv_agent/olp_xdv` → `d435f2d` (framework `main` after PR #47 merged 2026-10-03; laptop test suite red until laptop features are ported in follow-up PRs).
- 2026-10-03: **Laptop nightly loop retired** — `run_daily.bat` now logs a line and exits 0; the board runs only in GitHub Actions `daily.yml`. Disable the "OLP XDV" Windows scheduled task when convenient.
- 2026-10-03: **omniroute-test branches consolidated** onto `claude/eloquent-noether-8b69az`: `fix/pipeline-restore-and-fixture-verification`, `claude/charming-allen-fzjxwr`, `claude/zen-cerf-o0b7b7`, `ccr-51c326b5-vl6yc2` (submodule kept at framework `main` `d435f2d`); `claude/fix-scheduler-path` recorded as superseded. `.claude/scheduled_tasks.json` is empty, and `scripts/daily_olp_xdv_runner.sh` + `scripts/renew_automation.sh` now log and exit 0 so nothing re-creates the laptop 10pm job.
- 2026-10-03: Windows task **"OLP XDV Daily Board"** (`run_daily.bat`, 22:00) **disabled** on the laptop. Other OLP XDV tasks (result verification, hourly fixture check, SportyBet cache refresh, closing-line capture, FlashScore scraper, live-safe monitor, auto-sync, team-name audit, match analysis, MCP watchdog) stay on: they maintain local data and do not build or send the board.
- 2026-10-03: **Framework made one (Tolar07/framework #49-#53):** unused laptop-line code parked in `legacy/laptop/`; missed-run alarm (`watchdog.yml`); feed team names matched to the model (23 fixtures now model-rated); the laptop brain folded into the picks ledger (every rated fixture graded, "Model check" on the scorecard); agents/skills/CLAUDE.md/STATE.md aligned to the live pipeline (`tests/agent_refs_test.py` guards it).
- 2026-10-03: **Workspace concentrated on the framework:** the second pipeline copy at this repo's top level (55 scripts, `server/`, `verification/`, `data/`) and its old outputs/reports moved to `legacy/workspace/` (kept, never run). Workspace tools stay: `scripts/`, `sync_verifier.py`, `sync_check.py`, `git_sync.py`, `retire_mirror.py`, hooks.
- 2026-10-03: Submodule `olp_xdv_agent/olp_xdv` → `968091a` (framework `main` after #53: one framework, agents/skills/docs aligned, tests 31/31).
- 2026-10-03 (late): **Framework #54, #55, #59** — the missed-run watchdog now restarts a missed board slot itself and no longer false-alarms when GitHub fires its check after midnight (#54); the laptop-era vault notes are marked historical (#55); **fixture check + price check switched on** (#59, Architect: no paid APIs — standing order 27): every board fixture is checked against ESPN and football-data.co.uk (two agreeing → ✓ VERIFIED; listed postponed/cancelled → ⚠ not deployed), and every SportyBet price against bet365 and DraftKings with margins removed (a label only). Found on the way: football-data's free CSV had returned nothing for every league (byte-order mark decoded as Latin-1) — fixed. Another session merged #56/#57 (AI Survivor breeding) and #58 (standing order 26: live capital, £1 per acca, test — first written as Bet365 only, amended the same day to **SportyBet only**; the framework's `STANDING_ORDERS.md` is the record).
- 2026-10-03 (late): Workspace `CLAUDE.md` points sessions at the framework's own `CLAUDE.md`, `STANDING_ORDERS.md` and STATE current block; the stale workspace specialist agent and old prompt/board-review notes parked in `legacy/workspace/.claude/`; memory copies of three vault notes refreshed; a TheSportsDB key redacted from `.claude/settings.json` (both repos are public — the key, the admin password and a Telegram bot token in the framework's git history need rotating).
- 2026-10-03: Submodule `olp_xdv_agent/olp_xdv` → `264d0e2` (framework `main` after #59).

- 2026-10-04: **Framework #62-#69 (this session, Architect-approved):** country + league on every pick (order 28, #62); a bet365 board from the same run, sent to the Architect only, full betting market except "win to nil — no" (order 29, #63/#64); one record of the Telegram output in `STANDING_ORDERS.md`, 17 Sep spec marked superseded where it conflicts, Run ID header + send gate + NO-DATA line + competition-boundary splitting (order 30, #66); alternative markets restored on every fixture and news swaps drop BANKER (#67); alternative-market accas with their own codes (order 31) and learning that needs 3+ match days (order 22) (#68); the agents at work — supervisor status after every board, weekly results review, Claude PR review (needs an `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` secret) (#69). Weekly Claude agent review Routine: Mondays 09:51 Lagos, read-only, push + email to the Architect.
- 2026-10-04: **Framework #70-#71 (Architect-approved):** shaky picks switched to a steadier alternative within 5 points, marked ⇄ with the original kept and graded (order 32, #70); subscribers get the main board through the `TELEGRAM_SUBSCRIBER_CHAT_IDS` secret, the bet365 board stays Architect-only (order 33, #71, merged as `2ff67b4`). Only one chat receives the board until that secret holds the subscribers' chat IDs.
- 2026-10-04: **Everything in one place — framework `MAP.md` (framework #73).** A full audit of both repos (framework main, all 75 branches, `legacy/`, the vault; this workspace) is now one file in the framework that every session reads first: what runs (with the Routine IDs), who gets what, every secret, stored files, parked features, work only in git history, what is in this workspace and on the laptop, credentials to rotate, defects, decisions. Brought into the framework: the 10 Aug production intent and the recovered track record (`docs/records/`). The laptop task list below and the weekly Routine are in MAP §1 and §9.
- 2026-10-04: **Framework #74–#76 (Architect: "do the recommended fixes").** The pre-kickoff check (lineups, price drift, closing prices) is now one job looping every 20 min 09:00–20:40 UTC, started by the board run — GitHub had run its 20-minute cron 6 times in three days (#74). `/log` prices are now graded: the match is found on a recent board or a date is given, and wording that can't be settled is refused (#75). Every pick shows its kickoff in Lagos time — a KO column on Tables 1–2, before acca legs and bet365 singles (order 28, #76).
- 2026-10-04: **Workspace add-on audit.** `automaton`, `closing_edge`, `sports-skills`, `graphify`, `free-llm-api-resources`, `claude-code-action`, `ruflo` and everything under `external/` except `external/football-prediction/crosschecks/` are gitlinks with **no `.gitmodules` URL** — their code exists only on the laptop, so no cloud session or GitHub Action can reach or connect them. To use one, push it to a GitHub repo and add it as a proper submodule (or vendor the needed file into the framework). `crosschecks/` is six one-off research scripts (proportional vs Shin-style de-vig, a Dixon-Coles cross-check); folding a de-vig change into live selection would need a backtest first. The framework already carries its own sports-* and graphify skills.

- 2026-10-05: **Framework review + sync check (session `OLPXDV framework improvement areas`).** Full review of the framework (data, model, selection, delivery, tests, evidence); findings and the improvement list are in `docs/FRAMEWORK_REVIEW_2026-10-05.md`. Every recent branch in both repos (framework PRs #64-#78; workspace `ccr-2832deda-i6h0w0`, `claude/eloquent-noether-8b69az`, `ccr-51c326b5-vl6yc2`) is already on main; no other session is running. A stress-test run in the review container wrote a second 5 Oct board (109 fixtures, never sent) - kept as a labelled record in `docs/local-runs/2026-10-05-stress-test/`; the real 5 Oct board stays on framework main.
- 2026-10-05: Submodule `olp_xdv_agent/olp_xdv` -> `fa23da2` (framework `main`: #77 draw guard + team profiles + national-team Elo, #78 codes frozen at 10pm).
- 2026-10-05: **Framework #79 merged (Architect-approved engine upgrade).** Order 37 positive-value bets (Table 3C, own codes + Value acca); order 36 BTTS/goals calibration and $ VALUE picks; Champions/Europa/Conference League + HNL (market-implied) and Turkey, Greece, Austria, Switzerland (model-rated); season follows the date; stricter learning (order 22); Betfair Exchange sharp check; rating shrinkage; dry runs on scratch copies. Studies in the framework's `backtest/` (BTTS, REST, SHRINK). First live board with all of it: tonight's 20:47 UTC run for 6 Oct.
- 2026-10-05: Submodule `olp_xdv_agent/olp_xdv` -> framework `main` after #79.

## Shared Notes & Alerts

- Multi-session auto-synchronization enabled via CLAUDE.md.
- Canonical vault: `olp_xdv_agent/olp_xdv/docs/obsidian-vault/` (git-tracked, authoritative per Architect directive 2026-08-16).
- Retired mirror: `Documents/OLP_XDV_Vault/` (deprecated 2026-08-18, read-only).
- Agent memory: `.claude/projects/C--Users-Motunrayo-omniroute-test/memory/`
- Vault-memory sync active via `vault-memory-sync.js` with SessionStart/SessionEnd hooks.

## 2026-08-23 Pipeline Retrospective (Summary)

- **Accas produced:** 7 (A–G) | **Legs:** 35 total, 8 settled, 27 pending
- **Settled W/L:** 6W / 2L = 75.0% (0 full accas settled — all have ≥3 pending legs)
- **T1 (football-data.co.uk) failure:** All season files empty/headers-only (schema change)
- **T2 (ESPN API) coverage:** 29/35 fixtures matched — works but incomplete for lower tiers
- **CLV capture:** 0 entries Aug 10–23 (gap persists — `clv/closing_capture.py` not running in production)

**Bugs fixed this session:**
1. `build_cache` keyword-argument dispatch (ESPN.php:253 ValueError)
2. `_extract_closing_odds` NoneGuard bug — ESPN returns `odds=[None]`
3. Import error: `LEAGUE_MAP` → `SLUGS` in `data/espn_results.py`

**Full retrospective:** `olp_xdv_agent/olp_xdv/docs/obsidian-vault/STATE.md`

## Submodule Status

- `olp_xdv_agent/olp_xdv`: Modified (staged + unstaged changes)
  - Recent commits include HR57/HR58/HR59 hard rules, mirror retirement, vault sync hardening
  - Submodule points to rewritten history with secrets purged