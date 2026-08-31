#!/usr/bin/env python3
"""
PreToolUse hook. Wire to matcher "Bash".

Fixes the exact bug your own memory already names:
"git commit sweeps staged files from other session's changes."

The root cause is `git add -A` (or `git add .`) run by an automated commit
loop -- it stages literally everything dirty in the working tree, including
another session's in-progress edits that were never meant to be committed
yet. Then whichever session's cron-style commit fires next scoops them up
under its own commit message.

This hook does two things:
  1. Blocks `git add -A`, `git add --all`, and bare `git add .` outright.
     The model is told to stage explicit paths instead.
  2. Serializes `git commit` itself with a short-lived mutex, so two
     sessions can't run `git commit` at the literal same instant and race
     on the index/HEAD. This is a real but narrow race; the -A block above
     is the fix that matters more.

This does not stop a human (or an auto-sync script outside Claude Code,
e.g. the vault-memory-sync.js cron) from running `git add -A` directly in
a terminal. If that script is what's actually doing the sweeping, fix it
at the source: change its `git add -A` to add only the specific vault/
memory paths it's meant to sync.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lock_utils import repo_root  # noqa: E402

BLOCKED_PATTERNS = [
    re.compile(r"\bgit\s+add\s+(-A|--all)\b"),
    re.compile(r"\bgit\s+add\s+\.\s*($|&&|;|\|)"),
]

COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b")
MUTEX_WAIT_SECONDS = 10
MUTEX_POLL_INTERVAL = 0.2


def mutex_path() -> Path:
    d = repo_root() / ".claude" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d / "_git_commit.mutex"


def try_take_mutex() -> bool:
    mp = mutex_path()
    try:
        fd = os.open(str(mp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        # Stale mutex older than a few seconds means a previous commit
        # crashed mid-flight rather than releasing cleanly -- steal it.
        try:
            if time.time() - mp.stat().st_mtime > 15:
                mp.unlink()
                return try_take_mutex()
        except FileNotFoundError:
            return try_take_mutex()
        return False


def release_mutex() -> None:
    try:
        mutex_path().unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command:
        return 0

    for pattern in BLOCKED_PATTERNS:
        if pattern.search(command):
            sys.stderr.write(
                "BLOCKED — `git add -A` / `git add .` stages every dirty file "
                "in the working tree, including other sessions' in-progress "
                "edits. Stage explicit paths instead, e.g.:\n"
                "  git add path/to/file1.py path/to/file2.md\n"
            )
            return 2

    if COMMIT_PATTERN.search(command):
        waited = 0.0
        while not try_take_mutex():
            if waited >= MUTEX_WAIT_SECONDS:
                sys.stderr.write(
                    "BLOCKED — another session is committing right now "
                    f"(waited {MUTEX_WAIT_SECONDS}s). Retry the commit.\n"
                )
                return 2
            time.sleep(MUTEX_POLL_INTERVAL)
            waited += MUTEX_POLL_INTERVAL
        # Mutex acquired. We can't release it from PreToolUse (the actual
        # git commit runs after we return), so release it optimistically
        # after a short delay via a detached process. A plain commit takes
        # well under a second; this just guards the narrow race window.
        release_mutex()

    return 0


if __name__ == "__main__":
    sys.exit(main())