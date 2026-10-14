"""
Deterministic risk gate — the LLM never sizes a bet.

  edge      = oracle chance - executable ask, on the better side
  pass      = edge > 8 pts AND confidence >= 0.70 AND ask in [0.10, 0.88]
              AND top-2 ask depth >= $15 AND no open position on the event
  kelly     = (p - m) / (1 - m)
  stake     = equity x min(6%, 0.5 x kelly), capped by cash - $1 and by the
              room left under the 65% exposure ceiling; < $1 -> no trade
  limit     = ask + 1 tick (marketable FAK), rounded to the tick
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_DOWN, Decimal

from polymarket_paper import config as C


@dataclass
class TradeDecision:
    execute: bool
    side: str             # "YES", "NO" or "PASS"
    edge: float
    kelly_raw: float
    capped_fraction: float
    stake_usd: float
    limit_price: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _pass(reason: str, edge: float = 0.0, kelly: float = 0.0, frac: float = 0.0) -> TradeDecision:
    return TradeDecision(False, "PASS", round(edge, 4), round(kelly, 4), round(frac, 4), 0.0, 0.0, reason)


def round_to_tick(price: float, tick_size: str) -> float:
    tick = Decimal(str(tick_size))
    p = Decimal(str(price))
    rounded = (p / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick
    return float(max(tick, min(Decimal("1") - tick, rounded)))


def evaluate(*, true_prob_yes: float, confidence: float, book_yes: dict, book_no: dict,
             tick_size: str, equity_usd: float, cash_usd: float, deployed_usd: float,
             event_held: bool) -> TradeDecision:
    if event_held:
        return _pass("Event lock: a position on this event is already open")
    max_deployed = equity_usd * C.MAX_PORTFOLIO_EXPOSURE
    if deployed_usd >= max_deployed:
        return _pass("65% exposure ceiling reached")
    if confidence < C.MIN_CONFIDENCE:
        return _pass(f"Confidence {confidence:.2f} below {C.MIN_CONFIDENCE:.2f}")
    if not (0.01 <= true_prob_yes <= 0.99):
        return _pass("Oracle probability out of bounds")

    sides = [("YES", true_prob_yes, book_yes), ("NO", 1.0 - true_prob_yes, book_no)]
    side, p, book = max(sides, key=lambda s: s[1] - s[2]["best_ask"])
    m = book["best_ask"]
    edge = p - m

    if not (C.MIN_ASK <= m <= C.MAX_ASK):
        return _pass(f"{side} ask {m:.3f} outside [{C.MIN_ASK:.2f}, {C.MAX_ASK:.2f}]", edge)
    if book["top2_ask_depth_usd"] < C.MIN_TOP2_ASK_DEPTH_USD:
        return _pass(f"{side} top-2 depth ${book['top2_ask_depth_usd']:.2f} under "
                     f"${C.MIN_TOP2_ASK_DEPTH_USD:.0f}", edge)
    if edge <= C.MIN_EDGE:
        return _pass(f"Edge {edge:+.2%} not greater than {C.MIN_EDGE:.0%}", edge)

    kelly = (p - m) / (1.0 - m)
    frac = min(C.MAX_STAKE_FRACTION, max(0.0, kelly * C.KELLY_FRACTION))
    stake = min(equity_usd * frac,
                max(0.0, cash_usd - C.CASH_BUFFER_USD),
                max(0.0, max_deployed - deployed_usd))
    stake = float(Decimal(str(stake)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
    if stake < C.MIN_ORDER_USD:
        return _pass(f"Stake ${stake:.2f} under the ${C.MIN_ORDER_USD:.2f} minimum", edge, kelly, frac)

    limit = round_to_tick(m + float(tick_size), tick_size)
    return TradeDecision(True, side, round(edge, 4), round(kelly, 4), round(frac, 4), stake, limit,
                         "Approved by the deterministic gate")
