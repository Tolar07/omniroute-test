"""
Framework feed — the OLP XDV framework's picks, placed on Matchbook.

Architect directive 2026-10-15: "All the bets you've created and all the bets
you'll be creating has to be feeding Matchbook."

The framework (Tolar07/framework, public) writes output/picks/picks_<date>.json
every day. Every acca, 50+ and mega leg is also one of that day's singles, so
the singles are the whole book. Matchbook has no accumulators: each leg goes
on as its own single.

For each single:
  1. translate the SportyBet market to a Matchbook market + runner
       SB:18 total=X Over/Under X  -> "Total" (line X)   OVER X / UNDER X
       OVER_2_5                     -> "Total" (line 2.5) OVER 2.5
       SB:10 Home or Draw/...       -> "Double Chance"    "<home> or Draw" ...
       SB:16 hcp=H Home/Away (±h)   -> "Handicap"         "<team> ±h"  (half lines only)
       SB:1  Home/Draw/Away         -> "Match Odds"
       SB:29 Yes/No                 -> "Both Teams To Score"
       SB:11 Home/Away              -> "Draw No Bet"
     Anything else (team totals, win to nil, multigoals, combos, 3-way
     handicap) has no Matchbook twin and is skipped, with the reason.
  2. find the match on Matchbook: kick-off within 20 minutes, both team names
     alike. No confident match -> skipped, never guessed (HR35).
  3. hand it to the same risk gate as everything else, with the framework's
     own probability (`chance`) against Matchbook's best back price, net of
     commission. ½-Kelly sizes it; no edge at Matchbook's price -> no stake.

The framework itself is untouched and still never stakes.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Callable, Optional

import requests

from matchbook_live import config as C
from matchbook_live import scanner

PICKS_URL = "https://raw.githubusercontent.com/Tolar07/framework/main/output/picks/picks_{date}.json"
KICKOFF_TOLERANCE = timedelta(minutes=20)
MIN_TO_KICKOFF = timedelta(minutes=10)     # never bet a leg about to go in-play
MAX_TO_KICKOFF = timedelta(hours=12)       # bet late, after the framework's news/lineup checks
BAD_NEWS = ("RED", "BLOCK", "DROP", "AVOID", "OUT")

_NOISE = {"fc", "cf", "sc", "ac", "afc", "fk", "sk", "if", "bk", "cd", "ud", "sd", "rc", "sv", "vfb",
          "vfl", "tsg", "us", "as", "ss", "club", "de", "the", "calcio", "1907", "1909", "1913"}
_ALIASES = {"man": "manchester", "utd": "united", "psg": "paris saint germain", "spurs": "tottenham",
            "wolves": "wolverhampton", "nottm": "nottingham", "sheff": "sheffield", "bodoe": "bodo"}


# ---------------------------------------------------------------- fetching
def fetch_picks(dates: list[str], get: Callable = requests.get) -> tuple[list[dict], list[str]]:
    """Returns (picks files found, notes)."""
    found, notes = [], []
    for d in dates:
        try:
            r = get(PICKS_URL.format(date=d), timeout=20)
        except requests.RequestException as e:
            notes.append(f"picks {d}: fetch failed ({type(e).__name__}) — PENDING")
            continue
        if r.status_code == 404:
            notes.append(f"picks {d}: not published yet")
            continue
        if r.status_code != 200:
            notes.append(f"picks {d}: HTTP {r.status_code} — PENDING")
            continue
        found.append(r.json())
    return found, notes


def picks_dates(now: datetime) -> list[str]:
    return [(now + timedelta(days=k)).date().isoformat() for k in (0, 1)]


# ---------------------------------------------------------------- markets
def map_market(market: str) -> Optional[dict]:
    """SportyBet market key -> {'type', 'line', 'want'} or None when Matchbook has no twin.
    want is a role: 'over'/'under', 'home'/'draw'/'away', 'home_or_draw'/'home_or_away'/
    'draw_or_away', 'yes'/'no'; handicap carries the picked side's own line."""
    if market == "OVER_2_5":
        return {"type": "total", "line": 2.5, "want": "over"}
    parts = market.split("|")
    if len(parts) != 3:
        return None
    sb, spec, outcome = parts
    out = outcome.strip().lower()
    if sb == "SB:18":
        m = re.fullmatch(r"total=(\d+(?:\.\d+)?)", spec)
        if not m or not out.startswith(("over", "under")):
            return None
        line = float(m.group(1))
        return {"type": "total", "line": line, "want": out.split()[0]} if line % 1 == 0.5 else None
    if sb == "SB:10":
        role = {"home or draw": "home_or_draw", "home or away": "home_or_away",
                "draw or away": "draw_or_away"}.get(out)
        return {"type": "double_chance", "line": None, "want": role} if role else None
    if sb == "SB:16":
        m = re.fullmatch(r"(home|away) \(([+-]?\d+(?:\.\d+)?)\)", out)
        if not m:
            return None
        line = float(m.group(2))
        return ({"type": "handicap", "line": line, "want": m.group(1)}
                if abs(line) % 1 == 0.5 else None)          # half lines only: no push rules to mismatch
    if sb == "SB:1" and out in ("home", "draw", "away"):
        return {"type": "match_odds", "line": None, "want": out}
    if sb == "SB:29" and out in ("yes", "no"):
        return {"type": "btts", "line": None, "want": out}
    if sb == "SB:11" and out in ("home", "away"):
        return {"type": "dnb", "line": None, "want": out}
    return None


# ---------------------------------------------------------------- team names
def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    words = [_ALIASES.get(w, w) for w in s.split()]
    return " ".join(w for w in " ".join(words).split() if w not in _NOISE)


