"""
Matchbook LIVE agent — constants.

LIVE CAPITAL. This package logs in to Matchbook with the Architect's account
and places real back offers. It is the one agent the Architect carved out of
the capital bright line on 2026-10-14 (see CLAUDE.md, "Capital bright line —
Matchbook agent amendment"). Nothing else in the workspace may route a stake.

Orders go out only when MATCHBOOK_LIVE=1 is set on the runner. Without it a
cycle scans, evaluates and logs what it WOULD do, and places nothing.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------- endpoints
API_URL = "https://api.matchbook.com"
LOGIN_PATH = "/bpapi/rest/security/session"
SESSION_MAX_AGE_H = 5.0        # Matchbook sessions last ~6 h; re-login before that

# Pasting into `gh secret set` on Windows can carry a stray \r or space; Matchbook
# then answers "Incorrect credentials". Strip them, and let --check say if it did.
_RAW_USERNAME = os.getenv("MATCHBOOK_USERNAME", "")
_RAW_PASSWORD = os.getenv("MATCHBOOK_PASSWORD", "")
USERNAME = _RAW_USERNAME.strip()
PASSWORD = _RAW_PASSWORD.strip()
CREDENTIALS_NOTE = (f"username {len(USERNAME)} chars{' (an email address)' if '@' in USERNAME else ''}, "
                    f"password {len(PASSWORD)} chars; stray whitespace stripped from "
                    + (", ".join(n for n, raw, clean in (("username", _RAW_USERNAME, USERNAME),
                                                        ("password", _RAW_PASSWORD, PASSWORD)) if raw != clean)
                       or "neither"))
LIVE = os.getenv("MATCHBOOK_LIVE", "") == "1"

# --------------------------------------------------------------- scanner
SPORT_IDS = os.getenv("MB_SPORT_IDS", "15")            # 15 = soccer on Matchbook
MARKET_NAMES = tuple(x.strip().lower() for x in
                     os.getenv("MB_MARKET_NAMES", "Match Odds").split(",") if x.strip())
PER_PAGE = 50
MAX_EVENTS = 400
PAGE_SLEEP_S = 0.5
MIN_HOURS_TO_START = 2
MAX_DAYS_TO_START = 7
MAX_SPREAD = 0.04              # lay implied - back implied
MIN_BACK_DEPTH_GBP = 15.0      # available to back at the best two prices
MIN_IMPLIED = 0.10             # back odds 10.0 and shorter
MAX_IMPLIED = 0.88             # back odds 1.14 and longer

# --------------------------------------------------------------- risk gate
COMMISSION = float(os.getenv("MB_COMMISSION", "0.02"))   # charged on matched stake, win or lose
MIN_EDGE = 0.08                # strictly greater than 8 points over break-even
MIN_CONFIDENCE = 0.70
KELLY_FRACTION = 0.50
MAX_STAKE_FRACTION = 0.06
MAX_PORTFOLIO_EXPOSURE = 0.65
MIN_ORDER_GBP = 1.00
CASH_BUFFER_GBP = 1.00

# --------------------------------------------------------------- delta cache
CACHE_HOURS = 4
CACHE_MIN_MOVE = 0.03          # implied-probability move that forces a re-ask

# --------------------------------------------------------------- heartbeat lineage
# The AI Survivor lineage (framework standing order 23) carried onto Matchbook.
# AGENT_CAPITAL_GBP is the whole of what this agent may ever put at risk from
# outside its own winnings: genesis is the only money that comes in, and a
# child is funded from its parent's cash, never from the account.
AGENT_CAPITAL_GBP = 50.00
GENESIS_BANKROLL_GBP = AGENT_CAPITAL_GBP
SURVIVAL_FLOOR_GBP = 5.00
MITOSIS_MULTIPLE = 2.0         # equity >= 2x genesis and cash >= genesis -> split off a child
MAX_LINEAGES = 16
MIN_SETTLED_FOR_BURN_RULE = 10
BURN_WINDOW_HOURS = 48

# --------------------------------------------------------------- oracle (blind)
ORACLE_BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
ORACLE_API_KEY = os.getenv("OPENAI_API_KEY", "")
ORACLE_MODEL = os.getenv("OPENAI_MODEL", "")
ORACLE_BUDGET_S = 25 * 60     # stop asking after this, so the run reaches allocate + save inside the job limit
_cost = os.getenv("ORACLE_GBP_PER_1K_TOKENS", "").strip()
ORACLE_GBP_PER_1K_TOKENS: float | None = float(_cost) if _cost else None

STATE_DIR = Path(os.getenv("MB_STATE_DIR", Path(__file__).parent / "data"))
STOP_FILE = "STOP"             # create <state dir>/STOP to halt new orders at once
