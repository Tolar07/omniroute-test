"""
Polymarket PAPER engine — constants.

PAPER ONLY. This package reads Polymarket's public APIs (no account, no key)
and simulates fills against the live order book. It holds no private key,
signs nothing, sends nothing on-chain and never posts an order. That is the
framework's capital bright line ("no code routes a real stake"), which does
not yield to directives — see Tolar07/framework CLAUDE.md.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------- endpoints
# Read-only, unauthenticated. Order placement (POST /order) is deliberately
# absent from this package.
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
GEOBLOCK_URL = "https://polymarket.com/api/geoblock"

# --------------------------------------------------------------- scanner
MAX_MARKETS = 2000            # markets read per scan
PAGE_SIZE = 100              # Gamma's own cap per page
PAGE_SLEEP_S = 0.25           # keeps public polling well under 100 req/min per page burst
MAX_BOOK_FETCHES = 150        # order books read per scan (two per market)
MIN_HOURS_TO_RESOLVE = 2
MAX_DAYS_TO_RESOLVE = 14
MAX_SPREAD = 0.04
MIN_TOP2_ASK_DEPTH_USD = 15.0
MIN_ASK = 0.10
MAX_ASK = 0.88

# --------------------------------------------------------------- risk gate
MIN_EDGE = 0.08               # strictly greater than 8 points
MIN_CONFIDENCE = 0.70
KELLY_FRACTION = 0.50
MAX_STAKE_FRACTION = 0.06
MAX_PORTFOLIO_EXPOSURE = 0.65
MIN_ORDER_USD = 1.00
CASH_BUFFER_USD = 1.00

# --------------------------------------------------------------- delta cache
CACHE_HOURS = 4
CACHE_MIN_MOVE = 0.03

# --------------------------------------------------------------- execution (paper)
TAKE_PROFIT_BID = 0.985

# --------------------------------------------------------------- heartbeat lineage
# The AI Survivor lineage (framework standing order 23) carried onto Polymarket.
# Money rules follow the Polymarket spec: a lineage dies at the survival floor,
# not on one loss, because Kelly sizing never stakes the whole bankroll.
GENESIS_BANKROLL_USD = 66.00  # paper; ~GBP 50
SURVIVAL_FLOOR_USD = 6.50     # ~GBP 5
MITOSIS_MULTIPLE = 2.0        # equity >= 2x genesis and cash >= genesis -> split off a child
MAX_LINEAGES = 16             # same cap as engine/survivor.py
MIN_SETTLED_FOR_BURN_RULE = 10
BURN_WINDOW_HOURS = 48

# --------------------------------------------------------------- oracle (blind)
# OpenAI-compatible gateway (OmniRoute). Unset -> oracle PENDING, nothing trades.
ORACLE_BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
ORACLE_API_KEY = os.getenv("OPENAI_API_KEY", "")
ORACLE_MODEL = os.getenv("OPENAI_MODEL", "")
# USD per 1,000 tokens. Unset -> burn reads PENDING (never a made-up price).
_cost = os.getenv("ORACLE_USD_PER_1K_TOKENS", "").strip()
ORACLE_USD_PER_1K_TOKENS: float | None = float(_cost) if _cost else None

STATE_DIR = Path(os.getenv("PM_PAPER_STATE_DIR", Path(__file__).parent / "data"))
