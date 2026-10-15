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
import os
from datetime import datetime, timedelta
from pathlib import Path

from matchbook_live import config as C
from matchbook_live import framework_feed as F
from matchbook_live import scanner

QUOTE_PATH = "/multiples/rest/v2/odds"
SUBMIT_PATH = "/multiples/rest/v3/multiples"
ALLOWED = ("match_odds", "total", "btts", "handicap")
MAX_STAKE_GBP = 2.00
# Architect 2026-10-15: "budget £10 from the funds for the ACC, use £2 each ... a cap of 5 ACC".
# A batch counts against the day's budget; the earlier one-off £1 test (no "budget" tag) does not.
DAILY_BUDGET_GBP = 10.00
MIN_LEG_CHANCE = 0.75                # every leg the framework rates 75%+
LEGS = 3
WINDOW = (timedelta(minutes=30), timedelta(hours=16))
LOG_FILE = "multiples.jsonl"


def strongest(picks_files: list[dict], events: list[dict], now: datetime, n: int = LEGS,
              exclude_events: frozenset = frozenset()) -> list[dict]:
    """The n highest-chance eligible legs, one per match, at MIN_LEG_CHANCE or better."""
    rows = []
    for s in F.legs(picks_files):
        mk = F.map_market(s.get("market") or "")
        if mk is None or mk["type"] not in ALLOWED:
            continue
        try:
            p = float(s.get("chance"))
        except (TypeError, ValueError):
            continue
        if p < MIN_LEG_CHANCE:
            continue
        e = F.match_event(s.get("home") or "", s.get("away") or "", scanner._dt(s.get("kickoff_utc")),
                          events, s.get("kickoff"))
        start = scanner._dt(e.get("start")) if e else None
        if start is None or not (WINDOW[0] <= start - now <= WINDOW[1]) or str(e["id"]) in exclude_events:
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


AUTO = (os.getenv("MB_ACCA_AUTO") or "1") == "1"   # Architect 2026-10-15: bet365's accas move to Matchbook
AUTO_STAKE, AUTO_COUNT = 2.00, 5
AUTO_FROM_HOUR_UTC = 8               # after the framework's morning refresh
AUTO_MIN_FREE_GBP = 15.00            # leave the singles room


def auto(client, picks_files: list[dict], events: list[dict], state_dir: Path, now: datetime,
         free_funds: float | None) -> tuple[list[str], float]:
    """The cycle's daily accas: once the budget has room and legs are in the window.
    Returns (event lines, stake placed). Only placed accas and errors are news."""
    if not AUTO or now.hour < AUTO_FROM_HOUR_UTC:
        return [], 0.0
    today = [r for r in _log(state_dir) if r.get("at", "").startswith(now.date().isoformat())
             and r.get("budget")]
    if any(r.get("status") == "ERROR" for r in today):
        return ["acca: an order error today — no more automatic accas until tomorrow"], 0.0
    if sum(r["stake"] for r in today if r.get("status") == "PLACED") >= DAILY_BUDGET_GBP - 1e-9:
        return [], 0.0
    if free_funds is not None and free_funds < AUTO_MIN_FREE_GBP:
        return [f"acca: waiting, Matchbook free funds £{free_funds:.2f} under £{AUTO_MIN_FREE_GBP:.0f}"], 0.0
    before = len(_log(state_dir))
    msg = batch(client, picks_files, events, AUTO_STAKE, AUTO_COUNT, state_dir, now, live=True)
    new = _log(state_dir)[before:]
    placed = sum(r["stake"] for r in new if r.get("status") == "PLACED")
    if not new:                                       # no legs yet: say so quietly
        return [f"acca: {msg.splitlines()[0][6:]}"], 0.0
    return msg.splitlines(), placed


def _log(state_dir: Path) -> list[dict]:
    f = state_dir / LOG_FILE
    return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else []


def batch(client, picks_files: list[dict], events: list[dict], stake: float, count: int,
          state_dir: Path, now: datetime, live: bool) -> str:
    """Up to `count` accas of LEGS legs, no match in two accas or in one already placed today,
    strongest first, inside DAILY_BUDGET_GBP."""
    today = now.date().isoformat()
    log = [r for r in _log(state_dir) if r.get("at", "").startswith(today) and r.get("status") == "PLACED"]
    spent = sum(r["stake"] for r in log if r.get("budget"))
    room = int((DAILY_BUDGET_GBP - spent + 1e-9) // stake)
    if room < count:
        count = max(room, 0)
    if count == 0:
        return f"ACCA BUDGET: £{spent:.2f} of today's £{DAILY_BUDGET_GBP:.2f} already placed — nothing placed"
    used = frozenset(x["event_id"] for r in log for x in r["legs"])
    out = []
    for _ in range(count):
        legs = strongest(picks_files, events, now, LEGS, used)
        if len(legs) < LEGS:
            out.append(f"ACCA: only {len(legs)} more eligible leg(s) — stopped")
            break
        out.append(place(client, legs, stake, state_dir, now, live, budget=True))
        used = used | {x["event_id"] for x in legs}
    return "\n".join(out)


def place(client, legs: list[dict], stake: float, state_dir: Path, now: datetime, live: bool,
          budget: bool = False) -> str:
    """Quote, then place (live) or only report (dry). Logs every attempt."""
    if not 0 < stake <= MAX_STAKE_GBP:
        raise ValueError(f"acca stake £{stake:.2f} outside (0, £{MAX_STAKE_GBP:.2f}]")
    if len(legs) < 2:
        return f"ACCA: only {len(legs)} eligible leg(s) on Matchbook — nothing placed"
    try:
        q = client.multiple_quote([x["runner_id"] for x in legs])
        odds = float(q["odds"])
    except Exception as e:                           # Matchbook refused a leg: skip this acca, say why
        return (f"ACCA NOT PRICED: {type(e).__name__}: {str(e)[:200]}\n"
                + "\n".join(f"  {x['event_name']} — {x['market_name']}: {x['runner_name']}" for x in legs))
    chance = math.prod(x["p"] for x in legs)
    rec = {"at": now.isoformat(timespec="seconds"), "legs": legs, "stake": stake, "odds": odds,
           "singles_product": round(math.prod(x["odds"] for x in legs), 4), "model_chance": round(chance, 4),
           "min_stake": q.get("min-stake"), "max_stake": q.get("max-stake"), "live": live, "budget": budget}
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
