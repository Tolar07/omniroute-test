"""
Paper execution — simulated against the live book. No order is ever sent.

buy_fak  : walk the asks from best up to the limit price, spend up to the stake
           (Fill-and-Kill: take what is there, never rest an order).
sell_fak : walk the bids from best down, sell up to the shares held.
settle   : a resolved market pays $1 a winning share, $0 a losing one.
"""
from __future__ import annotations

from typing import Optional


def buy_fak(asks: list[tuple[float, float]], stake_usd: float, limit_price: float) -> Optional[dict]:
    spent = shares = 0.0
    for price, size in sorted(asks):
        if price > limit_price + 1e-12 or spent >= stake_usd - 1e-9:
            break
        take = min(size, (stake_usd - spent) / price)
        spent += take * price
        shares += take
    if shares <= 0 or spent < 1.0 - 1e-9:
        return None
    return {"shares": round(shares, 4), "cost_usd": round(spent, 2),
            "avg_price": round(spent / shares, 4)}


def sell_fak(bids: list[tuple[float, float]], shares: float, min_price: float = 0.0) -> Optional[dict]:
    sold = proceeds = 0.0
    for price, size in sorted(bids, reverse=True):
        if price < min_price or sold >= shares - 1e-9:
            break
        take = min(size, shares - sold)
        sold += take
        proceeds += take * price
    if sold <= 0:
        return None
    return {"shares": round(sold, 4), "proceeds_usd": round(proceeds, 2),
            "avg_price": round(proceeds / sold, 4)}


def resolution(market: dict) -> Optional[str]:
    """'YES' / 'NO' when Gamma shows the market closed with a 1/0 price, else None."""
    import json
    if not market.get("closed"):
        return None
    prices = market.get("outcomePrices")
    prices = json.loads(prices) if isinstance(prices, str) else prices
    try:
        yes, no = (float(x) for x in prices)
    except (TypeError, ValueError):
        return None
    if yes >= 0.999 and no <= 0.001:
        return "YES"
    if no >= 0.999 and yes <= 0.001:
        return "NO"
    if abs(yes - 0.5) < 1e-6 and abs(no - 0.5) < 1e-6 and market.get("umaResolutionStatus") == "resolved":
        return "SPLIT"              # 50/50 resolution: $0.50 a share
    return None                     # closed but not final -> wait
