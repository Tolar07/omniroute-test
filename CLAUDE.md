# CLAUDE.md — OLP XDV Agent Workspace

> **Single source of truth for Claude Code sessions in this workspace.**  
> Read this file at the start of every session.

---

## Project Overview

**OLP XDV Agent** — A Telegram bot/daemon for sports data collection, odds processing, and automated publishing with a CLV (Closing Line Value) feedback loop.

**Repository Root:** `C:\Users\Motunrayo\omniroute test\`  
**Canonical Vault (Authoritative):** `olp_xdv_agent/olp_xdv/docs/obsidian-vault/`  
**Agent Memory:** `.claude/projects/C--Users-Motunrayo-omniroute-test/memory/`

---

## Key Directories

| Path | Purpose |
|------|---------|
| `olp_xdv_agent/olp_xdv/` | **The framework** — Tolar07/framework `main` (submodule), the one live OLP XDV, run by GitHub Actions. Its own `CLAUDE.md` and `STANDING_ORDERS.md` govern it |
| `olp_xdv_agent/olp_xdv/docs/obsidian-vault/` | Canonical vault — **git-tracked, authoritative** |
| `.claude/` | Claude Code config and hooks for this workspace. The framework's own agents (`olp-xdv-01` … `10`, supervisor, specialist) and the `olp-xdv` skill live in `olp_xdv_agent/olp_xdv/.claude/` — start Claude Code in `olp_xdv_agent/olp_xdv` to use them |
| `.claude/projects/.../memory/` | Persistent agent memory across sessions |
| `scripts/` | Utility scripts (sync, retire, etc.) |
| `legacy/workspace/` | Parked laptop-era pipeline copies, outputs and reports (2026-10-03) — never run |
| `closing_edge/` | Closing Edge module |
| `sports-skills/` | Sports data skills |
| `graphify/` | Graph visualization tool |
| `free-llm-api-resources/` | LLM API reference data |

---

## Read First — The Framework's Own Documents

Every session starts with these four, all in `olp_xdv_agent/olp_xdv/`:

1. `CLAUDE.md` — the live loop, what each piece protects, the hard rules.
2. `STANDING_ORDERS.md` — the Architect's standing rules (test-enforced).
3. The CURRENT STATE block at the top of `docs/obsidian-vault/STATE.md`.
4. `MAP.md` — where everything is kept: the framework, its git history,
   THIS workspace (what in it matters and what is junk), the laptop,
   secrets and Routines. Look things up there before asking the Architect
   where something is; add anything you find that isn't listed.

## Canonical Vault — The Record

All notes are interconnected via `[[wikilinks]]`. Where a note disagrees with the three documents above, they win.

| Note | Purpose |
|------|---------|
| `[[STATE.md]]` | Current state block + session journal |
| `[[Rules.md]]` | All HRs/IDs as coded + doc-vs-code disagreements (the ID register) |
| `[[Decisions Log.md]]` | Dated Architect directives |
| `[[Protected Constants.md]]` | Off-limits: `ARCHITECT_SIGNOFF`, CLV gate, capital deployment |
| `[[Open Questions.md]]` | Unresolved items needing explicit Architect answer |
| `[[API Keys.md]]` | Credential reference (redacted; real values in `.env` only) |
| `[[Vault-Memory-Index.md]]` | Vault ↔ Memory index |
| `[[OLP XDV.md]]`, `[[Architecture.md]]`, `[[Agents.md]]`, `[[Loops.md]]`, `[[OLP_XDV_Framework_Index.md]]` | **Historical** — the laptop line before 2026-10-03 (web dashboard, Acca A production, laptop tasks, old agent roster). Kept as a record; do not act on them |
| `[[README.md]]` | Vault overview |

---

## Agent Memory System (Persistent Across Sessions)

**Location:** `.claude/projects/C--Users-Motunrayo-omniroute-test/memory/`

> **Checked 2026-10-05:** the 12 notes below exist only on the laptop — they were never
> pushed. The copy of that folder in this repo holds 23 copies of vault notes instead.
> Push them from the laptop for cloud sessions to read them. The framework's own
> memory, which every live run reads and writes, is in the framework: `memory/knowledge.json`
> (what was learned from results), `memory/proposals.json` (losing-market proposals and
> the Architect's decisions), `memory/runs.jsonl` (every board run) and
> `memory/corrections.csv` (`/note`) — standing order 39.

| Memory File (laptop only) | Purpose |
|-------------|---------|
| `MEMORY.md` | Master index (links to all memories below) |
| `olp-xdv-agent.md` | OLP XDV agent: Telegram bot/daemon + web wiring, publish gate, commit conventions |
| `safe-move-protocol.md` | Default opening move: check git status/log first |
| `git-commit-sweeps-staged.md` | `git commit` sweeps other session's staged files |
| `data-quality-monitor.md` | Season state, extra-league coverage, mypy/ruff gate |
| `booking-sportybet.md` | Booking modules: requests client, Playwright cache, bridge |
| `save-all-conversations.md` | Stop hook archives transcripts to memory/conversations/ |
| `commit-always.md` | Commit every session's work; never leave tree dirty |
| `everything-claude-code.md` | Plugin in OLP XDV .claude/; use agents/skills/commands/rules |
| `awesome-design-md.md` | Design-token library (73 brands); pitch-night palette in proto.css |
| `sports-data-skills.md` | machina-sports skills (4 skills in .claude/skills/) |
| `claude-code-action.md` | anthropics/claude-code-action cloned at workspace root |

---

## Task Observer (Active)

**Skill:** `.claude/skills/task-observer/` (rebelytics/one-skill-to-rule-them-all)
- **Scope:** Project-level only — staging-only, never auto-applies.
- **Behavior:** Logs observations to `skill-observations/log.md`; stages updates to `skill-updates/`; **never modifies live files directly.**
- **Activation:** Session-start — read `skill-observations/log.md` and `skill-observations/last-review-date.txt` before starting substantive work; log findings as observations during sessions.
- **Active-participation mode (2026-08-26):** The skill may receive explicit commands to propose, implement, or review staged updates. Before any auto-apply (to non-protected files only), the user must review and approve.

## Retired Mirror (Deprecated 2026-08-18)

**Location:** `Documents/OLP_XDV_Vault/` — **NOT authoritative, non-git, READ-ONLY**

All unique content migrated to canonical vault. Remaining files are read-only reference only:
- `Pipeline Runs/` — historical pipeline artifacts
- `.obsidian/` — Obsidian workspace config
- `.trash/` — Obsidian trash

---

## Two-Way Sync

Laptop only: `vault-memory-sync.js` syncs the vault with the laptop's agent
memory through SessionStart/SessionEnd hooks. Nothing enforces it in the
cloud: the framework's `sync-health.yml` is manual and points at a folder
that isn't in that repo, and HR54 is not in the `Rules.md` register.

---

## Critical Rules (Hard Rules / HRs)

| HR | Description |
|----|-------------|
| **HR54** | Vault ↔ Memory sync required on SessionStart/SessionEnd |
| **Capital bright line** | `assert_paper_only()` hard-fails below Phase 3-active; booking never clicks Place Bet; no code routes a real stake. Does not yield to directives |
| **HR59** | Traceable output — no fixture, odds figure or result in any output unless a fetch script produced it in this session (run_id + timestamp); a failed fetch reads `NO DATA — PENDING` |
| **HR35** | No silent completeness — missing data reads `PENDING`, never blank or a real-looking placeholder |

The canonical vault is git-tracked and the single source of truth, and the
`Documents/OLP_XDV_Vault/` mirror is retired (both are practices, not IDs: this
table listed them as HR57/HR58/HR59 until 2026-10-03, which clashed with the
register). IDs come from `[[Rules.md]]`; only the Architect assigns new ones.

---

## Protected Constants (Never Modify)

From `[[Protected Constants.md]]`:
- `ARCHITECT_SIGNOFF` — Requires explicit Architect approval
- **CLV Gate** — Closing Line Value threshold for publish decisions
- **Capital Deployment** — Fund allocation logic

---

## Standard Workflows

### Session Start
1. Read `MEMORY.md` (this file's memory counterpart)
2. Read the framework's `CLAUDE.md`, `STANDING_ORDERS.md` and the CURRENT STATE block of its `docs/obsidian-vault/STATE.md` (see "Read First" above)
3. Run vault-memory sync: `node scripts/vault-memory-sync.js`
4. Check git status: `git status && git log --oneline -5`

### Session End
1. Run vault-memory sync
2. Commit with explicit paths: `git add <paths> && git commit -m "..."` (the commit guard blocks `git add -A`)
3. Update `docs/STATE.md` with recent changes

### Making Changes
1. **Always read file first** before editing
2. Make atomic, scoped changes
3. Update relevant vault notes if architecture/decisions change
4. Run sync after vault edits

---

## Key Commands

```bash
# Sync vault ↔ memory
node scripts/vault-memory-sync.js

