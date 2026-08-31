#!/usr/bin/env python3
"""
PreToolUse hook. Wire to matcher "Edit|Write|MultiEdit|NotebookEdit".

Reads the standard PreToolUse JSON off stdin, pulls whatever path field the
tool call is targeting, and tries to acquire that path's lock for the
current session_id (see lock_utils.py). Exit code 2 blocks the tool call
and Claude Code shows stderr to the model, so a session that hits a lock
gets a clear reason instead of a silent failure -- and the model can decide
to wait, ask you, or work on something else instead.

Deliberately does NOT try to lock every tool (e.g. Bash commands that edit
files via sed/redirection slip through). It covers the tools Claude Code
itself uses for file edits, which is the overwhelming majority of the
sweep/collision cases in practice. Extend the PATH_KEYS list if you use
other structured file-editing tools.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lock_utils import acquire  # noqa: E402

PATH_KEYS = ("file_path", "notebook_path", "path")

# Don't lock the lock directory itself, git internals, or the state ledger --
# these are meant to be touched by tooling/hooks regardless of who's "in" a
# module, and locking them would just create false contention.
SKIP_SUBSTRINGS = (
    "/.claude/locks/",
    "/.git/",
    "docs/STATE.md",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # don't block on a hook-input parsing problem

    session_id = payload.get("session_id", "unknown-session")
    tool_input = payload.get("tool_input", {}) or {}

    target = None
    for key in PATH_KEYS:
        if key in tool_input:
            target = tool_input[key]
            break

    if not target:
        return 0  # nothing identifiable to lock; let it through

    target_str = str(target).replace("\\", "/")
    if any(s in target_str for s in SKIP_SUBSTRINGS):
        return 0

    ok, message = acquire(target, session_id)
    if not ok:
        sys.stderr.write(f"BLOCKED — {message}\n")
        return 2

    if "stolen" in message or "unreadable" in message:
        sys.stderr.write(f"NOTE — {message}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())