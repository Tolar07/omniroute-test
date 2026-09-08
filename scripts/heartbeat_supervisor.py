#!/usr/bin/env python3
"""Heartbeat supervisor gate.

The single choke-point every OLP XDV session (cloud Claude, local Claude,
scheduled run_daily.py) must call before publishing a heartbeat, and after
every settlement. Owns docs/HEARTBEAT_STATE.json and appends to
docs/STATE.md; the rules it enforces live in docs/HEARTBEAT_POLICY.md.

Commands
--------
    check
        Print a one-screen summary of the current policy + state and
        halt (exit 2) if the policy has any unset <!-- ARCHITECT-FILL -->
        sections, or the state is more than 26 hours stale.

    gate --stake <units> --selection <key> --ev <edge>
        Approve or halt a proposed heartbeat action. Exits 0 = approve,
        2 = halt (prints reason), 1 = policy/state unreadable.

    record --outcome W|L --pnl <units> [--lineage-id <id>]
        Update HEARTBEAT_STATE.json, append a line to docs/STATE.md's
        Heartbeat Coordination section, and print the new state. Does
        NOT git-commit — the caller commits with
        `git commit --only docs/HEARTBEAT_STATE.json docs/STATE.md`.

Design notes
------------
- Refuses to invent numbers. If the policy is unwritten, every gate call
  halts. This is deliberate: an "empty rule" must not silently mean the
  code's baseline.
- Reads paths relative to the script location so it works identically
  from a scheduled task, a session shell, or a wrapper.
- Never touches anything under olp_xdv_agent/olp_xdv/ or any protected
  file listed in root CLAUDE.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "docs" / "HEARTBEAT_POLICY.md"
STATE_PATH = REPO_ROOT / "docs" / "HEARTBEAT_STATE.json"
STATE_LEDGER_PATH = REPO_ROOT / "docs" / "STATE.md"
STATE_LEDGER_SECTION = "## Heartbeat Coordination"

STALENESS_HOURS = 26

EXIT_OK = 0
EXIT_UNREADABLE = 1
EXIT_HALT = 2

FILL_MARKER = re.compile(r"<!--\s*ARCHITECT-FILL[^>]*-->")


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _line_has_active_marker(line: str) -> bool:
    # Strip inline-code spans first so prose that quotes the marker
    # (e.g. "any unset `<!-- ARCHITECT-FILL -->` sections") does not
    # count as an unset field.
    stripped = re.sub(r"`[^`]*`", "", line)
    return bool(FILL_MARKER.search(stripped))


def _load_policy() -> tuple[str, list[str]]:
    """Return (policy_text, list_of_unset_field_line_numbers)."""
    if not POLICY_PATH.exists():
        raise FileNotFoundError(f"Missing policy: {POLICY_PATH}")
    text = POLICY_PATH.read_text(encoding="utf-8")
    unset: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _line_has_active_marker(line):
            unset.append(f"L{i}: {line.strip()}")
    return text, unset


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        raise FileNotFoundError(f"Missing state: {STATE_PATH}")
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _append_ledger(line: str) -> None:
    """Append a dated line under the Heartbeat Coordination section in STATE.md.

    Creates the section if it does not yet exist.
    """
    text = STATE_LEDGER_PATH.read_text(encoding="utf-8") if STATE_LEDGER_PATH.exists() else ""
    stamp = _iso(_now_utc())
    entry = f"- {stamp} {line}"
    if STATE_LEDGER_SECTION in text:
        marker_idx = text.index(STATE_LEDGER_SECTION)
        header_end = text.index("\n", marker_idx) + 1
        rest = text[header_end:]
        # Insert right after the header line, above any existing entries.
        new_text = text[:header_end] + entry + "\n" + rest
    else:
        sep = "" if text.endswith("\n") or not text else "\n"
        new_text = (
            text + sep + "\n" + STATE_LEDGER_SECTION + "\n" + entry + "\n"
        )
    STATE_LEDGER_PATH.write_text(new_text, encoding="utf-8")


def _stale(state: dict[str, Any]) -> tuple[bool, str]:
    ts = _parse_iso(state.get("updated_at_utc"))
    if ts is None:
        return True, "updated_at_utc missing or malformed"
    age = _now_utc() - ts
    if age > timedelta(hours=STALENESS_HOURS):
        return True, f"state age {age} exceeds {STALENESS_HOURS}h"
    return False, ""


def cmd_check(_: argparse.Namespace) -> int:
    try:
        policy_text, unset = _load_policy()
        state = _load_state()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    print("=== Heartbeat Supervisor — check ===")
    print(f"policy: {POLICY_PATH}")
    print(f"state:  {STATE_PATH}")
    print()
    print("policy unset sections:")
    if unset:
        for u in unset:
            print(f"  - {u}")
    else:
        print("  (none — all rules are set)")
    print()
    print("current state:")
    for k in (
        "last_outcome",
        "last_outcome_date",
        "current_lineage_id",
        "current_lineage_step",
        "previous_stake_units",
        "next_intended_stake_units",
        "next_intended_selection_key",
        "updated_by_session_id",
        "updated_at_utc",
    ):
        print(f"  {k}: {state.get(k)}")
    is_stale, why = _stale(state)
    print()
    print(f"stale: {is_stale}" + (f" ({why})" if is_stale else ""))
    if unset or is_stale:
        return EXIT_HALT
    return EXIT_OK


def cmd_gate(ns: argparse.Namespace) -> int:
    try:
        _, unset = _load_policy()
        state = _load_state()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    reasons: list[str] = []
    if unset:
        reasons.append(f"policy has {len(unset)} unset ARCHITECT-FILL sections")
    is_stale, why = _stale(state)
    if is_stale:
        reasons.append(f"state stale ({why})")

    # Structural checks — the exact numbers stay policy-driven. The
    # supervisor refuses to substitute a default. If the Architect has
    # written the rule, they can add a validator that reads the numbers
    # out of HEARTBEAT_POLICY.md and enforces them here.
    if state.get("last_outcome") == "W":
        prev = state.get("previous_stake_units")
        if prev is None:
            reasons.append("last_outcome=W but previous_stake_units is null")
        elif ns.stake is not None and ns.stake <= prev:
            reasons.append(
                f"proposed stake {ns.stake} does not compound previous {prev} after W"
            )

    if ns.stake is not None and ns.stake <= 0:
        reasons.append(f"proposed stake {ns.stake} not positive")
    if ns.ev is not None and ns.ev < 0:
        reasons.append(f"proposed EV {ns.ev} is negative")

    if reasons:
        print("HALT — heartbeat NOT approved:")
        for r in reasons:
            print(f"  - {r}")
        return EXIT_HALT

    print(
        f"APPROVE — stake={ns.stake} selection={ns.selection!r} ev={ns.ev}"
    )
    return EXIT_OK


def cmd_record(ns: argparse.Namespace) -> int:
    try:
        state = _load_state()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"UNREADABLE: {exc}", file=sys.stderr)
        return EXIT_UNREADABLE

    now = _now_utc()
    outcome = ns.outcome.upper()
    if outcome not in {"W", "L"}:
        print("outcome must be W or L", file=sys.stderr)
        return EXIT_UNREADABLE

    history = state.get("history") or []
    history.append(
        {
            "at_utc": _iso(now),
            "outcome": outcome,
            "pnl_units": ns.pnl,
            "lineage_id": ns.lineage_id or state.get("current_lineage_id"),
            "lineage_step": state.get("current_lineage_step"),
            "stake_units": state.get("next_intended_stake_units")
            or state.get("previous_stake_units"),
            "selection_key": state.get("next_intended_selection_key"),
            "recorded_by": ns.session_id,
        }
    )

    state["last_outcome"] = outcome
    state["last_outcome_date"] = now.strftime("%Y-%m-%d")
    state["last_outcome_pnl_units"] = ns.pnl
    state["previous_stake_units"] = (
        state.get("next_intended_stake_units")
        or state.get("previous_stake_units")
    )
    # Advance or reset lineage. The reset condition is policy — the
    # supervisor only tracks the step count; the wrapper that reads the
    # policy is responsible for calling record with the right outcome and
    # then updating current_lineage_id when the lineage resets.
    state["current_lineage_step"] = int(state.get("current_lineage_step") or 0) + 1
    state["next_intended_stake_units"] = None
    state["next_intended_selection_key"] = None
    state["updated_by_session_id"] = ns.session_id
    state["updated_at_utc"] = _iso(now)
    state["history"] = history

    _save_state(state)
    _append_ledger(
        f"outcome={outcome} pnl={ns.pnl} lineage_step={state['current_lineage_step']} "
        f"session={ns.session_id}"
    )

    print("=== recorded ===")
    print(json.dumps({k: state[k] for k in (
        "last_outcome",
        "last_outcome_date",
        "current_lineage_step",
        "previous_stake_units",
        "updated_by_session_id",
        "updated_at_utc",
    )}, indent=2))
    print("\nNext: commit with")
    print("  git commit --only docs/HEARTBEAT_STATE.json docs/STATE.md -m '…'")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Print current policy + state; halt if unset or stale.")

    g = sub.add_parser("gate", help="Approve or halt a proposed heartbeat.")
    g.add_argument("--stake", type=float, help="Proposed stake in units")
    g.add_argument("--selection", type=str, help="Selection key on the day's board")
    g.add_argument("--ev", type=float, help="Proposed EV (edge fraction, e.g. 0.05)")

    r = sub.add_parser("record", help="Record a settled outcome.")
    r.add_argument("--outcome", required=True, help="W or L")
    r.add_argument("--pnl", type=float, required=True, help="P&L in units")
    r.add_argument("--lineage-id", type=str, default=None)
    r.add_argument(
        "--session-id",
        type=str,
        default="unknown",
        help="Identifier of the session recording the outcome",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    if ns.cmd == "check":
        return cmd_check(ns)
    if ns.cmd == "gate":
        return cmd_gate(ns)
    if ns.cmd == "record":
        return cmd_record(ns)
    return EXIT_UNREADABLE


if __name__ == "__main__":
    sys.exit(main())
