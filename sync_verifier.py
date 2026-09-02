#!/usr/bin/env python3
"""
sync_verifier.py — the loop agent that answers "is everything actually
synced, online and offline" without you having to check by hand.

Checks, for the parent repo AND every submodule:
  - Are there uncommitted local changes? (DIRTY)
  - Does local HEAD have commits the remote doesn't? (AHEAD — this is
    the exact bug pattern from the very start of this project: a commit
    made locally and never pushed)
  - Does the remote have commits local doesn't? (BEHIND)
  - Both at once? (DIVERGED — needs a manual merge/rebase decision,
    can't self-resolve)

Deliberately does NOT alert on every DIRTY state — uncommitted changes
while you're actively working is completely normal, not a sync failure.
It only alerts when:
  - AHEAD persists past a threshold (default 15 min) — a real forgotten
    push, not mid-work.
  - BEHIND persists past a longer threshold (default 60 min) — normal
    session-start pulls should catch this quickly; only flag if nothing
    has pulled in a while.
  - DIVERGED — flagged immediately, every time, since this can't
    self-resolve and gets worse the longer it's left.

Usage:
    python sync_verifier.py --once      # single check, human-readable report, exit
    python sync_verifier.py             # runs forever as the loop agent
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
POLL_INTERVAL_SEC = int(os.environ.get("SYNC_VERIFIER_POLL_SEC", "300"))  # 5 min
AHEAD_ALERT_THRESHOLD_SEC = int(os.environ.get("SYNC_AHEAD_THRESHOLD_SEC", "900"))    # 15 min
BEHIND_ALERT_THRESHOLD_SEC = int(os.environ.get("SYNC_BEHIND_THRESHOLD_SEC", "3600")) # 60 min
STATE_FILE = Path(".claude/locks/sync_verifier_state.json")


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def find_submodule_paths(root: Path) -> list[Path]:
    gitmodules = root / ".gitmodules"
    if not gitmodules.exists():
        return []
    code, out = run(["git", "config", "--file", str(gitmodules), "--get-regexp", "path"], root)
    if code != 0:
        return []
    paths = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            paths.append(root / parts[1])
    return paths


@dataclass
class RepoSyncStatus:
    path: str
    dirty_files: list[str]
    ahead: int
    behind: int
    branch: str
    fetch_failed: bool


def check_repo(repo_dir: Path) -> RepoSyncStatus:
    branch_code, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_dir)
    branch = branch if branch_code == 0 else "unknown"

    fetch_code, _ = run(["git", "fetch"], repo_dir)
    fetch_failed = fetch_code != 0

    ahead, behind = 0, 0
    if not fetch_failed:
        code, out = run(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{branch}"],
            repo_dir,
        )
        if code == 0 and out:
            parts = out.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])

    _, status_out = run(["git", "status", "--porcelain"], repo_dir)
    dirty = [line[3:].strip() for line in status_out.splitlines()] if status_out else []

    return RepoSyncStatus(str(repo_dir), dirty, ahead, behind, branch, fetch_failed)


def classify(status: RepoSyncStatus) -> str:
    if status.fetch_failed:
        return "FETCH_FAILED"
    if status.ahead > 0 and status.behind > 0:
        return "DIVERGED"
    if status.ahead > 0:
        return "AHEAD"
    if status.behind > 0:
        return "BEHIND"
    if status.dirty_files:
        return "DIRTY_ONLY"  # uncommitted but not ahead/behind — normal mid-work state
    return "SYNCED"


def print_report(statuses: list[RepoSyncStatus]) -> None:
    print(f"\n=== Sync check @ {datetime.now().strftime('%H:%M:%S')} ===")
    for s in statuses:
        state = classify(s)
        icon = {"SYNCED": "[OK]", "DIRTY_ONLY": "[*]", "AHEAD": "[UP]", "BEHIND": "[DOWN]",
                "DIVERGED": "[!!]", "FETCH_FAILED": "[X]"}.get(state, "[?]")
        print(f"{icon} {s.path} [{s.branch}] - {state}"
              + (f" (ahead {s.ahead}, behind {s.behind})" if s.ahead or s.behind else "")
              + (f" - {len(s.dirty_files)} uncommitted file(s)" if s.dirty_files else ""))


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[sync_verifier] Telegram not configured, would alert: {message}", file=sys.stderr)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[sync_verifier] Telegram send failed: {exc}", file=sys.stderr)


def evaluate_and_alert(statuses: list[RepoSyncStatus], state: dict) -> dict:
    """
    Only alerts on real, sustained drift — not routine mid-edit dirty
    state, and not a one-off AHEAD reading that could just be a commit
    in flight right this second.
    """
    now = time.time()
    new_state = dict(state)

    for s in statuses:
        result = classify(s)
        key = s.path
        prev = state.get(key, {})

        if result == "DIVERGED":
            if prev.get("last_alert_state") != "DIVERGED":
                send_telegram(
                    f"⚠️ *Sync DIVERGED* — {s.path} [{s.branch}]\n"
                    f"Local has {s.ahead} commit(s) not on remote AND remote has "
                    f"{s.behind} commit(s) not local. This needs a manual merge/"
                    f"rebase decision — it will not resolve itself."
                )
            new_state[key] = {"state": result, "since": prev.get("since", now), "last_alert_state": result}

        elif result == "AHEAD":
            since = prev.get("since", now) if prev.get("state") == "AHEAD" else now
            duration = now - since
            if duration >= AHEAD_ALERT_THRESHOLD_SEC and prev.get("last_alert_state") != "AHEAD":
                send_telegram(
                    f"⬆️ *Unpushed commits* — {s.path} [{s.branch}]\n"
                    f"{s.ahead} commit(s) local-only for over {int(duration / 60)} min. "
                    f"Run git_sync.py to push, or this is exactly how the original "
                    f"submodule pointer bug happened."
                )
                new_state[key] = {"state": result, "since": since, "last_alert_state": result}
            else:
                new_state[key] = {"state": result, "since": since, "last_alert_state": prev.get("last_alert_state")}

        elif result == "BEHIND":
            since = prev.get("since", now) if prev.get("state") == "BEHIND" else now
            duration = now - since
            if duration >= BEHIND_ALERT_THRESHOLD_SEC and prev.get("last_alert_state") != "BEHIND":
                send_telegram(
                    f"⬇️ *Behind remote* — {s.path} [{s.branch}]\n"
                    f"{s.behind} commit(s) on remote not pulled locally for over "
                    f"{int(duration / 60)} min. Pull before starting new work here."
                )
                new_state[key] = {"state": result, "since": since, "last_alert_state": result}
            else:
                new_state[key] = {"state": result, "since": since, "last_alert_state": prev.get("last_alert_state")}

        else:
            # SYNCED, DIRTY_ONLY, or FETCH_FAILED — reset tracking, and if we'd
            # previously alerted on a now-resolved problem, say so once.
            if prev.get("last_alert_state") in ("AHEAD", "BEHIND", "DIVERGED"):
                send_telegram(f"✅ *Resolved* — {s.path} [{s.branch}] is back in sync.")
            new_state[key] = {"state": result, "since": now, "last_alert_state": None}

    return new_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single check, print report, exit")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    if not (root / ".git").exists():
        print(f"{root} is not a git repo root.")
        return 1

    def all_repos() -> list[Path]:
        repos = [root]
        repos.extend(p for p in find_submodule_paths(root) if p.exists())
        return repos

    if args.once:
        statuses = [check_repo(r) for r in all_repos()]
        print_report(statuses)
        return 0

    print(f"[sync_verifier] Loop agent running — checking every {POLL_INTERVAL_SEC}s. Ctrl+C to stop.")
    state = load_state()
    while True:
        try:
            statuses = [check_repo(r) for r in all_repos()]
            print_report(statuses)
            state = evaluate_and_alert(statuses, state)
            save_state(state)
        except Exception as exc:  # noqa: BLE001
            print(f"[sync_verifier] check failed this cycle: {exc}", file=sys.stderr)
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    sys.exit(main())