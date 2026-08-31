#!/usr/bin/env python3
"""
UserPromptSubmit hook.

This is the actual fix for "two sessions give different answers to the same
question" -- but scoped, not "read everything every time." It:

  1. Extracts candidate keywords from the prompt you just typed.
  2. Scans the canonical vault directory for .md notes, matching on
     filename and any `aliases:` frontmatter line (the same convention your
     memory files already use).
  3. Re-reads the best-matching note(s) FROM DISK, right now -- not from
     whatever either session already has in context -- and prints them to
     stdout, which Claude Code adds as context before the model answers.

Because both sessions run this same hook against the same files on disk at
the moment each question is asked, they ground their answers in identical
bytes even if one session edited something ten minutes ago. It does not
fix a genuine mid-edit collision (that's what the lock hooks are for) --
it fixes the "stale context" version of the inconsistency.

CONFIGURE VAULT_DIR below to your actual path before wiring this in.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lock_utils import repo_root  # noqa: E402

# ---- CONFIGURE THIS ----
VAULT_DIR_RELATIVE = "olp_xdv_agent/olp_xdv/docs/obsidian-vault"
MAX_MATCHES = 2
MAX_CHARS_PER_FILE = 4000
STOPWORDS = {
    "the", "a", "an", "is", "are", "what", "why", "how", "does", "do",
    "on", "in", "of", "for", "to", "and", "or", "with", "current", "right",
    "now", "status", "about", "please", "can", "you", "tell", "me",
}
# -------------------------


def load_index(vault_dir: Path) -> list[dict]:
    """Build {filename, aliases, path} for every note in the vault."""
    index = []
    if not vault_dir.exists():
        return index
    for md in vault_dir.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="ignore")
        aliases = []
        m = re.search(r"^aliases:\s*\[(.*?)\]", text, re.MULTILINE)
        if m:
            aliases = [a.strip().strip('"').strip("'") for a in m.group(1).split(",")]
        index.append({
            "path": md,
            "name": md.stem,
            "aliases": aliases,
        })
    return index


def score(entry: dict, keywords: set[str]) -> int:
    haystack = " ".join([entry["name"]] + entry["aliases"]).lower()
    haystack_words = set(re.findall(r"[a-z0-9]+", haystack))
    return len(keywords & haystack_words)


def extract_keywords(prompt: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", prompt.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    prompt = payload.get("prompt", "")
    if not prompt:
        return 0

    vault_dir = repo_root() / VAULT_DIR_RELATIVE
    index = load_index(vault_dir)
    if not index:
        return 0  # vault not found at configured path -- fail silent, don't block typing

    keywords = extract_keywords(prompt)
    if not keywords:
        return 0

    scored = [(score(e, keywords), e) for e in index]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda s: s[0], reverse=True)
    top = scored[:MAX_MATCHES]

    if not top:
        return 0

    out = ["--- Fresh canonical-note read (topic_context hook) ---"]
    for _, entry in top:
        text = entry["path"].read_text(encoding="utf-8", errors="ignore")
        truncated = len(text) > MAX_CHARS_PER_FILE
        text = text[:MAX_CHARS_PER_FILE]
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        out.append(f"\n## {entry['name']}.md (read just now from disk)\n{safe_text}")
        if truncated:
            out.append(f"\n[...truncated; full file at {entry['path']}]")
    out.append("\n--- end fresh read ---")
    print("\n".join(out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())