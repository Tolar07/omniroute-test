"""
Paper study — rules bet £1 on paper at Matchbook's live prices, on every match
the bot scans. NOTHING here places an order (Architect 2026-10-15: "do 50
paper ... use those matches ... get your theory right ... then apply what
you've learned").

The question: is the 1.50-2.00 band worth real money on Matchbook? The
framework's paper book (backtest/PAPER_BOOK.md) answers similar questions at
SportyBet's prices; these rules ask them at Matchbook's.

  FW-MED  DECISION RULE. A framework leg (single or rated pool) at 50-80% model
          chance, Matchbook 1.50-2.00, MEDIUM certainty on Matchbook (model 3-7
          pts over break-even): the live rule with the 80% bar lowered.
  FW-ALL  every framework leg priced 1.50-2.00 on Matchbook: is the model's
          chance right in this band at all (stated vs landed)?
  F2      1X2 favourite at 1.50-2.00            (framework paper book F2)
  F10     home win at 1.60-2.50                  (framework paper book F10)
  F9      home or away (double chance) 1.20-1.40 (framework paper book F9: the
          kind of bet the live rule takes)

A rule takes the best back price the first time the runner is seen inside the
live betting window (10 min-12 h before kick-off) with a tradable book. Each
cycle refreshes its closing price until kick-off: CLV = taken / close - 1.
Results come from the framework's graded universe archive (Flashscore,
regular time, data/universe/*.jsonl.gz on GitHub), matched by kick-off ±20
min and both team names: the same grader the framework uses. No match after
4 days -> UNGRADED, never guessed (HR35). Return per £1 is net of commission.

When FW-MED reaches DECISION_N graded bets the heartbeat posts PAPER RESULT
once. Pre-registered bar to propose real money: return >= 0 AND mean CLV > 0.
"""
from __future__ import annotations

import gzip
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import requests

from matchbook_live import config as C
from matchbook_live import framework_feed as F
from matchbook_live import scanner

PAPER_FILE = "paper.jsonl"
STATE_FILE = "paper_state.json"
ARCHIVE_API = "https://api.github.com/repos/Tolar07/framework/contents/data/universe"
ARCHIVE_RAW = "https://raw.githubusercontent.com/Tolar07/framework/main/data/universe/{name}"
INDEX_EVERY = timedelta(hours=1)        # GitHub's unauthenticated API allows 60 calls an hour
GRADE_AFTER = timedelta(hours=2, minutes=30)
UNGRADED_AFTER = timedelta(days=4)
KEEP_RESULTS = timedelta(days=7)
DECISION_RULE, DECISION_N = "FW-MED", 50
RULES = ("FW-MED", "FW-ALL", "F2", "F10", "F9")
BAND = (1.50, 2.00)


# ---------------------------------------------------------------- grading
def outcome(mk: dict, h: int, a: int) -> str:
    """WIN / LOSS / VOID for a mapped market ({'type','line','want'}) at full time h-a."""
    t, want, line = mk["type"], mk["want"], mk.get("line")
    if t == "match_odds":
        won = {"home": h > a, "away": a > h, "draw": h == a}[want]
    elif t == "double_chance":
        won = {"home_or_draw": h >= a, "home_or_away": h != a, "draw_or_away": a >= h}[want]
    elif t == "total":
        won = (h + a > line) if want == "over" else (h + a < line)
    elif t == "handicap":                                  # half lines only: never a push
        won = (h + line > a) if want == "home" else (a + line > h)
    elif t == "btts":
        won = (h > 0 and a > 0) == (want == "yes")
    elif t == "dnb":
        if h == a:
            return "VOID"
        won = (h > a) if want == "home" else (a > h)
    else:
        raise ValueError(t)
    return "WIN" if won else "LOSS"


def unit_return(rec: dict) -> Optional[float]:
    c = C.COMMISSION
    return {"WIN": rec["odds"] - 1 - c, "LOSS": -1 - c, "VOID": 0.0}.get(rec.get("status"))


# ---------------------------------------------------------------- rules
def _book(r: dict) -> Optional[dict]:
    b = scanner.runner_book(r)
    return b if scanner.tradable(b) is None else None


def _record(rule: str, e: dict, m: dict, r: dict, b: dict, mk: dict, now: datetime,
            p: Optional[float] = None) -> dict:
    eh, ea = F.split_event(e.get("name") or "")
    return {"key": f"{rule}|{m['id']}|{r['id']}", "rule": rule, "event_name": e.get("name"),
            "home": eh, "away": ea, "ko": e.get("start"), "market_name": m.get("name"),
            "runner_id": r["id"], "runner_name": r.get("name"), "mk": mk, "p": p,
            "odds": b["best_back"], "taken_at": now.isoformat(timespec="seconds"),
            "close": b["best_back"], "status": "OPEN"}


def _in_window(e: dict, now: datetime) -> bool:
    ko = scanner._dt(e.get("start"))
    return (ko is not None and e.get("status") == "open"
            and F.MIN_TO_KICKOFF <= ko - now <= F.MAX_TO_KICKOFF)


