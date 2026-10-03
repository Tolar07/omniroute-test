#!/usr/bin/env python3
"""
Tests for verification/fixture_matcher.py.

Standard-library only so it runs in any environment:
    python3 test_fixture_matcher.py     # plain runner (asserts)
    pytest test_fixture_matcher.py      # also works
"""

import sys
from pathlib import Path

# Ensure repo root is importable when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from verification.fixture_matcher import (
    normalize_team_name,
    teams_match,
    match_fixtures,
    unmatched_report,
    create_source_fixture,
)


def test_normalize_aliases_collapse_to_canonical():
    assert normalize_team_name("Man Utd") == "manchester united"
    assert normalize_team_name("Man United") == "manchester united"
    assert normalize_team_name("Manchester United") == "manchester united"
    # A name already in canonical form must not be re-expanded (regression guard).
    assert normalize_team_name("Tottenham Hotspur") == "tottenham hotspur"
    assert normalize_team_name("West Ham United") == "west ham united"
    assert normalize_team_name("Brighton & Hove Albion") == "brighton and hove albion"


def test_normalize_strips_club_affixes():
    assert normalize_team_name("Liverpool FC") == "liverpool"
    assert normalize_team_name("AS Roma") == "roma"
    # Never strip down to nothing.
    assert normalize_team_name("FC") == "fc"


def test_normalize_folds_accents_and_punctuation():
    assert normalize_team_name("Malmö FF") == normalize_team_name("Malmo FF")
    assert normalize_team_name("Bayer 04 Leverkusen") == "bayer 04 leverkusen"
    assert normalize_team_name("") == ""


def test_teams_match():
    assert teams_match("Man Utd", "Manchester United")
    assert teams_match("Brighton", "Brighton & Hove Albion")
    assert teams_match("Liverpool FC", "Liverpool")
    assert not teams_match("Arsenal", "Chelsea")
    assert not teams_match("Arsenal", "")


def test_create_source_fixture_handles_key_variants():
    # kickoff_utc key + home_team/away_team keys.
    f = create_source_fixture(
        {"home_team": "Man Utd", "away_team": "Liverpool",
         "kickoff_utc": "2026-09-06T13:00:00Z", "competition": "PL"},
        "SourceA",
    )
    assert f.home_team == "Man Utd"
    assert f.away_team == "Liverpool"
    assert f.league == "PL"
    assert f.kickoff_date == "2026-09-06"

    # No parseable date -> falls back to target_date.
    f2 = create_source_fixture(
        {"home": "A", "away": "B", "kickoff": "13:00"},
        "SourceB",
        target_date="2026-09-06",
    )
    assert f2.kickoff_date == "2026-09-06"


def test_cross_source_verification():
    """Same fixture from three sources with mixed key/name styles verifies once."""
    fixture_lists = {
        "FlashScore": [
            {"home": "Man Utd", "away": "Liverpool", "league": "PL",
             "kickoff_date": "2026-09-06T13:00:00Z"}
        ],
        "BBC Sport": [
            {"home": "Manchester United", "away": "Liverpool", "league": "PL",
             "kickoff": "13:00"}  # time only -> target_date fallback
        ],
        "SportyBet": [
            {"home": "Man United", "away": "Liverpool FC", "league": "PL",
             "kickoff_utc": "2026-09-06T13:00:00Z"}
        ],
    }
    matched = match_fixtures(fixture_lists, target_date="2026-09-06")
    assert len(matched) == 1
    fixture = matched[0]
    assert fixture.source_count == 3
    assert fixture.is_verified
    assert fixture.sources == {"FlashScore", "BBC Sport", "SportyBet"}

    report = unmatched_report(matched)
    assert report["total_fixtures"] == 1
    assert report["verified_fixtures"] == 1
    assert report["single_source_fixtures"] == 0
    assert report["verification_rate"] == 1.0


def test_single_source_not_verified():
    fixture_lists = {
        "FlashScore": [
            {"home": "Arsenal", "away": "Chelsea", "league": "PL",
             "kickoff_date": "2026-09-06"}
        ],
    }
    matched = match_fixtures(fixture_lists, target_date="2026-09-06")
    assert len(matched) == 1
    assert not matched[0].is_verified
    report = unmatched_report(matched)
    assert report["verified_fixtures"] == 0
    assert report["single_source_fixtures"] == 1


def test_different_dates_do_not_merge():
    """Same teams on different dates are distinct fixtures, not a false verify."""
    fixture_lists = {
        "FlashScore": [
            {"home": "Arsenal", "away": "Chelsea", "league": "PL",
             "kickoff_date": "2026-09-06"}
        ],
        "BBC Sport": [
            {"home": "Arsenal", "away": "Chelsea", "league": "PL",
             "kickoff_date": "2026-09-13"}
        ],
    }
    matched = match_fixtures(fixture_lists)
    assert len(matched) == 2
    assert all(not f.is_verified for f in matched)


def test_fixture_missing_team_is_skipped():
    fixture_lists = {
        "FlashScore": [
            {"home": "", "away": "Chelsea", "kickoff_date": "2026-09-06"},
            {"home": "Arsenal", "away": "Chelsea", "kickoff_date": "2026-09-06"},
        ],
    }
    matched = match_fixtures(fixture_lists, target_date="2026-09-06")
    assert len(matched) == 1  # the empty-home fixture is dropped


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERROR {test.__name__}: {exc!r}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
