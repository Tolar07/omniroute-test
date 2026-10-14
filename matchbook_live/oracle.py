"""
Blind oracle — Blue (wins) vs Red (does not win) vs Judge through an
OpenAI-compatible gateway (OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL).

The question for every candidate: does this SELECTION win this Matchbook market?

Information barrier: the brief is built from a WHITELIST of non-price fields
(event, kick-off, market, selection, the other selections). No odds, volume or
liquidity ever reaches a prompt, so the model cannot anchor on the market.

No gateway configured, a failed call, or a judge answer that is not valid JSON
in range -> None (PENDING). Nothing trades on a missing probability (HR35).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional

import requests

from matchbook_live import config as C

BLIND_FIELDS = ("event_name", "start", "market_name", "runner_name", "other_runners")

BLUE = ("You are the BLUE team. Build the strongest evidence-based case that the SELECTION "
        "wins this betting-exchange market (90-minute result unless the market says otherwise). "
        "End with 'BLUE ESTIMATE: <probability 0-1>'.")
RED = ("You are the RED team. Attack the Blue case: weak assumptions, base rates, team news, "
       "home advantage, draw likelihood. Argue that the SELECTION does not win. End with "
       "'RED ESTIMATE: <probability the selection wins 0-1>'.")
JUDGE = ("You are the JUDGE. Weigh both cases. Reply with ONLY a JSON object: "
         '{"true_prob_yes": <0-1>, "confidence": <0-1>, "reasoning": "<two sentences>"}. '
         "true_prob_yes is the chance the SELECTION wins. confidence is how sure you are the "
         "probability is right, not how likely the selection is to win.")


@dataclass
class OracleResult:
    true_prob: float
    confidence: float
    reasoning: str
    tokens: int
    cost_gbp: Optional[float]      # None = cost PENDING (no rate configured)


def blind_brief(candidate: dict) -> str:
    def show(v):
        return ", ".join(v) if isinstance(v, list) else str(v or "").strip()
    return "\n".join(f"{k.replace('_', ' ').upper()}: {show(candidate.get(k))}" for k in BLIND_FIELDS)


def _chat(system: str, user: str, post: Callable = requests.post) -> tuple[str, int]:
    r = post(f"{C.ORACLE_BASE_URL}/chat/completions",
             headers={"Authorization": f"Bearer {C.ORACLE_API_KEY}"} if C.ORACLE_API_KEY else {},
             json={"model": C.ORACLE_MODEL, "temperature": 0.2,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]},
             timeout=120)
    r.raise_for_status()
    d = r.json()
    return d["choices"][0]["message"]["content"], int((d.get("usage") or {}).get("total_tokens") or 0)


def parse_judge(text: str) -> Optional[tuple[float, float, str]]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        p, c = float(d["true_prob_yes"]), float(d["confidence"])
    except (ValueError, KeyError, TypeError):
        return None
    if not (0.0 <= p <= 1.0 and 0.0 <= c <= 1.0):
        return None
    return p, c, str(d.get("reasoning", ""))[:400]


def available() -> bool:
    return bool(C.ORACLE_BASE_URL and C.ORACLE_MODEL)


def evaluate(candidate: dict, chat: Callable = _chat) -> Optional[OracleResult]:
    if not available() and chat is _chat:
        return None
    brief = blind_brief(candidate)
    try:
        blue, t1 = chat(BLUE, brief)
        red, t2 = chat(RED, f"{brief}\n\nBLUE CASE:\n{blue}")
        judge, t3 = chat(JUDGE, f"{brief}\n\nBLUE CASE:\n{blue}\n\nRED CASE:\n{red}")
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None
    parsed = parse_judge(judge)
    if parsed is None:
        return None
    tokens = t1 + t2 + t3
    cost = None if C.ORACLE_GBP_PER_1K_TOKENS is None else round(tokens / 1000 * C.ORACLE_GBP_PER_1K_TOKENS, 6)
    return OracleResult(parsed[0], parsed[1], parsed[2], tokens, cost)
