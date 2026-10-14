"""
Market scanner — Gamma market list + CLOB order books, read-only.

Every price here comes from a fetch in this run (HR59). A book that fails to
load drops the market from this scan; nothing is filled in.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import requests

from polymarket_paper import config as C

HEADERS = {"User-Agent": "olp-xdv-polymarket-paper/1.0 (read-only)"}


def _get(url: str, params: Optional[dict] = None, timeout: float = 20.0):
    r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_markets(max_markets: int = C.MAX_MARKETS, now: Optional[datetime] = None,
                  get=_get, sleep=time.sleep) -> list[dict]:
    """Open markets ending inside the resolution window. Gamma caps a page at
    100 whatever `limit` asks for, so page until an empty page."""
    now = now or datetime.now(timezone.utc)
    window = {"end_date_min": (now + timedelta(hours=C.MIN_HOURS_TO_RESOLVE)).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "end_date_max": (now + timedelta(days=C.MAX_DAYS_TO_RESOLVE)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    out: list[dict] = []
    seen: set = set()
    while len(out) < max_markets:
        page = get(f"{C.GAMMA_API_URL}/markets",
                   {"active": "true", "closed": "false", "limit": C.PAGE_SIZE,
                    "offset": len(out), **window})
        fresh = [m for m in page or [] if m.get("id") not in seen]
        if not fresh:
            break
        seen.update(m.get("id") for m in fresh)
        out.extend(fresh)
        sleep(C.PAGE_SLEEP_S)
    return out[:max_markets]


def fetch_market(market_id: str, get=_get) -> dict:
    return get(f"{C.GAMMA_API_URL}/markets/{market_id}")


def fetch_book(token_id: str, get=_get) -> dict:
    return get(f"{C.CLOB_API_URL}/book", {"token_id": token_id})


def parse_book(book: dict) -> Optional[dict]:
    """Best bid/ask and levels from a CLOB book.

    The CLOB lists bids ascending and asks descending, so the best of each is
    the LAST entry — take max/min rather than trusting order."""
    try:
        bids = sorted(((float(b["price"]), float(b["size"])) for b in book.get("bids", [])),
                      reverse=True)
        asks = sorted((float(a["price"]), float(a["size"])) for a in book.get("asks", []))
    except (KeyError, TypeError, ValueError):
        return None
    if not asks:
        return None
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0]
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": None if best_bid is None else round(best_ask - best_bid, 6),
        "top2_ask_depth_usd": round(sum(p * s for p, s in asks[:2]), 2),
        "bids": bids,
        "asks": asks,
    }


def _jl(v):
    return json.loads(v) if isinstance(v, str) else (v or [])


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def prefilter(m: dict, now: datetime) -> Optional[dict]:
    """Cheap filter on Gamma fields, before any book is read."""
    if not m.get("enableOrderBook") or not m.get("acceptingOrders", True):
        return None
    outcomes = _jl(m.get("outcomes"))
    tokens = _jl(m.get("clobTokenIds"))
    if len(tokens) != 2 or [o.lower() for o in outcomes] != ["yes", "no"]:
        return None
    end = _parse_dt(m.get("endDate"))
    if end is None:
        return None
    if not (now + timedelta(hours=C.MIN_HOURS_TO_RESOLVE) <= end
            <= now + timedelta(days=C.MAX_DAYS_TO_RESOLVE)):
        return None
    spread = m.get("spread")
    if spread is not None and float(spread) > C.MAX_SPREAD:
        return None
    events = m.get("events") or [{}]
    return {
        "market_id": str(m["id"]),
        "condition_id": m.get("conditionId"),
        "event_id": str(events[0].get("id") or m["id"]),
        "event_title": events[0].get("title") or "",
        "question": m.get("question") or "",
        "description": m.get("description") or "",
        "end_date": m.get("endDate"),
        "token_yes": tokens[0],
        "token_no": tokens[1],
        "tick_size": str(m.get("orderPriceMinTickSize") or "0.01"),
        "neg_risk": bool(m.get("negRisk")),
        "category": (m.get("category") or "").lower(),
    }


def scan(now: Optional[datetime] = None, max_markets: int = C.MAX_MARKETS,
         get: Callable = _get, sleep=time.sleep) -> tuple[list[dict], dict]:
    """Returns (candidates with both books, stats)."""
    now = now or datetime.now(timezone.utc)
    markets = fetch_markets(max_markets, now, get=get, sleep=sleep)
    pre = [c for c in (prefilter(m, now) for m in markets) if c]
    stats = {"markets_read": len(markets), "in_window": len(pre),
             "books_read": 0, "book_errors": 0, "candidates": 0}
    out = []
    for c in pre:
        if stats["books_read"] + 2 > C.MAX_BOOK_FETCHES:
            break
        try:
            yes = parse_book(fetch_book(c["token_yes"], get=get))
            no = parse_book(fetch_book(c["token_no"], get=get))
        except (requests.RequestException, ValueError):
            stats["book_errors"] += 1
            continue
        finally:
            stats["books_read"] += 2
            sleep(C.PAGE_SLEEP_S)
        if not yes or not no or yes["spread"] is None or yes["spread"] > C.MAX_SPREAD:
            continue
        if not any(C.MIN_ASK <= b["best_ask"] <= C.MAX_ASK
                   and b["top2_ask_depth_usd"] >= C.MIN_TOP2_ASK_DEPTH_USD for b in (yes, no)):
            continue
        c["book_yes"], c["book_no"] = yes, no
        c["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        out.append(c)
    stats["candidates"] = len(out)
    return out, stats
