#!/usr/bin/env python3
"""
diagnose_fixture_sources.py — tests every fixture source LIVE and tells
you exactly what's wrong with each. Run this instead of guessing at
"API connectivity issues."

Confirmed bug it checks for first: API-Football's season parameter is a
4-DIGIT START YEAR (2026 for the 2026-27 season), per their own docs.
The framework's internal season string is 2627. Passing 2627 returns an
empty result set with NO error — indistinguishable from "no fixtures
today" unless you check. That alone explains "0 fixtures available."

Usage:
    python diagnose_fixture_sources.py
    python diagnose_fixture_sources.py --date 2026-09-05
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime

import requests

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
FOOTBALL_DATA_KEY = os.environ.get("FOOTBALL_DATA_ORG_KEY", "")


def hr(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def safe_print(text: str) -> None:
    """Print with Unicode fallback for Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace common emoji with ASCII
        text = (text
                .replace('❌', '[FAIL]')
                .replace('✅', '[OK]')
                .replace('⚠', '[WARN]')
                .replace('❓', '[?]'))
        print(text)


def test_api_football(target: str) -> None:
    hr("1. API-FOOTBALL (primary, paid)")
    if not API_FOOTBALL_KEY:
        safe_print("[FAIL] API_FOOTBALL_KEY not set in environment.")
        safe_print("   This alone produces '0 fixtures' with no other symptom.")
        return

    safe_print(f"[OK] Key present: {API_FOOTBALL_KEY[:6]}...{API_FOOTBALL_KEY[-4:]}")

    # Check account status first - a quota-exhausted key looks like an outage.
    try:
        r = requests.get("https://v3.football.api-sports.io/status",
                         headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=15)
        data = r.json()
        resp = data.get("response", {})
        sub = resp.get("subscription", {})
        req = resp.get("requests", {})
        safe_print(f"  Account: plan={sub.get('plan')} active={sub.get('active')} ends={sub.get('end')}")
        safe_print(f"  Quota:   {req.get('current')}/{req.get('limit_day')} used today")
        if data.get("errors"):
            safe_print(f"  [WARN] errors: {data['errors']}")
    except Exception as exc:
        safe_print(f"[FAIL] /status call failed: {exc}")
        return

    # THE KEY TEST: date-only query (no season needed).
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures",
                         headers={"x-apisports-key": API_FOOTBALL_KEY},
                         params={"date": target}, timeout=20)
        data = r.json()
        n = len(data.get("response", []))
        safe_print(f"\n  [OK] date-only query (?date={target}): {n} fixture(s)")
        if data.get("errors"):
            safe_print(f"     errors: {data['errors']}")
        if n:
            for fx in data["response"][:5]:
                lg = fx["league"]["name"]
                t = fx["teams"]
                safe_print(f"       {lg}: {t['home']['name']} v {t['away']['name']} @ {fx['fixture']['date']}")
    except Exception as exc:
        safe_print(f"[FAIL] date query failed: {exc}")

    # Demonstrate the wrong-season bug explicitly.
    safe_print("\n  --- season parameter comparison (Bundesliga, league=78) ---")
    for season_label, season_value in (("WRONG (framework format)", "2627"),
                                        ("CORRECT (4-digit start year)", "2026")):
        try:
            r = requests.get("https://v3.football.api-sports.io/fixtures",
                             headers={"x-apisports-key": API_FOOTBALL_KEY},
                             params={"league": 78, "season": season_value, "date": target},
                             timeout=20)
            data = r.json()
            n = len(data.get("response", []))
            errs = data.get("errors")
            safe_print(f"  season={season_value:<6} [{season_label}]: {n} fixture(s), errors={errs or 'none'}")
        except Exception as exc:
            safe_print(f"  season={season_value}: request failed - {exc}")


