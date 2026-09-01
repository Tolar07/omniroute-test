#!/usr/bin/env python3
"""
Wire to SessionStart, BEFORE session_full_read.py (order matters — pull
first, then read the vault, so the full-vault read reflects whatever the
pull just brought in, not what was on disk before it).

This is the other half of "make sure everything is in sync": git_sync.py
handles pushing your work out; this handles pulling everyone else's work
in, automatically, the moment a session opens -- so you don't have to
remember to do it, and a session never silently starts working from a
copy that's already behind what's on GitHub.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lock_utils import repo_root  # noqa: E402


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


def pull(repo_dir: Path) -> None:
    code, out = run(["git", "pull", "--rebase", "--autostash"], repo_dir)
    if code != 0:
        sys.stderr.write(
            f"session_start_pull: could not cleanly pull {repo_dir} — "
            f"{out.splitlines()[-1] if out else 'unknown error'}. "
            f"Starting session anyway, but this repo may be out of sync "
            f"until manually resolved (run git_sync.py or fix the conflict by hand).\n"
        )
    else:
        sys.stderr.write(f"session_start_pull: {repo_dir} up to date.\n")


def main() -> int:
    root = repo_root = repo_root()
    if not (_root / ".git").exists():
        return 0  # not a git repo, nothing to sync

    for _sm in find_submodule_paths(_root):
        if _sm.exists():
            pull(_sm)

    pull(_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())