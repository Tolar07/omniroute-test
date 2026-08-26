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
| `olp_xdv_agent/olp_xdv/` | Main OLP XDV agent repo (submodule) |
| `olp_xdv_agent/olp_xdv/docs/obsidian-vault/` | Canonical vault — **git-tracked, authoritative** |
| `.claude/` | Claude Code config, skills, agents, hooks |
| `.claude/projects/.../memory/` | Persistent agent memory across sessions |
| `scripts/` | Utility scripts (sync, retire, etc.) |
| `data/` | Runtime data, databases |
| `closing_edge/` | Closing Edge module |
| `sports-skills/` | Sports data skills |
| `graphify/` | Graph visualization tool |
| `free-llm-api-resources/` | LLM API reference data |

---

## Canonical Vault — Core Notes (Read These First)

All notes are interconnected via `[[wikilinks]]`. Start with `[[OLP XDV.md]]` every session.

| Note | Purpose |
|------|---------|
| `[[OLP XDV.md]]` | Entry point — read first every session |
| `[[Rules.md]]` | All HRs/IDs as coded + doc-vs-code disagreements |
| `[[Decisions Log.md]]` | Dated Architect directives (backfilled + 4× 11-Aug-2026) |
| `[[Protected Constants.md]]` | Off-limits: `ARCHITECT_SIGNOFF`, CLV gate, capital deployment |
| `[[Agents.md]]` | 16 project agents (7 chusri + 9 plugin) with model/tools |
| `[[Architecture.md]]` | Pipeline: SCAN → trigger → publish, CLV loop, admin dash |
| `[[Open Questions.md]]` | Unresolved items needing explicit Architect answer |
| `[[Loops.md]]` | Recurring pipeline loops |
| `[[README.md]]` | Vault overview |
| `[[API Keys.md]]` | Credential reference (sanitized, real values in `.env` only) |
| `[[OLP_XDV_Framework_Index.md]]` | Navigation index with repo paths |
| `[[Vault-Memory-Index.md]]` | Vault ↔ Memory index (this file) |

---

## Agent Memory System (Persistent Across Sessions)

**Location:** `.claude/projects/C--Users-Motunrayo-omniroute-test/memory/`

| Memory File | Purpose |
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

**Active:** `vault-memory-sync.js` (bidirectional sync between canonical vault ↔ agent memory)  
**Enforced:** SessionStart/SessionEnd hooks enforce HR54 compliance on both stores

---

## Critical Rules (Hard Rules / HRs)

| HR | Description |
|----|-------------|
| **HR54** | Vault ↔ Memory sync required on SessionStart/SessionEnd |
| **HR57** | Mirror retirement — canonical vault only |
| **HR58** | Vault is git-tracked single source of truth |
| **HR59** | Sync hardening — bidirectional enforcement |

See `[[Rules.md]]` in canonical vault for full list.

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
2. Read `olp_xdv_agent/olp_xdv/docs/obsidian-vault/OLP XDV.md`
3. Run vault-memory sync: `node scripts/vault-memory-sync.js`
4. Check git status: `git status && git log --oneline -5`

### Session End
1. Run vault-memory sync
2. Commit all changes: `git add -A && git commit -m "..."`
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

# Commit (sweeps staged from other sessions)
git add -A && git commit -m "descriptive message"

# Run OLP XDV agent
cd olp_xdv_agent/olp_xdv && python -m olp_xdv

# Run tests
cd olp_xdv_agent/olp_xdv && pytest
```

---

## Environment

- **Python:** 3.11+ (venv in `olp_xdv_agent/olp_xdv/.venv`)
- **Node:** 20+ (for sync scripts)
- **Playwright:** Installed for browser automation
- **Real credentials:** `.env` only (never commit)

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

**olp-xdv-supervisor** — Single authoritative coordinator for multi-session state management. Maintains `docs/STATE.md` synchronization protocol.

---

*Last updated: 2026-08-20*