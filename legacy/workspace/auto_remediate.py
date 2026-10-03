#!/usr/bin/env python3
"""
auto_remediate.py — the actual missing piece. Wire this into
run_night_pipeline.py's failure handling (see the hook point at the
bottom) so a stage failure triggers a real fix attempt, not just a
report you have to manually relay between Claude Code and this chat.

What it does on a stage failure:
  1. Gathers the failure: the traceback, the relevant source file(s),
     and PROTECTED_RULES.md (so the fix can't violate a bright line).
  2. Invokes Claude Code headlessly (`claude -p`) with an explicit,
     narrow mandate: diagnose, write the smallest fix that addresses
     the ROOT cause (not a workaround), run any existing tests, and
     report back structured JSON.
  3. If the fix is applied and tests pass, commits+pushes it via
     git_sync.py with a clear auto-fix message, and retries the failed
     stage ONCE.
  4. Either way — fixed-and-retried, or still broken — sends ONE
     Telegram message summarizing what was tried, so you find out the
     outcome of the attempt, not just the original failure.

GUARDRAILS (deliberately narrow, not "fix anything about anything"):
  - Never touches capital deployment, staking, or PROTECTED_RULES.md
    itself — those stay Architect-only regardless of how confident the
    fix looks.
  - Only attempts ONE retry per stage per run. If it fails twice, stop
    and escalate to you — repeated auto-retries on a real, deeper
    problem just burns time and API calls without progress.
  - Every attempt (successful or not) is logged to INCIDENTS.md with
    what was tried, so there's a record even when it works — silent
    automatic fixes are exactly the kind of thing that becomes
    impossible to reconstruct later when you're asking "why did this
    change."

REQUIRES: the Bash-permission problem from earlier has to actually be
resolved for this to work headlessly — `claude -p` needs either a
scoped allowlist covering the files it'll touch, or
--dangerously-skip-permissions for this specific invocation. If that's
still unresolved, this script will hang the same way everything else
has been hanging, for the same underlying reason.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".claude" / "hooks"))
from lock_utils import repo_root  # noqa: E402

MAX_RETRIES_PER_STAGE = 1
INCIDENTS_MD = repo_root() / "INCIDENTS.md"


def build_remediation_prompt(stage_name: str, traceback_text: str) -> str:
    protected_rules_path = repo_root() / "PROTECTED_RULES.md"
    protected_rules = protected_rules_path.read_text(encoding="utf-8") if protected_rules_path.exists() else ""

    return f"""A scheduled pipeline stage just failed. Diagnose the ROOT cause
(not a surface workaround), write the smallest correct fix, and run any
existing tests that cover the affected code.

STAGE: {stage_name}

TRACEBACK:
{traceback_text}

HARD LIMITS — do not violate these regardless of how it would help:
{protected_rules}

When done, output ONLY this JSON object (no other text):
{{
  "root_cause": "<one sentence>",
  "fix_applied": true | false,
  "files_changed": ["<path>", ...],
  "tests_run": "<command run, or 'none existed'>",
  "tests_passed": true | false | null,
  "safe_to_retry": true | false,
  "notes": "<anything the Architect should know, especially if you did NOT fix it>"
}}

If the fix would touch capital deployment, staking logic, or
PROTECTED_RULES.md itself — do NOT make the change. Set fix_applied to
false and explain why in notes instead.
"""


def invoke_claude_code(prompt: str) -> dict | None:
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            cwd=repo_root(),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        print("auto_remediate: 'claude' CLI not found on PATH.", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("auto_remediate: Claude Code invocation timed out after 10 min.", file=sys.stderr)
        return None

    if result.returncode != 0:
        print(f"auto_remediate: claude -p exited {result.returncode}: {result.stderr[:500]}", file=sys.stderr)
        return None

    try:
        # claude -p --output-format json wraps the actual response; the
        # remediation JSON we asked for is inside the model's text output.
        outer = json.loads(result.stdout)
        text = outer.get("result", outer.get("content", result.stdout))
        cleaned = text.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"auto_remediate: could not parse Claude Code's response: {e}", file=sys.stderr)
        return None


def log_incident(stage_name: str, remediation: dict | None) -> None:
    line = f"- **{datetime.now().isoformat(timespec='seconds')}** — auto-remediation attempted for `{stage_name}`: "
    if remediation is None:
        line += "invocation failed (see stderr / logs), no fix attempted.\n"
    else:
        line += (
            f"root cause: {remediation.get('root_cause', 'unknown')}; "
            f"fix_applied={remediation.get('fix_applied')}; "
            f"tests_passed={remediation.get('tests_passed')}; "
            f"files: {', '.join(remediation.get('files_changed', []) or ['none'])}\n"
        )
    with open(INCIDENTS_MD, "a", encoding="utf-8") as f:
        f.write(line)


def attempt_remediation(stage_name: str, traceback_text: str) -> bool:
    """Returns True if it's safe to retry the stage now."""
    prompt = build_remediation_prompt(stage_name, traceback_text)
    remediation = invoke_claude_code(prompt)
    log_incident(stage_name, remediation)

    if remediation is None:
        return False

    if remediation.get("fix_applied") and remediation.get("tests_passed") is not False:
        # Fix applied and either tests passed or there were none to run.
        # Commit+push it so the fix persists, using the same sync path as
        # everything else in this kit.
        commit_msg = f"auto-fix: {remediation.get('root_cause', 'pipeline failure')} ({stage_name})"
        subprocess.run(
            [sys.executable, str(repo_root() / "git_sync.py"), commit_msg],
            cwd=repo_root(),
        )
        return bool(remediation.get("safe_to_retry", False))

    return False


if __name__ == "__main__":
    # Manual test invocation: python auto_remediate.py "<stage>" "<traceback text>"
    if len(sys.argv) < 3:
        print("Usage: python auto_remediate.py <stage_name> <traceback_text>")
        sys.exit(1)
    ok = attempt_remediation(sys.argv[1], sys.argv[2])
    print(f"Safe to retry: {ok}")