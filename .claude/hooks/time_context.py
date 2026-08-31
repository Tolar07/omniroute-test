#!/usr/bin/env python3
"""
Wire to BOTH SessionStart and UserPromptSubmit.

Why per-turn and not just SessionStart: SessionStart context is set once,
when the session opens. Your sessions run long (the 22:00-night-before to
next-morning production shift, for instance), and as a session's context
grows and gets compacted, an early "today is X" line can get summarized
away or simply crowded out. A model with no fresh reminder of the date
will default toward whatever date it last saw mentioned, or its training
cutoff -- which is exactly the "mixed up the date" symptom you're seeing.
Re-stating it on every single prompt costs a few tokens and makes the
failure mode structurally impossible instead of just less likely.

Uses likely.

Uses the local system clock of the machine Claude Code is running on
(your Windows box), so it's automatically correct across BST/GMT without
hardcoding a timezone or offset.
"""
from __future__ import annotations

import sys
from datetime import datetime


def main() -> int:
    now = datetime.now().astimezone()
    weekday = now.strftime("%A")
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    tz = now.strftime("%Z%z") or "local time, no tz name available"
    iso_week = now.isocalendar()[1]

    print(
        f"[live clock] Right now it is {weekday}, {date_str}, {time_str} "
        f"({tz}), ISO week {iso_week}. Use this as the actual current "
        f"date/time for anything time-sensitive in this turn -- do not "
        f"infer the date from training data or from an earlier message."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())