def market_rules(e: dict, now: datetime) -> list[dict]:
    """F2, F10, F9 on one Matchbook event."""
    if not _in_window(e, now):
        return []
    eh, ea = F.split_event(e.get("name") or "")
    out = []
    for m in e.get("markets") or []:
        if m.get("status") != "open":
            continue
        runners = {(r.get("name") or "").strip().lower(): r
                   for r in m.get("runners") or [] if r.get("status") == "open"}
        if m.get("market-type") == "one_x_two":
            home, away = runners.get(eh.lower()), runners.get(ea.lower())
            hb, ab = (_book(home) if home else None), (_book(away) if away else None)
            if hb and ab:
                fav, fb, want = (home, hb, "home") if hb["best_back"] <= ab["best_back"] else (away, ab, "away")
                if BAND[0] <= fb["best_back"] <= BAND[1]:
                    out.append(_record("F2", e, m, fav, fb, {"type": "match_odds", "want": want}, now))
            if hb and 1.60 <= hb["best_back"] <= 2.50:
                out.append(_record("F10", e, m, home, hb, {"type": "match_odds", "want": "home"}, now))
        elif (m.get("name") or "").strip().lower() == "double chance":
            r = runners.get(f"{eh} or {ea}".lower())
            b = _book(r) if r else None
            if b and 1.20 <= b["best_back"] <= 1.40:
                out.append(_record("F9", e, m, r, b, {"type": "double_chance", "want": "home_or_away"}, now))
    return out


def framework_rules(picks_files: list[dict], events: list[dict], now: datetime) -> list[dict]:
    """FW-ALL and FW-MED on every framework leg Matchbook lists."""
    out = []
    for s in F.legs(picks_files):
        mk = F.map_market(s.get("market") or "")
        try:
            p = float(s.get("chance"))
        except (TypeError, ValueError):
            continue
        if mk is None:
            continue
        ko = scanner._dt(s.get("kickoff_utc"))
        e = F.match_event(s.get("home") or "", s.get("away") or "", ko, events, s.get("kickoff"))
        if e is None or not _in_window(e, now):
            continue
        m, r, _ = F.find_runner(e, mk)
        b = _book(r) if r else None
        if not b or not (BAND[0] <= b["best_back"] <= BAND[1]):
            continue
        out.append(_record("FW-ALL", e, m, r, b, mk, now, p))
        gap = p - (1 + C.COMMISSION) / b["best_back"]
        if 0.50 <= p < 0.80 and gap > 0 and F.certainty(gap) == "MEDIUM":
            out.append(_record("FW-MED", e, m, r, b, mk, now, p))
    return out


# ---------------------------------------------------------------- results archive
def _get_json(url: str, get: Callable) -> object:
    r = get(url, timeout=30, headers={"Accept": "application/vnd.github+json"})
    r.raise_for_status()
    return r.json()


def refresh_results(st: dict, now: datetime, get: Callable = requests.get) -> str:
    """Pull graded football games we have not read from the framework's archive."""
    last = st.get("index_at")
    if last and now - datetime.fromisoformat(last) < INDEX_EVERY:
        return ""
    st["index_at"] = now.isoformat(timespec="seconds")
    names = [x["name"] for x in _get_json(ARCHIVE_API, get) if x.get("name", "").endswith(".jsonl.gz")]
    read = set(st.get("read", []))
    new = 0
    for name in sorted(n for n in names if n not in read):
        r = get(ARCHIVE_RAW.format(name=name), timeout=60)
        r.raise_for_status()
        for line in gzip.decompress(r.content).decode("utf-8").splitlines():
            g = json.loads(line) if line.strip() else {}
            res = g.get("result") or {}
            if g.get("sport") == "football" and "h" in res and "a" in res and g.get("ko"):
                st.setdefault("results", []).append([g["ko"], g.get("home"), g.get("away"), res["h"], res["a"]])
                new += 1
        read.add(name)
    st["read"] = sorted(read)
    cutoff = now - KEEP_RESULTS
    st["results"] = [x for x in st.get("results", []) if (scanner._dt(x[0]) or now) >= cutoff]
    return f"{new} new graded game(s)" if new else ""


def find_result(rec: dict, results: list[list]) -> Optional[tuple[int, int]]:
    ko = scanner._dt(rec.get("ko"))
    best, score = None, 0.0
    for k, home, away, h, a in results:
        t = scanner._dt(k)
        if ko is None or t is None or abs(t - ko) > F.KICKOFF_TOLERANCE:
            continue
        sh, sa = F.alike(rec["home"], home or ""), F.alike(rec["away"], away or "")
        if min(sh, sa) >= 0.5 and sh + sa >= 1.3 and sh + sa > score:
            best, score = (int(h), int(a)), sh + sa
    return best


