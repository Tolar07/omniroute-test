#!/usr/bin/env python3
"""
OLP XDV — LAYER DIAGNOSTIC

Run:  py -3.12 diagnose.py

Tests the stack from the bottom up and stops being useful to lie to.
Reports the FIRST broken layer — everything above a broken layer is
untrustworthy regardless of what it reports about itself.

Designed to run against a codebase it knows nothing about: every import
and call is defensive. A module that will not import is a finding, not
a crash.
"""

import os
import re
import sys
import json
import importlib
import traceback
from pathlib import Path
from datetime import date, timedelta

REPO = Path(__file__).resolve().parent
RESULTS = []


def report(layer, name, ok, detail=""):
    RESULTS.append((layer, name, ok, detail))
    mark = "PASS" if ok else "FAIL" if ok is False else "WARN"
    print(f"  [{mark}] {name}")
    if detail:
        for line in str(detail).splitlines():
            print(f"         {line}")


def header(n, title):
    print(f"\n{'='*66}\nLAYER {n}: {title}\n{'='*66}")


# ──────────────────────────────────────────────────────────────────
# GROUND TRUTH — verified 2026-09-12 against ESPN, Sky Sports,
# premierleague.com. Update when you add a new date.
# ──────────────────────────────────────────────────────────────────
GROUND_TRUTH = {
    "2026-09-12": {
        "premier_league_count": 7,
        "must_contain": [
            ("Liverpool", "Fulham"),
            ("Sunderland", "Arsenal"),
            ("Chelsea", "Hull City"),
            ("Tottenham", "Everton"),
        ],
        "must_not_contain": [
            ("Manchester City", "Arsenal"),
            ("Manchester United", "Manchester City"),  # this is 09-13
        ],
    }
}


# ──────────────────────────────────────────────────────────────────
def layer0_environment():
    header(0, "ENVIRONMENT")

    env = REPO / ".env"
    if not env.exists():
        report(0, ".env present", False, f"not found at {env}")
        return
    report(0, ".env present", True)

    keys = {}
    for line in env.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        keys[k.strip()] = v.strip()

    if not keys:
        report(0, "keys parsed", False, "file exists but contains no key=value pairs")
        return

    for k, v in sorted(keys.items()):
        placeholder = v in ("", "None", "null", "changeme", "your_key_here", "xxx")
        report(0, f"key {k}", not placeholder,
               "EMPTY OR PLACEHOLDER VALUE" if placeholder else f"set ({len(v)} chars)")


# ──────────────────────────────────────────────────────────────────
STUB_PAT = re.compile(
    r"\b(stub|STUB|placeholder|hardcoded|hard-coded|dummy|mock(?!ito)|"
    r"NotImplementedError|FIXME|TODO|for now|temporary)\b"
)


def layer1_stub_scan():
    header(1, "STUB SCAN")

    hits = {}
    for py in REPO.rglob("*.py"):
        if any(p in py.parts for p in (".venv", "venv", "site-packages",
                                       "__pycache__", "tests", "test")):
            continue
        try:
            for i, line in enumerate(py.read_text(errors="ignore").splitlines(), 1):
                if STUB_PAT.search(line):
                    hits.setdefault(py.relative_to(REPO), []).append((i, line.strip()[:90]))
        except Exception:
            continue

    if not hits:
        report(1, "no stub markers found", True)
        return

    critical = [f for f in hits if "fixture" in str(f).lower()
                or "odds" in str(f).lower()
                or "booking" in str(f).lower()]

    for f in sorted(hits, key=lambda x: (x not in critical, str(x))):
        tag = "  <-- DATA PATH" if f in critical else ""
        report(1, f"{f}{tag}", f not in critical,
               "\n".join(f"L{n}: {t}" for n, t in hits[f][:4]))


# ──────────────────────────────────────────────────────────────────
CANDIDATE_SOURCES = [
    ("data.espn_source", ["fetch_upcoming", "fetch", "get_fixtures"]),
    ("data.apifootball_client", ["fetch_upcoming", "fetch_fixtures", "get_fixtures"]),
    ("data.multi_source_concentrator", ["fetch", "fetch_all", "get_fixtures"]),
    ("fixtures_agent", ["fetch_fixtures", "get_fixtures", "run", "fetch"]),
]


def call_any(mod, names, arg):
    """Try each candidate function name until one accepts the arg."""
    for n in names:
        fn = getattr(mod, n, None)
        if not callable(fn):
            continue
        try:
            return n, fn(arg)
        except TypeError:
            try:
                return n, fn(date.fromisoformat(arg))
            except Exception:
                continue
        except Exception as e:
            return n, e
    return None, None


def layer2_sources():
    header(2, "DATA SOURCES — can they be called at all?")

    today = date.today().isoformat()
    live = {}

    for modname, fns in CANDIDATE_SOURCES:
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            report(2, f"import {modname}", False, f"{type(e).__name__}: {e}")
            continue
        report(2, f"import {modname}", True)

        fname, result = call_any(mod, fns, today)
        if fname is None:
            report(2, f"{modname} callable", False,
                   f"none of {fns} exist or accept a date")
            continue
        if isinstance(result, Exception):
            report(2, f"{modname}.{fname}()", False,
                   f"{type(result).__name__}: {result}")
            continue

        n = len(result) if hasattr(result, "__len__") else "?"
        report(2, f"{modname}.{fname}() -> {n} rows", bool(n),
               "returned zero rows" if not n else "")
        if n:
            live[modname] = (fname, result)

    return live