def test_espn(target: str) -> None:
    hr("2. ESPN (free, no key - good fallback)")
    # Undocumented/unofficial endpoint. Reliable in practice but can change
    # without notice — treat as a fallback, never the sole source.
    ymd = target.replace("-", "")
    for slug, name in (("ger.1", "Bundesliga"), ("eng.1", "Premier League"),
                        ("esp.1", "La Liga"), ("ita.1", "Serie A")):
        try:
            r = requests.get(
                f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard",
                params={"dates": ymd}, timeout=15)
            events = r.json().get("events", [])
            safe_print(f"  {name:<16} ({slug}): {len(events)} fixture(s)")
            for e in events[:3]:
                safe_print(f"       {e.get('name')} @ {e.get('date')}")
        except Exception as exc:
            safe_print(f"  {name}: failed — {exc}")


def test_thesportsdb(target: str) -> None:
    hr("3. THESPORTSDB (free)")
    # NOTE: the 'l' parameter takes a league NAME, not a numeric id.
    # Passing an id silently returns nothing — a likely cause of the
    # "TheSportsDB date handling" issue reported.
    tests = [
        ("s=Soccer (all soccer that day)", {"d": target, "s": "Soccer"}),
        ("l=German Bundesliga (name)", {"d": target, "l": "German Bundesliga"}),
        ("l=78 (numeric id — expected to FAIL)", {"d": target, "l": "78"}),
    ]
    for label, params in tests:
        try:
            r = requests.get("https://www.thesportsdb.com/api/v1/json/3/eventsday.php",
                             params=params, timeout=15)
            events = r.json().get("events")
            count = len(events) if events else 0
            safe_print(f"  {label}: {count} event(s)")
        except Exception as exc:
            safe_print(f"  {label}: failed — {exc}")


def test_football_data_org(target: str) -> None:
    hr("4. FOOTBALL-DATA.ORG (free tier - recommended addition)")
    if not FOOTBALL_DATA_KEY:
        print("  FOOTBALL_DATA_ORG_KEY not set.")
        print("  Free tier covers the major European leagues, ~10 calls/min.")
        print("  Register at football-data.org/client/register — worth adding")
        print("  as a third independent source so no single API can zero the board.")
        return
    try:
        r = requests.get("https://api.football-data.org/v4/matches",
                         headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
                         params={"dateFrom": target, "dateTo": target}, timeout=20)
        matches = r.json().get("matches", [])
        safe_print(f"  [OK] {len(matches)} match(es) on {target}")
        for m in matches[:5]:
            print(f"     {m['competition']['name']}: {m['homeTeam']['name']} v "
                  f"{m['awayTeam']['name']} @ {m['utcDate']}")
    except Exception as exc:
        print(f"  ❌ failed — {exc}")


def test_openligadb(target: str) -> None:
    hr("5. OPENLIGADB (free, no key - German football only)")
    try:
        r = requests.get("https://api.openligadb.de/getmatchdata/bl1/2026", timeout=20)
        matches = r.json()
        on_date = [m for m in matches if m.get("matchDateTime", "").startswith(target)]
        safe_print(f"  Bundesliga 2026-27: {len(matches)} total fixtures, {len(on_date)} on {target}")
        for m in on_date[:5]:
            safe_print(f"     {m['team1']['teamName']} v {m['team2']['teamName']} @ {m['matchDateTime']}")
    except Exception as exc:
        safe_print(f"  [FAIL] failed — {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    safe_print(f"Diagnosing fixture sources for {args.date}")
    safe_print(f"(run at {datetime.now().isoformat(timespec='seconds')})")

    test_api_football(args.date)
    test_espn(args.date)
    test_thesportsdb(args.date)
    test_football_data_org(args.date)
    test_openligadb(args.date)

    hr("READ THE RESULTS THIS WAY")
    safe_print("""
- If API-Football's date-only query returns fixtures but the
  season=2627 query returns 0: THAT is your bug. Fix the season format
  (or drop the season param entirely and query by date).

- If several sources agree there are 0 fixtures on this date, then
  there genuinely are none, and an empty board is the CORRECT output —
  not a failure to fix.

- If API-Football's /status shows the quota exhausted or the
  subscription inactive, that's a billing/account issue, not code.

- Cross-check: run this with --date set to a date you KNOW has matches
  (e.g. 2026-09-05 for Bundesliga Matchday 2). If sources return
  fixtures then but not today, today is genuinely empty.
""")


if __name__ == "__main__":
    main()