# Check git status
git status && git log --oneline -5

# Commit explicit paths only (git add -A is blocked by the commit guard)
git add <paths> && git commit -m "descriptive message"

# Build a board without sending it (the framework; live runs are GitHub Actions)
cd olp_xdv_agent/olp_xdv && python run_daily.py --no-send --only-production --target-date <YYYY-MM-DD>

# Run the framework's tests
cd olp_xdv_agent/olp_xdv && python tests/run_all.py
```

---

## Environment

- **Python:** 3.11+ (venv in `olp_xdv_agent/olp_xdv/.venv`)
- **Node:** 20+ (for sync scripts)
- **Playwright:** Installed for browser automation
- **Real credentials:** `.env` only (never commit)

---

## Branch Policy (2026-10-03)

- **`main` is the only live line** in this repo, and `Tolar07/framework` `main` is the only live OLP XDV framework. All live branches were merged on 2026-10-03 (omniroute-test PR #6; framework PR #47).
- Every other branch is a **frozen backup**, kept on purpose and never deleted. Do not resume work on one, merge from one, or base new work on one without the Architect explicitly naming it. This includes `main-purged`, `claude/heartbeat-supervisor`, `claude/schedule-10pm`, `claude/omniroute-test-read-r9gga9` and the merged session branches.
- New work starts from the latest `main`.

---

## Submodules

| Submodule | Path | Status |
|-----------|------|--------|
| olp_xdv_agent | `olp_xdv_agent/olp_xdv` | Active, rewritten history |
| free-llm-api-resources | `free-llm-api-resources` | Model list updated |
| graphify | `graphify` | Ignore obj/bin |
| claude-code-action | `claude-code-action` | Cloned at root |

---

## Installed Skills (Project-Scoped)

**Task Observer** (`rebelytics/one-skill-to-rule-them-all`) — installed at `.claude/skills/task-observer/`
- **Scope:** Project-level only (not global/user-level)
- **Behavior:** Staging-only — writes observations to `skill-observations/` and staged skill updates to `skill-updates/`; **never auto-applies** or modifies live files directly.
- **Activation:** Manual invocation at task start (not auto-chained).

**Protected-file review requirement:** Any staged update from Task Observer touching:
- `olp_xdv_agent/olp_xdv/bets/booking_tracker.py`
- `olp_xdv_agent/olp_xdv/variant_selection.py`
- The odds tolerance check (in `booking/verify_external_code.py` and `Rules.md`)
- The constitution/bright-lines file (`automaton/constitution.md`)

...requires **manual line-by-line review before approval** — same bar as any other change to those files.

---

## Quick Links

| Target | Path |
|--------|------|
| Canonical vault root | `olp_xdv_agent/olp_xdv/docs/obsidian-vault/` |
| Agent memory root | `.claude/projects/C--Users-Motunrayo-omniroute-test/memory/` |
| OLP XDV repo root | `olp_xdv_agent/olp_xdv/` |
| Retired mirror (read-only) | `Documents/OLP_XDV_Vault/` |

---

## Supervisor Agent

**olp-xdv-supervisor** (in the framework's `.claude/agents/`) watches the live loop — every GitHub Actions workflow, tests on `main`, each stage agent's area — and reports one honest status. This workspace's `docs/STATE.md` is updated by whichever session changes the workspace.

---

*Last updated: 2026-10-03*