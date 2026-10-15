"""
The Matchbook board — replaces the framework's bet365 board (framework standing
order 29, Architect 2026-10-15: "Matchbook should replace bet365 ... Matchbook
is doing everything automatically").

Sent once per picks date, the first cycle that sees the framework's
picks_<date>.json. Every framework single is shown with its Matchbook market
and price and what the bot does with it:

  BET    chance 80%+ and MEDIUM certainty on Matchbook (3-7 pts over break-even):
         the live rule; it is placed inside 12 h of kick-off if the price holds
  PAPER  priced 1.50-2.00 on Matchbook: the paper study records it, no money
  SKIP   anything else, with the reason

plus the rated-pool legs that also qualify for BET, and the day's accumulators
(placed by the cycle, £10 a day: multiples.batch).
"""
from __future__ import annotations

from datetime import datetime

from matchbook_live import config as C
from matchbook_live import framework_feed as F
from matchbook_live import paper, scanner


def verdict(p: float, b: dict) -> tuple[str, str]:
    """(BET / PAPER / SKIP, reason) for a framework chance p against a Matchbook book."""
    why = scanner.tradable(b)
    gap = p - (1 + C.COMMISSION) / b["best_back"]
    cert = F.certainty(gap)
    if not why and b["best_back"] > F.MAX_ODDS:
        why = f"odds above the {F.MAX_ODDS:.2f} cap"
    if not why and p >= F.MIN_CHANCE and cert == "MEDIUM" and gap > 0:
        return "BET", f"MEDIUM, edge {gap:+.1%}"
    if paper.BAND[0] <= b["best_back"] <= paper.BAND[1]:
        return "PAPER", f"edge {gap:+.1%}"
    if why:
        return "SKIP", why
    if p < F.MIN_CHANCE:
        return "SKIP", f"chance {p:.1%}, under {F.MIN_CHANCE:.0%}"
    if gap <= 0:
        return "SKIP", f"below Matchbook break-even ({gap:+.1%})"
    return "SKIP", f"{cert} certainty ({gap:+.1%})"


def _row(s: dict, events: list[dict]) -> tuple[str, str]:
    """(verdict, line) for one framework leg."""
    ko = scanner._dt(s.get("kickoff_utc"))
    when = ko.strftime("%H:%M") if ko else "--:--"
    label = f"{when} {s.get('fixture')} — {s.get('pick') or s.get('market')}"
    try:
        p = float(s.get("chance"))
    except (TypeError, ValueError):
        return "SKIP", f"  {label}: no framework chance — PENDING"
    mk = F.map_market(s.get("market") or "")
    if mk is None:
        return "SKIP", f"  {label} ({p:.0%}): market not on Matchbook"
    e = F.match_event(s.get("home") or "", s.get("away") or "", ko, events, s.get("kickoff"))
    if e is None:
        return "SKIP", f"  {label} ({p:.0%}): match not listed on Matchbook"
    m, r, note = F.find_runner(e, mk)
    b = scanner.runner_book(r) if r else None
    if b is None:
        return "SKIP", f"  {label} ({p:.0%}): {note or 'no back price'}"
    v, why = verdict(p, b)
    return v, f"  {label} ({p:.0%}) → {m.get('name')}: {r.get('name')} @ {b['best_back']:.2f} · {why}"


def render(picks_file: dict, events: list[dict], now: datetime) -> str:
    date = picks_file.get("date")
    groups: dict[str, list[str]] = {"BET": [], "PAPER": [], "SKIP": []}
    for s in picks_file.get("singles") or []:
        v, line = _row({**s, "pool": False}, events)
        groups[v].append(line)
    pool_bets = []
    for s in F.legs([picks_file]):
        if s.get("pool"):
            v, line = _row(s, events)
            if v == "BET":
                pool_bets.append(line)
    n = len(picks_file.get("singles") or [])
    out = [f"MATCHBOOK BOARD · {date} · replaces the bet365 board",
           f"{n} framework singles priced on Matchbook at {now:%H:%M} UTC (times UTC). "
           "BET = placed automatically inside 12 h of kick-off if the price holds; "
           "PAPER = recorded by the paper study, no money; SKIP = not bet.",
           "", f"BET ({len(groups['BET'])})", *(groups["BET"] or ["  none"])]
    if pool_bets:
        out += ["", f"BET — also from the framework's rated pool ({len(pool_bets)})", *pool_bets]
    out += ["", f"PAPER ({len(groups['PAPER'])})", *(groups["PAPER"] or ["  none"]),
            "", f"SKIP ({len(groups['SKIP'])})", *(groups["SKIP"] or ["  none"]),
            "", "ACCAS: up to 5 × £2 trebles a day (£10 budget) of Matchbook-eligible 75%+ legs, "
                "placed by the bot and reported when placed. Matchbook refuses Double Chance in "
                "multiples, so they are not the SportyBet/bet365 slips."]
    return "\n".join(out)


def due(pop: dict, picks_files: list[dict]) -> list[dict]:
    """Picks files whose board has not been sent yet (marks nothing)."""
    sent = set(pop.get("mb_board_sent") or [])
    return [f for f in picks_files if f.get("date") and f["date"] not in sent]


def mark_sent(pop: dict, date: str) -> None:
    pop["mb_board_sent"] = sorted({*(pop.get("mb_board_sent") or []), date})[-14:]
