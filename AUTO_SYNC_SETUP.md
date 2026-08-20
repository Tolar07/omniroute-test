# Automated Vault-Memory Sync + Git Commit (Every 5 Minutes)

This document describes the automated setup to enforce **HR54** (vault ↔ memory bidirectional sync) and **commit-always** (never leave tree dirty) every 5 minutes.

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/auto-sync-commit.js` | Node.js script: sync → git add -A → git commit if changes |
| `scripts/auto-sync-commit.bat` | Windows batch equivalent for Task Scheduler |
| `scripts/setup-auto-sync.ps1` | PowerShell script to install Windows Task Scheduler job |
| `scripts/AUTO_SYNC_SETUP.md` | This documentation |

---

## Quick Start (Manual Test)

```bash
# From repo root: C:\Users\Motunrayo\omniroute test
node scripts/auto-sync-commit.js
```

Or via batch:
```cmd
scripts\auto-sync-commit.bat
```

---

## Automated Setup (Windows Task Scheduler)

### Option 1: PowerShell (Recommended - Run as Administrator)

```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-auto-sync.ps1
```

### Option 2: Manual Task Scheduler

1. Open **Task Scheduler** (`taskschd.msc`)
2. **Create Basic Task** → Name: `OLP_XDV_AutoSyncCommit`
3. **Trigger**: Daily, repeat every 5 minutes indefinitely
4. **Action**: Start a program
   - Program: `node` (full path, e.g., `C:\Program Files\nodejs\node.exe`)
   - Arguments: `"C:\Users\Motunrayo\omniroute test\scripts\auto-sync-commit.js"`
   - Start in: `C:\Users\Motunrayo\omniroute test`
5. **Finish** → Check "Run whether user is logged on or not"

### Verify Task

```powershell
Get-ScheduledTask -TaskName "OLP_XDV_AutoSyncCommit" | Get-ScheduledTaskInfo
```

### Manual Run

```powershell
Start-ScheduledTask -TaskName "OLP_XDV_AutoSyncCommit"
```

### Disable/Remove

```powershell
Disable-ScheduledTask -TaskName "OLP_XDV_AutoSyncCommit"
Unregister-ScheduledTask -TaskName "OLP_XDV_AutoSyncCommit" -Confirm:$false
```

---

## What the Script Does (Every 5 Minutes)

1. **Vault ↔ Memory Sync (HR54)**
   - Runs `node .claude/scripts/hooks/vault-memory-sync.js reconcile`
   - Bidirectional auto-resolve: newer timestamp wins
   - Logs to `logs/auto-sync/auto-sync-YYYYMMDD.log`

2. **Git Status Check**
   - `git status --short` — shows dirty files

3. **Git Add All**
   - `git add -A` — stages everything (sweeps other session's staged files per `git-commit-sweeps-staged.md`)

4. **Conditional Commit**
   - Only commits if staged files exist
   - Message: `chore(auto): vault-memory sync + changes <timestamp>`
   - Includes: `Co-Authored-By: Claude <noreply@anthropic.com>`

5. **Final Status**
   - Reports working tree CLEAN/DIRTY

---

## Logging

Logs go to: `logs/auto-sync/auto-sync-YYYYMMDD.log`

Each run appends:
```
[2026-08-20T14:30:00.000Z] ════════════════════════════════════════════════════════════
[2026-08-20T14:30:00.000Z] 🔄 AUTO SYNC + COMMIT STARTED
[2026-08-20T14:30:00.000Z] ════════════════════════════════════════════════════════════
[2026-08-20T14:30:01.000Z] 
[2026-08-20T14:30:01.000Z] 📦 Step 1: Vault <-> Memory sync (HR54)
[2026-08-20T14:30:02.000Z]    ✅ Sync complete
[2026-08-20T14:30:02.000Z]    Summary: 10 in sync, 0 diverged, 0 missing in vault, 0 missing in memory
[2026-08-20T14:30:02.000Z] 
[2026-08-20T14:30:02.000Z] 📋 Step 2: Git status check
[2026-08-20T14:30:02.000Z]    Files changed: 0
[2026-08-20T14:30:02.000Z] 
[2026-08-20T14:30:02.000Z] 📥 Step 3: Git add -A (sweeps other session's staged files)
[2026-08-20T14:30:02.000Z]    ✅ Staged all changes
[2026-08-20T14:30:02.000Z] 
[2026-08-20T14:30:02.000Z] 💾 Step 4: Check for staged changes to commit
[2026-08-20T14:30:02.000Z]    No staged changes to commit
[2026-08-20T14:30:02.000Z] 
[2026-08-20T14:30:02.000Z] 📊 Step 6: Final status
[2026-08-20T14:30:02.000Z]    Working tree: CLEAN
[2026-08-20T14:30:02.000Z] 
[2026-08-20T14:30:02.000Z] ════════════════════════════════════════════════════════════
[2026-08-20T14:30:02.000Z] ✅ AUTO SYNC + COMMIT COMPLETE
[2026-08-20T14:30:02.000Z] ════════════════════════════════════════════════════════════
```

---

## Integration with Existing Hooks

| Hook | Trigger | What It Does |
|------|---------|--------------|
| `session-start.js` | SessionStart | Loads context, runs vault-memory sync |
| `session-end.js` | SessionEnd | Archives conversation, updates session file |
| `obsidian-sync.js` | SessionStart/End | Legacy sync (superseded by vault-memory-sync.js) |
| **auto-sync-commit.js** | **Every 5 min (Task Scheduler)** | **Sync + commit continuously** |

---

## HR54 Compliance

> **HR54**: Vault ↔ Memory sync required on SessionStart/SessionEnd

The 5-minute automated sync **exceeds** HR54 by syncing continuously, not just at session boundaries. This prevents divergence when multiple sessions are active.

---

## commit-always Compliance

> **commit-always**: Commit every session's work; never leave tree dirty

The 5-minute automated commit **enforces** this continuously — even if a session crashes or forgets to commit, the automation catches it within 5 minutes.

---

## Safety Notes

- **Only commits when there are actual changes** — no empty commits
- **Sweeps staged files from other sessions** — `git add -A` captures everything
- **Descriptive commit messages** — timestamp + file count for traceability
- **Co-Authored-By** — proper attribution
- **Runs in repo root** — `C:\Users\Motunrayo\omniroute test`
- **Node.js must be in PATH** — uses `node` command directly

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Task doesn't run | Check Task Scheduler history; ensure "Run whether user is logged on or not" |
| Node not found | Use full path to `node.exe` in Task action |
| Permission denied | Run Task Scheduler setup as Administrator |
| Sync fails | Check `logs/auto-sync/` for details; run `node .claude/scripts/hooks/vault-memory-sync.js status` manually |
| Git errors | Ensure no other process locks `.git/index` |

---

## Next Steps

1. **Test manually**: `node scripts/auto-sync-commit.js`
2. **Install scheduled task**: Run `scripts/setup-auto-sync.ps1` as Admin
3. **Verify**: Check `logs/auto-sync/` after 5-10 minutes
4. **Monitor**: Periodically review log for any recurring issues