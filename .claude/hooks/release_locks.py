#!/usr/bin/env python3
"""
SessionEnd hook (also safe to wire to Stop if you want locks released after
every turn rather than only when the session fully ends -- see the note in
the setup instructions about that tradeoff).

Releases every lock this session_id holds, then rewrites the "Active Locks"
section of docs/STATE.md so it reflects what's actually locked right now
instead of being a note someone forgot to update. This turns STATE.md from
aspirational documentation into a generated status report.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lock_utils import list_active, release_all_for_session, repo_root  # noqa: E402

STATE_MD_RELATIVE = "docs/STATE.md"
SECTION_HEADER = "## Active Locks"


def render_locks_section() -> str:
    locks = [l for l in list_active() if not l.get("stale")]
    if not locks:
        return f"{SECTION_HEADER}\n\n- None\n"
    lines = [SECTION_HEADER, ""]
    for l in locks:
        age_min = int((time.time() - l.get("acquired_at", 0)) / 60)
        lines.append(f"- `{l.get('path')}` — session {l.get('session_id')} ({age_min} min)")
    lines.append("")
    return "\n".join(lines)


def update_state_md() -> None:
    state_path = repo_root() / STATE_MD_RELATIVE
    if not state_path.exists():
        return  # don't create it from a hook if it isn't already tracked
    text = state_path.read_text(encoding="utf-8")
    new_section = render_locks_section()

    pattern = re.compile(
        rf"{re.escape(SECTION_HEADER)}\n.*?(?=\n## |\Z)", re.DOTALL
    )
    if pattern.search(text):
        text = pattern.sub(new_section.rstrip("\n") + "\n", text, count=1)
    else:
        text = new_section + "\n" + text
    state_path.write_text(text, encoding="utf-8")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    session_id = payload.get("session_id", "unknown-session")
    released = release_all_for_session(session_id)

    try:
        update_state_md()
    except Exception as exc:  # never fail SessionEnd over a doc-formatting bug
        sys.stderr.write(f"release_locks: STATE.md update skipped ({exc})\n")

    if released:
        sys.stderr.write(f"Released {len(released)} lock(s) for session {session_id}\n")
    return 0  # SessionEnd output isn't shown to the model either way


if __name__ == "__main__":
    sys.exit(main())