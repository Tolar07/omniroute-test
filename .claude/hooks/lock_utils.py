#!/usr/bin/env python3
"""
Shared file-locking primitives for multi-session Claude Code safety.

Why this exists: with several Claude Code sessions open on the same working
copy, two sessions can edit or commit the same file within the same few
minutes. STATE.md's "Active Locks" section is documentation, not enforcement
-- nothing stops a second session from writing while it says "None". This
module makes locks real: a session must atomically create a lock file before
editing a path, and any other session's attempt to edit the same path fails
until the lock is released or goes stale.

Design notes:
- Uses os.open(..., O_CREAT | O_EXCL) for lock creation. This is atomic on
  both POSIX and Windows (NTFS) via Python's os module, so no separate
  "check then create" race exists.
- Locks live under <repo>/.claude/locks/ as one JSON file per locked path,
  named by a short hash of the resolved absolute path so any file in the
  repo (not just markdown) can be locked, including paths with characters
  that aren't safe as filenames.
- A lock older than LOCK_TTL_SECONDS is considered abandoned (crashed
  session, forgotten SessionEnd) and can be stolen. This trades a small
  risk of a live session losing its lock during an unusually long single
  edit against the much larger risk of a dead lock blocking everyone
  forever. Raise the TTL if 20 minutes is too short for how you work.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

LOCK_TTL_SECONDS = int(os.environ.get("CLAUDE_LOCK_TTL_SECONDS", "1200"))  # 20 min


def repo_root() -> Path:
    """Resolve the repo root Claude Code hooks run against.

    Claude Code sets CLAUDE_PROJECT_DIR for hook subprocesses. Fall back to
    cwd for manual invocation (e.g. running --status by hand).
    """
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(root) if root else Path.cwd()


def lock_dir() -> Path:
    d = repo_root() / ".claude" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lock_id(target_path: str) -> str:
    resolved = str(Path(target_path).resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]


def _lock_file(target_path: str) -> Path:
    return lock_dir() / f"{_lock_id(target_path)}.lock"


def _read_lock(lock_path: Path) -> dict | None:
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _is_stale(info: dict) -> bool:
    return (time.time() - info.get("acquired_at", 0)) > LOCK_TTL_SECONDS


def acquire(target_path: str, session_id: str) -> tuple[bool, str]:
    """Try to acquire the lock for target_path on behalf of session_id.

    Returns (ok, message). ok=True means the caller may proceed with the
    edit. ok=False means another live session holds the lock; message
    explains who and for how long, suitable for showing back to the model.
    """
    lp = _lock_file(target_path)
    payload = {
        "path": str(Path(target_path).resolve()),
        "session_id": session_id,
        "pid": os.getpid(),
        "acquired_at": time.time(),
    }
    try:
        fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return True, "lock acquired"
    except FileExistsError:
        pass

    existing = _read_lock(lp)
    if existing is None:
        # Corrupt/empty lock file -- treat as stale, steal it.
        lp.write_text(json.dumps(payload), encoding="utf-8")
        return True, "lock acquired (previous lock file was unreadable)"

    if existing.get("session_id") == session_id:
        # Same session re-touching the file (e.g. two edits in a row) --
        # refresh the timestamp and continue.
        lp.write_text(json.dumps(payload), encoding="utf-8")
        return True, "lock refreshed (already held by this session)"

    if _is_stale(existing):
        lp.write_text(json.dumps(payload), encoding="utf-8")
        age_min = int((time.time() - existing.get("acquired_at", 0)) / 60)
        return True, f"stale lock stolen (previous holder inactive {age_min} min)"

    age_min = int((time.time() - existing.get("acquired_at", 0)) / 60)
    other = existing.get("session_id", "unknown")
    return False, (
        f"Locked by session {other} for {age_min} min "
        f"(path: {existing.get('path')}). Wait, ask that session to finish, "
        f"or if it's actually dead, it will auto-release after "
        f"{LOCK_TTL_SECONDS // 60} min."
    )


def release_all_for_session(session_id: str) -> list[str]:
    """Remove every lock owned by session_id. Called on SessionEnd/Stop."""
    released = []
    for lp in lock_dir().glob("*.lock"):
        info = _read_lock(lp)
        if info and info.get("session_id") == session_id:
            try:
                lp.unlink()
                released.append(info.get("path", str(lp)))
            except FileNotFoundError:
                pass
    return released


def list_active() -> list[dict]:
    """All current locks, live or stale, for status reporting."""
    out = []
    for lp in lock_dir().glob("*.lock"):
        info = _read_lock(lp)
        if info:
            info["stale"] = _is_stale(info)
            out.append(info)
    return out