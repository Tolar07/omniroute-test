"""
Matchbook multiples (accumulators) — a one-off test (Architect 2026-10-15:
"test one of the strongest ACCA ... with £1 in Matchbook. Use the bot to test
it and book it").

Matchbook's multiples are not in its public API docs; the website uses
  POST /multiples/rest/v2/odds       {"selections": [{"runner-id"}], "permutation-type"} -> odds, min/max stake
  POST /multiples/rest/v3/multiples  {"selections": [{"side", "odds", "runner-id"}], "stake",
                                      "permutation-type", "odds", "odds-type"}       -> places it
Multiples accept Match Odds, the full-match Total, Both Teams To Score and
half-line Handicap only (Double Chance, Draw No Bet, team / 1st-half totals,
quarter-ball handicaps: refused, checked 2026-10-15). They are priced under
the exchange: three legs worth 1.77 as singles were quoted 1.63.

The legs are the framework's strongest: the highest-chance legs (singles or
rated pool) in those markets, one per match, kicking off 30 min-16 h away.
Stake is capped at MAX_STAKE_GBP; nothing here runs on the 15-minute cycle.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from matchbook_live import config as C
from matchbook_live import framework_feed as F
from matchbook_live import scanner

QUOTE_PATH = "/multiples/rest/v2/odds"
SUBMIT_PATH = "/multiples/rest/v3/multiples"
ALLOWED = ("match_odds", "total", "btts", "handicap")
MAX_STAKE_GBP = 2.00
LEGS = 3
WINDOW = (timedelta(minutes=30), timedelta(hours=16))
LOG_FILE = "multiples.jsonl"


def strongest(picks_files: list[dict], events: list[dict], now: datetime, n: int = LEGS) -> list[dict]:
    rows = []
    for s in F.legs(picks_files):
        mk = F.map_market(s.get("market") or "")
        if mk is None or mk["type"] not in ALLOWED:
            continue
        try:
            p = float(s.get("chance"))
        except (TypeError, ValueError):
            continue
        e = F.match_event(s.get("home") or "", s.get("away") or "", scanner._dt(s.get("kickoff_utc")),
                          events, s.get("kickoff"))
        start = scanner._dt(e.get("start")) if e else None
        if start is None or not (WINDOW[0] <= start - now <= WINDOW[1]):
            continue
        m, r, _ = F.find_runner(e, mk)
        b = scanner.runner_book(r) if r else None
        if b is None:
            continue
        rows.append({"p": p, "event_id": str(e["id"]), "event_name": e.get("name"), "start": e.get("start"),
                     "market_name": m.get("name"), "runner_id": r["id"], "runner_name": r.get("name"),
                     "odds": b["best_back"], "fw_pick": s.get("pick") or s.get("market"),
                     "pool": bool(s.get("pool"))})
    rows.sort(key=lambda x: -x["p"])
    out, used = [], set()
    for x in rows:
        if x["event_id"] not in used:
            out.append(x)
            used.add(x["event_id"])
        if len(out) == n:
            break
    return out


def place(client, legs: list[dict], stake: float, state_dir: Path, now: datetime, live: bool) -> str:
    """Quote, then place (live) or only report (dry). Logs every attempt."""
    if not 0 < stake <= MAX_STAKE_GBP:
        raise ValueError(f"acca stake £{stake:.2f} outside (0, £{MAX_STAKE_GBP:.2f}]")
    if len(legs) < 2:
        return f"ACCA: only {len(legs)} eligible leg(s) on Matchbook — nothing placed"
    q = client.multiple_quote([x["runner_id"] for x in legs])
    odds = float(q["odds"])
    chance = math.prod(x["p"] for x in legs)
    rec = {"at": now.isoformat(timespec="seconds"), "legs": legs, "stake": stake, "odds": odds,
           "singles_product": round(math.prod(x["odds"] for x in legs), 4), "model_chance": round(chance, 4),
           "min_stake": q.get("min-stake"), "max_stake": q.get("max-stake"), "live": live}
    if stake < float(q.get("min-stake") or 0):
        rec["status"] = "BELOW MIN STAKE"
    elif not live:
        rec["status"] = "DRY"
    else:
        try:
            rec["response"] = client.multiple_submit(legs, stake, odds)
            rec["status"] = "PLACED"
        except Exception as e:                       # report it, never retry blind with money
            rec["status"], rec["error"] = "ERROR", f"{type(e).__name__}: {str(e)[:300]}"
    with open(state_dir / LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lines = [f"ACCA {rec['status']}: £{stake:.2f} @ {odds:.2f} on Matchbook (singles would pay "
             f"{rec['singles_product']:.2f}) · framework chance {chance:.0%} · break-even "
             f"{1 / odds:.0%}"]
    lines += [f"  {x['start'][11:16]} {x['event_name']} — {x['market_name']}: {x['runner_name']} "
              f"@{x['odds']:.2f} ({x['p']:.0%})" for x in legs]
    if rec.get("error"):
        lines.append(f"  {rec['error']}")
    elif rec.get("response"):
        lines.append(f"  Matchbook: {json.dumps(rec['response'])[:300]}")
    return "\n".join(lines)