# ──────────────────────────────────────────────────────────────────
def fingerprint(rows):
    """Order-independent signature of a fixture set."""
    out = []
    for r in rows or []:
        if isinstance(r, dict):
            out.append("|".join(str(r.get(k, "")) for k in
                                ("home", "away", "home_team", "away_team")))
        else:
            out.append(str(r))
    return hash(tuple(sorted(out)))


def layer3_variance(live):
    """THE KEY TEST.

    A real source returns different fixtures on different dates.
    A stub returns the same rows forever. This single check catches
    both a hardcoded fixture list and a date parameter that is being
    silently ignored.
    """
    header(3, "VARIANCE — does the data change when the date changes?")

    if not live:
        report(3, "variance test", None, "skipped — no source returned rows")
        return

    d0 = date.today()
    dates = [(d0 + timedelta(days=n)).isoformat() for n in (0, 1, 2, 30)]

    for modname, (fname, _) in live.items():
        mod = importlib.import_module(modname)
        prints = {}
        for d in dates:
            _, res = call_any(mod, [fname], d)
            if isinstance(res, Exception):
                prints[d] = f"ERROR {type(res).__name__}"
            else:
                prints[d] = fingerprint(res)

        uniq = len(set(prints.values()))
        if uniq == 1:
            report(3, f"{modname} varies by date", False,
                   "IDENTICAL OUTPUT FOR ALL FOUR DATES — this is a stub, "
                   "or the date argument is being ignored.\n"
                   + "\n".join(f"{d}: {v}" for d, v in prints.items()))
        else:
            report(3, f"{modname} varies by date", True,
                   f"{uniq} distinct results across 4 dates")


# ──────────────────────────────────────────────────────────────────
def rows_to_pairs(rows):
    pairs = []
    for r in rows or []:
        if isinstance(r, dict):
            h = r.get("home") or r.get("home_team") or ""
            a = r.get("away") or r.get("away_team") or ""
            if h or a:
                pairs.append((str(h), str(a)))
    return pairs


def layer4_ground_truth(live):
    header(4, "GROUND TRUTH — does the data match reality?")

    today = date.today().isoformat()
    truth = GROUND_TRUTH.get(today)
    if not truth:
        report(4, "ground truth available", None,
               f"no verified fixture set for {today}. "
               "Add one to GROUND_TRUTH before trusting any board.")
        return
    if not live:
        report(4, "ground truth check", None, "skipped — no source returned rows")
        return

    for modname, (_, rows) in live.items():
        pairs = rows_to_pairs(rows)
        flat = " ".join(f"{h} v {a}" for h, a in pairs)

        missing = [f"{h} v {a}" for h, a in truth["must_contain"]
                   if h not in flat or a not in flat]
        report(4, f"{modname}: contains known real fixtures",
               not missing,
               "MISSING: " + ", ".join(missing) if missing else "")

        ghosts = [f"{h} v {a}" for h, a in truth["must_not_contain"]
                  if h in flat and a in flat]
        report(4, f"{modname}: free of known-false fixtures",
               not ghosts,
               "FABRICATED FIXTURE PRESENT: " + ", ".join(ghosts) if ghosts else "")


# ──────────────────────────────────────────────────────────────────
def layer5_traceability():
    header(5, "TRACEABILITY — HR59")

    hook = REPO / ".claude" / "hooks"
    report(5, "PreToolUse hook directory exists", hook.exists(),
           "" if hook.exists() else
           "No enforcement hook. HR59 is instruction only — a model can "
           "still emit an untraceable board.")

    found = False
    for py in REPO.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        try:
            if "run_id" in py.read_text(errors="ignore"):
                found = True
                break
        except Exception:
            continue
    report(5, "run_id referenced in code", found,
           "" if found else "No run_id anywhere — output cannot be traced to a run.")


# ──────────────────────────────────────────────────────────────────
def summary():
    print(f"\n{'='*66}\nSUMMARY\n{'='*66}")
    fails = [r for r in RESULTS if r[2] is False]
    if not fails:
        print("  No failures. If the board is still wrong, the fault is in\n"
              "  logic above the data layer, not in the data.")
        return 0

    first = min(f[0] for f in fails)
    print(f"  {len(fails)} failure(s). Lowest broken layer: {first}\n")
    print(f"  Fix layer {first} first. Every layer above it is reporting\n"
          f"  on data it cannot validate, so nothing above layer {first}\n"
          f"  means anything yet.\n")
    for layer, name, _, detail in fails:
        if layer == first:
            print(f"    L{layer}  {name}")
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    print(f"OLP XDV DIAGNOSTIC — {date.today().isoformat()}")
    print(f"repo: {REPO}")

    try:
        layer0_environment()
        layer1_stub_scan()
        live = layer2_sources()
        layer3_variance(live)
        layer4_ground_truth(live)
        layer5_traceability()
    except Exception:
        print("\nDIAGNOSTIC ITSELF CRASHED:")
        traceback.print_exc()
        sys.exit(2)

    sys.exit(summary())