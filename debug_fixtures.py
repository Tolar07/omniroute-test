#!/usr/bin/env python3
"""
Debug script to inspect fixtures fetched by the pipeline logic
"""

import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "olp_xdv_agent" / "olp_xdv"))

from data.multi_source_concrete import get_fixtures
from engine.leagues import WHITELISTED_LEAGUES
from data.thesportsdb_fixtures import map_team
from booking.bridge import load_sportybet_fixtures, sportybet_fixtures_to_pairs
from datetime import date, datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_fixtures")

def fetch_fixtures_for_date(target_date_str):
    """Fetch fixtures using the same logic as agent_1_ingest but without date gate"""
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = date.today()
    print(f"Fetching fixtures for target date: {target_date.isoformat()}")

    # Calculate days_ahead from today to target_date
    today = date.today()
    days_ahead = (target_date - today).days
    if days_ahead < 0:
        days_ahead = 0
    print(f"  days_ahead parameter: {days_ahead}")

    fixtures = []
    data_flags = []

    for league in WHITELISTED_LEAGUES:
        upcoming_fixtures: list[tuple[str, str]] = []
        fixture_dates: dict[tuple[str, str], str] = {}
        primary_had_fixtures = False
        src = "?"

        try:
            fx = get_fixtures(league, "2627", days_ahead=days_ahead, api_football_season=None)
            raw_fixtures = fx.get("fixtures") or []
            upcoming_fixtures = [(map_team(league, h), map_team(league, a))
                                 for h, a in raw_fixtures]
            fixture_dates.update(fx.get("dates") or {})
            src = fx.get("source", "?")
            if fx.get("skipped"):
                data_flags.append(f"{league}: {fx['skipped']} fixture rows skipped/malformed")
            primary_had_fixtures = bool(upcoming_fixtures)

            if src != "thesportsdb":
                data_flags.append(f"{league}: fixtures via {src}")
        except Exception as e:
            data_flags.append(f"{league}: multi-source fixtures: {e}")
            logger.warning(f"{league}: multi-source fixtures: {e}")

        try:
            sb_pairs = sportybet_fixtures_to_pairs(
                league, days_ahead=45, max_age_hours=48)
            if sb_pairs:
                sb_pairs = [(map_team(league, h), map_team(league, a))
                            for h, a in sb_pairs]
                existing = set(upcoming_fixtures)
                merged = 0
                for h, a in sb_pairs:
                    if (h, a) not in existing:
                        upcoming_fixtures.append((h, a))
                        existing.add((h, a))
                        merged += 1
                for f in load_sportybet_fixtures(
                        league, days_ahead=45, max_age_hours=48):
                    if f.kickoff_utc:
                        mh = map_team(league, f.home_team)
                        ma = map_team(league, f.away_team)
                        fixture_dates[(mh, ma)] = f.kickoff_utc[:10]
                if merged:
                    if primary_had_fixtures:
                        data_flags.append(
                            f"{league}: +{merged} fixture(s) merged from SportyBet cache "
                            f"(primary: {src})")
                    else:
                        data_flags.append(
                            f"{league}: fixtures via SportyBet cache "
                            f"({merged} — primary sources failed)")
        except Exception as e:
            data_flags.append(f"{league}: SportyBet cache merge failed ({e})")
            logger.warning(f"{league}: SportyBet cache merge failed: {e}")

        for h, a in upcoming_fixtures:
            fixtures.append({
                "match_id": f"FX-{league[:2].upper()}-{h[:3]}{a[:3]}",
                "sport": "football", "league": league,
                "home_team": h, "away_team": a,
                "kickoff_utc": fixture_dates.get((h, a)),
                "source_endpoints": [src] if src != "?" else [],
            })

        if not upcoming_fixtures:
            data_flags.append(f"{league}: no upcoming fixtures — NO DATA — PENDING")

    return fixtures, data_flags