# ---------------------------------------------------------------- one cycle
def _load(state_dir: Path) -> tuple[list[dict], dict]:
    pf, sf = state_dir / PAPER_FILE, state_dir / STATE_FILE
    recs = [json.loads(x) for x in pf.read_text(encoding="utf-8").splitlines() if x.strip()] if pf.exists() else []
    st = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
    return recs, st


def _save(state_dir: Path, recs: list[dict], st: dict) -> None:
    (state_dir / PAPER_FILE).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
                                        encoding="utf-8")
    (state_dir / STATE_FILE).write_text(json.dumps(st), encoding="utf-8")


def cycle(state_dir: Path, picks_files: list[dict], events: list[dict], now: datetime,
          get: Callable = requests.get) -> tuple[list[str], list[str]]:
    """Take new paper bets, refresh closing prices, grade. Returns (heartbeat lines, events)."""
    recs, st = _load(state_dir)
    have = {r["key"] for r in recs}
    taken = 0
    for r in [*framework_rules(picks_files, events, now), *(x for e in events for x in market_rules(e, now))]:
        if r["key"] not in have:
            recs.append(r)
            have.add(r["key"])
            taken += 1
    # closing price: the last best back seen before kick-off
    live = {}
    for e in events:
        start = scanner._dt(e.get("start"))
        if start is not None and start > now:
            for m in e.get("markets") or []:
                for r in m.get("runners") or []:
                    live[str(r.get("id"))] = r
    for rec in recs:
        if rec["status"] == "OPEN" and str(rec["runner_id"]) in live:
            b = scanner.runner_book(live[str(rec["runner_id"])])
            if b:
                rec["close"] = b["best_back"]
    note = ""
    try:
        note = refresh_results(st, now, get)
    except Exception as e:                                  # archive down: grade next run
        note = f"results archive PENDING ({type(e).__name__})"
    graded = 0
    for rec in recs:
        ko = scanner._dt(rec.get("ko"))
        if rec["status"] != "OPEN" or ko is None or now - ko < GRADE_AFTER:
            continue
        ft = find_result(rec, st.get("results", []))
        if ft:
            rec["status"], rec["ft"] = outcome(rec["mk"], *ft), f"{ft[0]}-{ft[1]}"
            graded += 1
        elif now - ko > UNGRADED_AFTER:
            rec["status"] = "UNGRADED"
    events_out = []
    s = summary(recs)
    d = s.get(DECISION_RULE, {})
    if d.get("graded", 0) >= DECISION_N and not st.get("decision_posted"):
        st["decision_posted"] = now.isoformat(timespec="seconds")
        ok = d["ret"] >= 0 and (d["clv"] or 0) > 0
        events_out.append(f"PAPER RESULT {DECISION_RULE}: {line(DECISION_RULE, d)} -> "
                          + ("passes the bar (return >= 0, CLV > 0): propose real money"
                             if ok else "fails the bar: the 1.50-2.00 band stays paper"))
    _save(state_dir, recs, st)
    head = (f"PAPER STUDY (Matchbook prices, £1 paper, no money) · {taken} new · {graded} graded"
            + (f" · {note}" if note else ""))
    return [head, *(f"  {line(k, s[k])}" for k in RULES if k in s)], events_out


# ---------------------------------------------------------------- the record
def summary(recs: list[dict]) -> dict:
    out: dict = {}
    for k in RULES:
        rows = [r for r in recs if r["rule"] == k]
        if not rows:
            continue
        g = [r for r in rows if r["status"] in ("WIN", "LOSS", "VOID")]
        rets = [unit_return(r) for r in g]
        n = len(rets)
        mean = sum(rets) / n if n else 0.0
        se = math.sqrt(sum((x - mean) ** 2 for x in rets) / (n - 1) / n) if n > 1 else None
        clvs = [r["odds"] / r["close"] - 1 for r in rows if r.get("close")]
        ps = [r["p"] for r in g if r.get("p") is not None and r["status"] != "VOID"]
        out[k] = {"bets": len(rows), "open": sum(r["status"] == "OPEN" for r in rows), "graded": n,
                  "won": sum(r["status"] == "WIN" for r in g), "ret": mean, "se": se,
                  "clv": sum(clvs) / len(clvs) if clvs else None,
                  "stated": sum(ps) / len(ps) if ps else None,
                  "avg_odds": sum(r["odds"] for r in rows) / len(rows)}
    return out


def line(k: str, d: dict) -> str:
    landed = d["won"] / d["graded"] if d["graded"] else None
    return (f"{k}: {d['bets']} bets ({d['open']} open) · avg {d['avg_odds']:.2f} · graded {d['graded']}"
            + (f" won {landed:.0%}" if landed is not None else "")
            + (f" vs stated {d['stated']:.0%}" if d.get("stated") is not None else "")
            + (f" · return {d['ret']:+.1%}" + (f" ± {d['se']:.1%}" if d['se'] is not None else "")
               if d["graded"] else "")
            + (f" · CLV {d['clv']:+.1%}" if d["clv"] is not None else ""))
