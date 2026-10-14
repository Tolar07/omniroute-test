"""
Live execution — fill-and-kill on Matchbook.

A back offer goes in at the best back price on the book. Whatever matches at
once is the position; anything left unmatched is cancelled straight away, so
no order ever rests on the exchange.

Settlement reads Matchbook's settled-bets report. A position is paid back its
recorded cost plus the exchange's own net profit-and-loss for that offer
(commission already taken off), so the ledger follows the exchange even if the
matched amount recorded at entry was off by a race with the cancel.
"""
from __future__ import annotations

from typing import Optional


def _matched(offer: dict) -> tuple[float, float]:
    """(matched stake, stake-weighted odds) from an offer's matched-bets."""
    bets = offer.get("matched-bets") or []
    stake = sum(float(b.get("stake") or 0) for b in bets)
    if stake <= 0:
        return 0.0, 0.0
    odds = sum(float(b.get("stake") or 0) * float(b.get("decimal-odds") or b.get("odds") or 0)
               for b in bets) / stake
    return round(stake, 2), round(odds, 4)


def back_fak(client, runner_id, odds: float, stake: float) -> tuple[Optional[dict], str]:
    """Returns (fill, note). fill is None when nothing matched."""
    o = client.back(runner_id, odds, stake)
    oid, status = o.get("id"), o.get("status")
    if status == "failed" or oid is None:
        return None, f"offer failed: {str(o)[:200]}"
    matched, avg = _matched(o)
    note, cancel_pending = status or "?", False
    if status != "matched" and float(o.get("remaining") or 0) > 0:
        try:
            client.cancel(oid)
            note += " -> unmatched part cancelled"
        except Exception as e:                       # the next run retries the cancel
            note += f" -> CANCEL FAILED ({type(e).__name__}); retried next run"
            cancel_pending = True
        try:
            m2, a2 = _matched(client.offer(oid))
            if m2 > matched:
                matched, avg = m2, a2
        except Exception:
            pass
    if matched <= 0 and not cancel_pending:
        return None, note + ", nothing matched"
    return {"offer_id": oid, "matched_gbp": matched, "avg_odds": avg or odds,
            "cancel_pending": cancel_pending}, note


def settled_by_offer(client, market_ids: list) -> dict:
    """offer-id -> {'net': net P&L incl. commission, 'stake': matched stake, 'result': ...}."""
    out: dict = {}
    for m in client.settled(market_ids):
        for sel in m.get("selections") or []:
            for b in sel.get("bets") or []:
                key = str(b.get("offer-id"))
                e = out.setdefault(key, {"net": 0.0, "stake": 0.0, "results": set()})
                e["net"] += float(b.get("net-profit-and-loss") or 0)
                e["stake"] += float(b.get("stake") or 0)
                e["results"].add(b.get("result") or "?")
    for e in out.values():
        r = e.pop("results")
        e["result"] = r.pop() if len(r) == 1 else "MIXED"
        e["net"], e["stake"] = round(e["net"], 2), round(e["stake"], 2)
    return out