def main():
    # Fetch fixtures (this will use whatever date the underlying APIs consider "today")
    fixtures, data_flags = fetch_fixtures_for_date(None)

    print(f"\nFetched {len(fixtures)} raw fixtures:")
    print("=" * 80)

    # Show first few fixtures
    for i, fx in enumerate(fixtures[:10]):
        print(f"{i+1:2d}. {fx['match_id']}: {fx['home_team']} v {fx['away_team']} ({fx['league']})")
        print(f"    Kickoff: {fx['kickoff_utc']}")
        print(f"    Sources: {fx['source_endpoints']}")
        print()

    if len(fixtures) > 10:
        print(f"    ... and {len(fixtures) - 10} more fixtures")

    print("\nData flags from fetching:")
    print("=" * 80)
    for flag in data_flags[:10]:
        print(f"  {flag}")
    if len(data_flags) > 10:
        print(f"  ... and {len(data_flags) - 10} more flags")

    # Now apply the date gate manually for target date 2026-09-03
    from datetime import date
    from dataclasses import dataclass
    from typing import List, Tuple
    from collections import Counter

    @dataclass
    class DatedFixture:
        fixture_id: str
        home: str
        away: str
        league: str
        kickoff_utc: datetime

    def validate_fixture_dates(
        fixtures: List[DatedFixture],
        target_date: date,
    ) -> Tuple[List[DatedFixture], List[str]]:
        kept, rejected = [], []

        for f in fixtures:
            fixture_date = f.kickoff_utc.date()
            if fixture_date != target_date:
                delta_days = (fixture_date - target_date).days
                reason = (
                    f"REJECTED {f.home} v {f.away} ({f.league}) — kickoff is "
                    f"{fixture_date.isoformat()} ({delta_days:+d} days from target "
                    f"{target_date.isoformat()}). This is a different matchday, not today's."
                )
                # Using print instead of logger for visibility
                print(f"  {reason}")
                rejected.append(reason)
                continue
            kept.append(f)

        if fixtures and not kept:
            reason = (
                f"ALL {len(fixtures)} fixture(s) rejected as wrong-date for {target_date.isoformat()}. "
                f"This usually means the fetch queried a forward window (next matchday / next N days) "
                f"instead of the target date — check the date parameter passed to the fixtures API, "
                f"not the API itself. An empty board is the correct output here; shipping "
                f"another matchday's fixtures as today's is not."
            )
            print(f"  {reason}")

        return kept, rejected

    def check_kickoff_time_diversity(fixtures: List[DatedFixture]) -> str | None:
        if len(fixtures) < 3:
            return None

        times = Counter(f.kickoff_utc.strftime("%H:%M") for f in fixtures)
        most_common_time, count = times.most_common(1)[0]

        if count == len(fixtures):
            return (
                f"SUSPICIOUS: all {len(fixtures)} fixtures show the identical kickoff time "
                f"{most_common_time}. Real matchdays normally stagger kickoffs. This is the "
                f"signature of one real time being copied across every row (as happened on "
                f"the 2 Sep board). Verify against the source feed before trusting these times."
            )
        return None

    def run_full_date_check(
        fixtures: List[DatedFixture],
        target_date: date,
    ) -> Tuple[List[DatedFixture], List[str]]:
        kept, rejected = validate_fixture_dates(fixtures, target_date)
        flag = check_kickoff_time_diversity(kept)
        if flag:
            print(f"  {flag}")
            rejected.append(flag)
        return kept, rejected

    # Convert pipeline fixtures to DatedFixture objects
    print(f"\nConverting to DatedFixture objects for date gate validation...")
    dated_fixtures = []
    for fx in fixtures:
        if fx.get("kickoff_utc"):
            try:
                kickoff_str = fx["kickoff_utc"]
                # Clean up weird formats like "19:30\xa0\xa0\nID"
                kickoff_str = kickoff_str.strip()
                if "\n" in kickoff_str:
                    kickoff_str = kickoff_str.split("\n")[0]
                # Try to parse as date only first
                if "T" not in kickoff_str and "-" in kickoff_str and len(kickoff_str) == 10:
                    # It's just a date like "2026-09-02"
                    kickoff_dt = datetime.fromisoformat(kickoff_str)
                else:
                    kickoff_dt = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
                dated_fixtures.append(DatedFixture(
                    fixture_id=fx["match_id"],
                    home=fx["home_team"],
                    away=fx["away_team"],
                    league=fx["league"],
                    kickoff_utc=kickoff_dt
                ))
            except (ValueError, AttributeError) as e:
                print(f"  Warning: Could not parse kickoff for {fx['match_id']}: {e} (value: {fx['kickoff_utc']})")
                # Skip invalid fixtures for gate validation
        else:
            print(f"  Warning: Missing kickoff for {fx['match_id']}")

    print(f"Converted {len(dated_fixtures)} fixtures to DatedFixture objects")

    # Apply date gate for target date 2026-09-03
    target_date = date(2026, 9, 3)
    print(f"\nApplying date gate for target date: {target_date.isoformat()}")
    print("=" * 80)

    validated_fixtures, rejection_reasons = run_full_date_check(dated_fixtures, target_date)

    print(f"\nDate gate results:")
    print(f"  Input fixtures: {len(dated_fixtures)}")
    print(f"  Validated fixtures: {len(validated_fixtures)}")
    print(f"  Rejected fixtures: {len(rejection_reasons)}")

    if rejection_reasons:
        print(f"\nRejection reasons:")
        print("=" * 80)
        for reason in rejection_reasons[:10]:  # Show first 10
            print(f"  {reason}")
        if len(rejection_reasons) > 10:
            print(f"  ... and {len(rejection_reasons) - 10} more rejection reasons")

    # Show what survived
    print(f"\nValidated fixtures (first 10):")
    print("=" * 80)
    for i, vf in enumerate(validated_fixtures[:10]):
        print(f"{i+1:2d}. {vf.fixture_id}: {vf.home} v {vf.away} ({vf.league})")
        print(f"    Kickoff: {vf.kickoff_utc.isoformat()}")
    if len(validated_fixtures) > 10:
        print(f"    ... and {len(validated_fixtures) - 10} more validated fixtures")

if __name__ == "__main__":
    main()