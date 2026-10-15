"""
Deterministic risk gate — the LLM never sizes a bet. Back bets only, so the
most a position can lose is its stake (plus commission).

Matchbook charges commission on matched stake whether the bet wins or loses
(COMMISSION, ~2%), so for decimal odds o and oracle chance p:

  break-even = (1 + c) / o
  edge       = p - break-even
  pass       = edge > min_edge (8 pts oracle, 3 framework) AND confidence >= 0.70 AND implied 1/o in [0.10, 0.88]
               AND best-two back depth >= £15 AND no open position on the event
  kelly      = (p*b - (1-p)*(1+c)) / (b*(1+c)),  b = o - 1 - c
  stake      = equity x min(6%, 0.5 x kelly), capped by cash - £1, by the room
               left under the 65% exposure ceiling and by Matchbook free funds
               - £1; under £1 -> no trade
  odds       = the best back price on the book now (taken, not improved)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Optional

from matchbook_live import config as C


@dataclass
class TradeDecision:
    execute: bool
    edge: float
    kelly_raw: float
    capped_fraction: float
    stake_gbp: float
    odds: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _pass(reason: str, edge: float = 0.0, kelly: float = 0.0, frac: float = 0.0) -> TradeDecision:
    return TradeDecision(False, round(edge, 4), round(kelly, 4), round(frac, 4), 0.0, 0.0, reason)


def evaluate(*, true_prob: float, confidence: float, book: dict, equity_gbp: float, cash_gbp: float,
             deployed_gbp: float, event_held: bool, free_funds_gbp: Optional[float] = None,
             commission: float = C.COMMISSION, min_edge: float = C.MIN_EDGE) -> TradeDecision:
    if event_held:
        return _pass("Event lock: a position on this event is already open")
    max_deployed = equity_gbp * C.MAX_PORTFOLIO_EXPOSURE
    if deployed_gbp >= max_deployed:
        return _pass("65% exposure ceiling reached")
    if confidence < C.MIN_CONFIDENCE:
        return _pass(f"Confidence {confidence:.2f} below {C.MIN_CONFIDENCE:.2f}")
    if not (0.01 <= true_prob <= 0.99):
        return _pass("Oracle probability out of bounds")

    o = book["best_back"]
    c = commission
    edge = true_prob - (1 + c) / o
    if not (C.MIN_IMPLIED <= 1 / o <= C.MAX_IMPLIED):
        return _pass(f"Odds {o:.2f} outside the {C.MIN_IMPLIED:.2f}-{C.MAX_IMPLIED:.2f} implied window", edge)
    if book["back_depth_gbp"] < C.MIN_BACK_DEPTH_GBP:
        return _pass(f"Back depth £{book['back_depth_gbp']:.2f} under £{C.MIN_BACK_DEPTH_GBP:.0f}", edge)
    if edge <= min_edge:
        return _pass(f"Edge {edge:+.2%} not greater than {min_edge:.0%}", edge)

    b = o - 1 - c
    kelly = (true_prob * b - (1 - true_prob) * (1 + c)) / (b * (1 + c))
    frac = min(C.MAX_STAKE_FRACTION, max(0.0, kelly * C.KELLY_FRACTION))
    caps = [equity_gbp * frac, cash_gbp - C.CASH_BUFFER_GBP, max_deployed - deployed_gbp]
    if free_funds_gbp is not None:
        caps.append(free_funds_gbp - C.CASH_BUFFER_GBP)
    stake = max(0.0, min(caps))
    stake = float(Decimal(str(stake)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))
    if stake < C.MIN_ORDER_GBP:
        return _pass(f"Stake £{stake:.2f} under the £{C.MIN_ORDER_GBP:.2f} minimum", edge, kelly, frac)
    return TradeDecision(True, round(edge, 4), round(kelly, 4), round(frac, 4), stake, o,
                         "Approved by the deterministic gate")
