"""
Self-improvement — the bot learns where it really has an edge.

1. CLOSING PRICE. Every run, each open position records Matchbook's best back
   price for its runner while the match has not kicked off. The last one
   before kick-off is the closing price. CLV = price taken / closing price - 1:
   beating the close is the honest early measure of skill, long before
   results settle the argument.

2. SCORECARD. Every bet sits in a bucket: source (oracle / framework pick /
   framework rated pool) x market (Match Odds, Total, Double Chance, ...).
   Per bucket: bets, settled, P&L, mean CLV.

3. EVIDENCE GATE. A bucket with 20+ bets carrying a closing price and a
   negative mean CLV is PAUSED for 7 days: no new bets from it. After 7 days
   it is let back in to be measured again. The gate can only stop bets,
   never add or enlarge one; the money rules stay as they are.

The scorecard and the graded ledger go into the state dir, the heartbeat and
the daily Telegram debrief, and are published for the framework to learn from.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

MIN_CLV_SAMPLE = 20
PAUSE_DAYS = 7


def bucket_of(source: str, fw_pool: bool, market_name: str) -> str:
    kind = "oracle" if source != "framework" else ("framework-pool" if fw_pool else "framework-pick")
    return f"{kind} / {market_name or '?'}"


def record_closing(hist: list[dict], events: list[dict], now: datetime) -> int:
    """Update close_back on open positions whose match has not started. Returns how many."""
    from matchbook_live import scanner
    by_runner = {}
    for e in events:
        start = scanner._dt(e.get("start"))
        if start is None or start <= now:
            continue
        for m in e.get("markets") or []:
            for r in m.get("runners") or []:
                by_runner[str(r.get("id"))] = r
    n = 0
    for h in hist:
        if h.get("status") != "OPEN":
            continue
        r = by_runner.get(str(h.get("runner_id")))
        b = scanner.runner_book(r) if r else None
        if b:
            h["close_back"] = b["best_back"]
            n += 1
    return n


def clv(h: dict) -> Optional[float]:
    if not h.get("close_back") or not h.get("avg_odds"):
        return None
    return h["avg_odds"] / h["close_back"] - 1


def card(hist: list[dict]) -> dict:
    out: dict = {}
    for h in hist:
        if h.get("status") == "VOID":
            continue
        b = out.setdefault(bucket_of(h.get("source", "oracle"), h.get("fw_pool", False), h.get("market_name", "")),
                           {"bets": 0, "settled": 0, "pnl": 0.0, "clv_n": 0, "clv_sum": 0.0})
        b["bets"] += 1
        if h.get("status") != "OPEN":
            b["settled"] += 1
            b["pnl"] = round(b["pnl"] + (h.get("pnl_gbp") or 0.0), 2)
        c = clv(h)
        if c is not None and h.get("status") != "OPEN":     # the close is final once the match is over
            b["clv_n"] += 1
            b["clv_sum"] += c
    for b in out.values():
        b["mean_clv"] = round(b["clv_sum"] / b["clv_n"], 4) if b["clv_n"] else None
        b.pop("clv_sum")
    return out


def update_pauses(pop: dict, hist: list[dict], now: datetime) -> list[str]:
    """Pause buckets that keep losing to the close; release them after PAUSE_DAYS."""
    pauses = pop.setdefault("paused_buckets", {})
    out = []
    for k, until in list(pauses.items()):
        if datetime.fromisoformat(until) <= now:
            del pauses[k]
            out.append(f"LEARNING: {k} back in after {PAUSE_DAYS} days — measured again")
    for k, b in card(hist).items():
        if k in pauses or b["clv_n"] < MIN_CLV_SAMPLE or b["mean_clv"] is None or b["mean_clv"] >= 0:
            continue
        pauses[k] = (now + timedelta(days=PAUSE_DAYS)).isoformat(timespec="seconds")
        out.append(f"LEARNING: {k} PAUSED {PAUSE_DAYS} days — mean CLV {b['mean_clv']:+.1%} "
                   f"over {b['clv_n']} bets (losing to Matchbook's closing price)")
    return out


def allowed(pop: dict, c: dict) -> bool:
    k = bucket_of(c.get("source", "oracle"), c.get("fw_pool", False), c.get("market_name", ""))
    return k not in pop.get("paused_buckets", {})


def render(hist: list[dict], pop: dict) -> list[str]:
    rows = []
    for k, b in sorted(card(hist).items()):
        clv_txt = "PENDING" if b["mean_clv"] is None else f"{b['mean_clv']:+.1%} ({b['clv_n']})"
        flag = "  PAUSED" if k in pop.get("paused_buckets", {}) else ""
        rows.append(f"  {k}: {b['bets']} bets, {b['settled']} settled, P&L £{b['pnl']:+.2f}, CLV {clv_txt}{flag}")
    return rows or ["  no bets yet"]