def alike(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    contain = len(ta & tb) / min(len(ta), len(tb))
    return max(SequenceMatcher(None, a, b).ratio(), 0.9 * contain)


def split_event(name: str) -> tuple[str, str]:
    for sep in (" vs ", " v "):
        if sep in name:
            h, a = name.split(sep, 1)
            return h.strip(), a.strip()
    return name, ""


def match_event(home: str, away: str, kickoff: datetime, events: list[dict]) -> Optional[dict]:
    best, best_score = None, 0.0
    for e in events:
        start = scanner._dt(e.get("start"))
        if start is None or abs(start - kickoff) > KICKOFF_TOLERANCE:
            continue
        eh, ea = split_event(e.get("name") or "")
        sh, sa = alike(home, eh), alike(away, ea)
        if min(sh, sa) < 0.5 or sh + sa < 1.3:
            continue
        if sh + sa > best_score:
            best, best_score = e, sh + sa
    return best


# ---------------------------------------------------------------- runners
def find_runner(e: dict, mk: dict) -> tuple[Optional[dict], Optional[dict], str]:
    """(market, runner, note) on the Matchbook event for a mapped pick."""
    eh, ea = split_event(e.get("name") or "")
    for m in e.get("markets") or []:
        if m.get("status") != "open":
            continue
        name, mtype = (m.get("name") or "").strip().lower(), m.get("market-type")
        runners = [r for r in m.get("runners") or [] if r.get("status") == "open"]
        if mk["type"] == "total" and mtype == "total" and _f(m.get("handicap")) == mk["line"]:
            hit = [r for r in runners if (r.get("name") or "").lower().startswith(mk["want"])]
        elif mk["type"] == "handicap" and mtype == "handicap":
            team = eh if mk["want"] == "home" else ea
            hit = [r for r in runners if _f(r.get("handicap")) == mk["line"]
                   and alike((r.get("name") or "").rsplit(" ", 1)[0], team) >= 0.8]
        elif mk["type"] == "double_chance" and name == "double chance":
            target = {"home_or_draw": f"{eh} or Draw", "home_or_away": f"{eh} or {ea}",
                      "draw_or_away": f"Draw or {ea}"}[mk["want"]]
            hit = [r for r in runners if (r.get("name") or "").strip().lower() == target.lower()]
        elif mk["type"] == "match_odds" and mtype == "one_x_two":
            target = {"home": eh, "away": ea, "draw": "Draw"}[mk["want"]]
            hit = [r for r in runners if (r.get("name") or "").strip().lower() == target.lower()]
        elif mk["type"] == "btts" and mtype == "both_to_score":
            hit = [r for r in runners if (r.get("name") or "").strip().lower() == mk["want"]]
        elif mk["type"] == "dnb" and name == "draw no bet":
            target = eh if mk["want"] == "home" else ea
            hit = [r for r in runners if (r.get("name") or "").strip().lower() == target.lower()]
        else:
            continue
        if len(hit) == 1:
            return m, hit[0], ""
    return None, None, "market or runner not listed on Matchbook"


def _f(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- the feed
def legs(picks_files: list[dict]) -> list[dict]:
    """Every single in the picks files, newest file wins for a fixture+market."""
    out: dict = {}
    for f in picks_files:
        for s in f.get("singles") or []:
            out[(s.get("fixture"), s.get("market"))] = {**s, "picks_date": f.get("date")}
    return list(out.values())


def candidates(picks_files: list[dict], events: list[dict], now: datetime,
               held_keys: set) -> tuple[list[dict], list[str]]:
    """Framework legs ready for the risk gate, and a line per leg that was not."""
    out, skipped = [], []
    for s in legs(picks_files):
        label = f"{s.get('pick') or s.get('market')} — {s.get('fixture')}"
        key = f"{s.get('picks_date')}|{s.get('fixture')}|{s.get('market')}"
        if key in held_keys:
            continue
        ko = scanner._dt(s.get("kickoff_utc"))
        if ko is None:
            skipped.append(f"{label}: no kick-off time — PENDING")
            continue
        if not (MIN_TO_KICKOFF <= ko - now <= MAX_TO_KICKOFF):
            continue                                          # too early or too late: quietly wait / pass
        if str(s.get("news_level") or "").upper() in BAD_NEWS:
            skipped.append(f"{label}: framework news flag {s.get('news_level')}")
            continue
        try:
            p = float(s.get("chance"))
        except (TypeError, ValueError):
            skipped.append(f"{label}: no framework probability — PENDING")
            continue
        mk = map_market(s.get("market") or "")
        if mk is None:
            skipped.append(f"{label}: market not on Matchbook ({s.get('market')})")
            continue
        e = match_event(s.get("home") or "", s.get("away") or "", ko, events)
        if e is None:
            skipped.append(f"{label}: match not found on Matchbook")
            continue
        m, r, note = find_runner(e, mk)
        if r is None:
            skipped.append(f"{label}: {note}")
            continue
        runners = [x for x in m.get("runners") or [] if x.get("status") == "open"]
        c = scanner.candidate(e, m, r, runners)
        why = scanner.tradable(c["book"])
        if why:
            skipped.append(f"{label}: {why}")
            continue
        c.update(source="framework", fw_key=key, fw_pick=s.get("pick"), fw_code=s.get("code"),
                 fw_price=s.get("price"), min_edge=C.MIN_EDGE_FRAMEWORK,
                 oracle={"true_prob": p, "confidence": 1.0,
                         "reasoning": f"framework {s.get('tier') or ''} {s.get('certainty') or ''}".strip()})
        out.append(c)
    return out, skipped
