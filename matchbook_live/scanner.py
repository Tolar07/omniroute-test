"""
Market scanner — Matchbook events with prices, read without logging in.

A candidate is one runner in one market: "back this runner" is the YES side.
Every price comes from a fetch in this run (HR59). A page that fails to load
ends the scan with what was read; nothing is filled in.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from matchbook_live import config as C


def _dt(s: Optional[str]) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
    except ValueError:
        return None


def runner_book(runner: dict) -> Optional[dict]:
    """Best back (highest odds you can take) and best lay, with back depth."""
    backs = sorted(((float(p["odds"]), float(p.get("available-amount") or 0))
                    for p in runner.get("prices") or [] if p.get("side") == "back"), reverse=True)
    lays = sorted(float(p["odds"]) for p in runner.get("prices") or [] if p.get("side") == "lay")
    if not backs or backs[0][0] <= 1.0:
        return None
    best_back = backs[0][0]
    best_lay = lays[0] if lays else None
    spread = None if best_lay is None else round(1 / best_back - 1 / best_lay, 6)
    return {"best_back": best_back, "best_lay": best_lay, "implied": round(1 / best_back, 6),
            "spread": spread, "back_depth_gbp": round(sum(a for _, a in backs[:2]), 2), "backs": backs}


def tradable(b: Optional[dict]) -> Optional[str]:
    """None if the book is fit to trade, else why not."""
    if not b:
        return "no back price"
    if b["spread"] is None or b["spread"] > C.MAX_SPREAD:
        return "back-lay spread too wide" if b["spread"] is not None else "no lay price"
    if not (C.MIN_IMPLIED <= b["implied"] <= C.MAX_IMPLIED):
        return f"odds {b['best_back']:.2f} outside the window"
    if b["back_depth_gbp"] < C.MIN_BACK_DEPTH_GBP:
        return f"back depth £{b['back_depth_gbp']:.0f} under £{C.MIN_BACK_DEPTH_GBP:.0f}"
    return None


def candidate(e: dict, m: dict, r: dict, runners: list[dict]) -> dict:
    return {"event_id": str(e["id"]), "event_name": e.get("name") or "",
            "start": e.get("start"), "market_id": str(m["id"]),
            "market_name": m.get("name") or "", "runner_id": r["id"],
            "runner_name": r.get("name") or "",
            "other_runners": [x.get("name") or "" for x in runners if x is not r],
            "book": runner_book(r)}


def in_window(e: dict, now: datetime) -> bool:
    start = _dt(e.get("start"))
    return (start is not None and e.get("status") == "open"
            and now + timedelta(hours=C.MIN_HOURS_TO_START) <= start
            <= now + timedelta(days=C.MAX_DAYS_TO_START))


def candidates_from_event(e: dict, now: datetime) -> list[dict]:
    """Oracle candidates: every tradable runner in the MARKET_NAMES markets."""
    if not in_window(e, now):
        return []
    out = []
    for m in e.get("markets") or []:
        if m.get("status") != "open" or (m.get("name") or "").strip().lower() not in C.MARKET_NAMES:
            continue
        runners = [r for r in m.get("runners") or [] if r.get("status") == "open"]
        for r in runners:
            if tradable(runner_book(r)) is None:
                out.append(candidate(e, m, r, runners))
    return out


def fetch_events(client, max_events: int = C.MAX_EVENTS, sleep=time.sleep) -> tuple[list[dict], dict]:
    stats = {"events_read": 0, "page_errors": 0}
    events: list[dict] = []
    offset = 0
    while offset < max_events:
        try:
            d = client.events(offset=offset)
        except Exception:
            stats["page_errors"] += 1
            break
        evs = d.get("events") or []
        if not evs:
            break
        events += evs
        offset += len(evs)
        if offset >= int(d.get("total") or 0):
            break
        sleep(C.PAGE_SLEEP_S)
    stats["events_read"] = len(events)
    return events, stats


def scan(client, now: Optional[datetime] = None, max_events: int = C.MAX_EVENTS,
         sleep=time.sleep) -> tuple[list[dict], dict, list[dict]]:
    """Returns (oracle candidates, stats, every event read)."""
    now = now or datetime.now(timezone.utc)
    events, stats = fetch_events(client, max_events, sleep)
    out = [c for e in events for c in candidates_from_event(e, now)]
    stats["candidates"] = len(out)
    return out, stats, events
