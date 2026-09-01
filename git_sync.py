#!/usr/bin/env python3
"""
git_sync.py — "commit and sync," done right, every time.

Why this exists: `git commit` alone only writes to your LOCAL .git folder.
Nothing is visible to GitHub, other sessions, or other machines until
`git push` runs too. The dangling submodule pointer from earlier in this
project's history is almost certainly this exact gap -- a commit made
locally inside olp_xdv_agent/olp_xdv that was never pushed, so the parent
repo's recorded submodule commit doesn't exist anywhere but one machine's
disk.

This script always does the full sequence, and does it in the right
order for a submodule setup:
  1. Show exactly which files are dirty (transparent, not a blind -A)
  2. Stage those explicit files, commit
  3. Pull --rebase (fold in anything another session already pushed,
     BEFORE pushing your own work — this is what avoids fights between
     sessions, alongside the file locks from earlier)
  4. Push
  5. If a submodule changed, do steps 1-4 INSIDE the submodule first,
     then step 5b: back in the parent repo, stage the updated submodule
     pointer, commit, pull --rebase, push -- so the parent repo's record
     of "which submodule commit is current" is never stale.

If a rebase conflict happens, this ABORTS the rebase and tells you
exactly what to do manually. It will never try to auto-resolve a
conflict -- that's a decision only you or Claude Code with full context
should make, not a sync script.

Usage:
    python git_sync.py "commit message here"
    python git_sync.py "commit message" --repo path/to/submodule
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".claude" / "hooks"))
try:
    from lock_utils import repo_root as _hooks_repo_root, override_active  # noqa: E402
except ImportError:
    def _hooks_repo_root() -> Path:
        return Path.cwd()

    def override_active() -> bool:
        return False


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


def dirty_files(repo_dir: Path) -> list[str]:
    code, out = run(["git", "status", "--porcelain"], repo_dir)
    if code != 0 or not out:
        return []
    files = []
    for line in out.splitlines():
        # porcelain format: "XY path" — path starts at column 3
        f = line[3:].strip()
        # Only add files that actually exist (skip directories, worktrees, etc.)
        if (repo_dir / f).exists():
            files.append(f)
        else:
            print(f"  (skipping non-existent: {f})")
    return files


def take_mutex(repo_dir: Path) -> bool:
    if override_active():
        return True
    mutex = repo_dir / ".claude" / "locks" / "_git_commit.mutex"
    mutex.parent.mkdir(parents=True, exist_ok=True)
    waited = 0.0
    while waited < 10:
        try:
            fd = __import__("os").open(str(mutex), __import__("os").O_CREAT | __import__("os").O_EXCL | __import__("os").O_WRONLY)
            __import__("os").close(fd)
            return True
        except FileExistsError:
            if time.time() - mutex.stat().st_mtime > 15:
                mutex.unlink(missing_ok=True)
                continue
            time.sleep(0.3)
            waited += 0.3
    return False


def release_mutex(repo_dir: Path) -> None:
    mutex = repo_dir / ".claude" / "locks" / "_git_commit.mutex"
    mutex.unlink(missing_ok=True)


def sync_one_repo(repo_dir: Path, message: str) -> bool:
    print(f"\n=== Syncing {repo_dir} ===")

    if not take_mutex(repo_dir):
        print("BLOCKED — another session is syncing this repo right now. "
              "Wait and retry, or use architect_override.py if this is stuck.")
        return False

    try:
        dirty = dirty_files(repo_dir)
        if not dirty:
            print("Nothing changed here — pulling latest anyway to stay current.")
        else:
            print(f"Staging {len(dirty)} file(s):")
            for f in dirty:
                print(f"  {f}")
            code, out = run(["git", "add"] + dirty, repo_dir)
            if code != 0:
                print(f"git add failed:\n{out}")
                return False

            code, out = run(["git", "commit", "-m", message], repo_dir)
            if code != 0:
                print(f"git commit failed (may be nothing staged after all):\n{out}")

        print("Pulling latest (rebase, autostash)...")
        code, out = run(["git", "pull", "--rebase", "--autostash"], repo_dir)
        if code != 0:
            print(f"PULL/REBASE FAILED — likely a real conflict:\n{out}")
            print("Aborting rebase to leave the repo in a clean, known state. "
                  "This needs a manual look, not an auto-resolve.")
            run(["git", "rebase", "--abort"], repo_dir)
            return False

        print("Pushing...")
        code, out = run(["git", "push"], repo_dir)
        if code != 0:
            print(f"PUSH FAILED:\n{out}")
            return False

        print(f"✓ {repo_dir} is synced — local and remote match.")
        return True
    finally:
        release_mutex(repo_dir)


def find_submodule_paths(repo_root: Path) -> list[Path]:
    gitmodules = repo_root / ".gitmodules"
    if not gitmodules.exists():
        return []
    code, out = run(["git", "config", "--file", str(gitmodules), "--get-regexp", "path"], repo_root)
    if code != 0:
        return []
    paths = []
    for line in out.splitlines():
        # format: "submodule.<name>.path <path>"
        parts = line.split()
        if len(parts) == 2:
            paths.append(repo_root / parts[1])
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message", help="Commit message")
    parser.add_argument("--repo", default=None, help="Sync only this specific path (submodule or parent), not the full chain")
    args = parser.parse_args()

    repo_root = _hooks_repo_root()

    if args.repo:
        ok = sync_one_repo(Path(args.repo), args.message)
        return 0 if ok else 1

    # Full chain: submodules first, then the parent repo records their new pointers.
    submodules = find_submodule_paths(repo_root)
    all_ok = True

    for sm in submodules:
        if sm.exists():
            all_ok = sync_one_repo(sm, args.message) and all_ok

    all_ok = sync_one_repo(repo_root, args.message) and all_ok

    if all_ok:
        print("\n[OK] Everything synced — submodule(s) and parent repo both match GitHub.")
    else:
        print("\n[FAIL] Sync incomplete — see errors above before trusting the remote state.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())