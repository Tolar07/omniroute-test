"""
Fixture matcher for cross-source verification with team name normalization.

This module provides improved fixture matching that handles team name variations
while maintaining the OLP XDV verification standard of >=2 independent sources.
"""

from typing import List, Dict, Set, Tuple, Optional
import re
from dataclasses import dataclass
from datetime import date


@dataclass
class SourceFixture:
    """Represents a fixture from a single source."""
    home_team: str
    away_team: str
    league: str
    kickoff_utc: str  # ISO format timestamp or empty string
    raw_data: Dict  # Original source data for provenance

    @property
    def kickoff_date(self) -> str:
        """Extract date portion from kickoff_utc."""
        if self.kickoff_utc and len(self.kickoff_utc) >= 10:
            return self.kickoff_utc[:10]  # YYYY-MM-DD
        return str(date.today())  # Fallback to today


@dataclass
class MatchedFixture:
    """Represents a fixture matched across multiple sources."""
    home_team: str
    away_team: str
    league: str
    kickoff_date: str
    sources: Set[str]  # Names of sources that reported this fixture
    raw_data_list: List[Dict]  # Raw data from each source

    @property
    def is_verified(self) -> bool:
        """Fixture is verified if >=2 independent sources agree."""
        return len(self.sources) >= 2

    @property
    def source_count(self) -> int:
        """Number of sources reporting this fixture."""
        return len(self.sources)


def normalize_team_name(name: str) -> str:
    """
    Normalize team name for better matching across sources.
    Handles common variations and abbreviations.
    """
    if not name:
        return ""

    # Convert to lowercase and strip
    name = name.strip().lower()

    # Common team name variations
    variations = {
        r'\bman utd\b': 'manchester united',
        r'\bman united\b': 'manchester united',
        r'\bnewcastle\b': 'newcastle united',
        r'\bnewcastle utd\b': 'newcastle united',
        r'\btottenham\b': 'tottenham hotspur',
        r'\btottenham hotspurs\b': 'tottenham hotspur',
        r'\bwolves\b': 'wolverhampton wanderers',
        r'\bman city\b': 'manchester city',
        r'\bmanchester city\b': 'manchester city',
        r'\bbrighton\b': 'brighton & hove albion',
        r'\bwest ham\b': 'west ham united',
        r'\bwestham\b': 'west ham united',
        r'\bleicester\b': 'leicester city',
        r'\bleeds\b': 'leeds united',
        r'\baston villa\b': 'aston villa',
        r'\beverton\b': 'everton',
        r'\barsenal\b': 'arsenal',
        r'\bchelsea\b': 'chelsea',
        r'\bliverpool\b': 'liverpool',
    }

    # Apply variations
    for pattern, replacement in variations.items():
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

    # Remove extra whitespace and normalize
    name = ' '.join(name.split())

    return name


def teams_match(name1: str, name2: str) -> bool:
    """
    Check if two team names match using normalization.
    """
    if not name1 or not name2:
        return False

    norm1 = normalize_team_name(name1)
    norm2 = normalize_team_name(name2)

    return norm1 == norm2


def create_source_fixture(fixture_dict: Dict, source_name: str) -> SourceFixture:
    """
    Convert a fixture dictionary from a source into a SourceFixture.
    """
    return SourceFixture(
        home_team=fixture_dict.get("home", ""),
        away_team=fixture_dict.get("away", ""),
        league=fixture_dict.get("league", ""),
        kickoff_utc=fixture_dict.get("kickoff_date", ""),
        raw_data=fixture_dict
    )


def match_fixtures(fixture_lists: Dict[str, List[Dict]]) -> List[MatchedFixture]:
    """
    Match fixtures across multiple sources using improved team name matching.

    Args:
        fixture_lists: Dictionary mapping source names to lists of fixture dictionaries

    Returns:
        List of MatchedFixture objects with consolidated sources
    """
    # Map (norm_home, norm_away, date) -> list of source fixtures
    fixture_map: Dict[Tuple[str, str, str], List[Tuple[str, SourceFixture]]] = {}

    # Process each source's fixtures
    for source_name, fixtures in fixture_lists.items():
        for fixture_dict in fixtures:
            source_fixture = create_source_fixture(fixture_dict, source_name)

            # Normalize team names for matching
            home_norm = normalize_team_name(source_fixture.home_team)
            away_norm = normalize_team_name(source_fixture.away_team)
            date_key = source_fixture.kickoff_date

            # Create matching key
            key = (home_norm, away_norm, date_key)

            if key not in fixture_map:
                fixture_map[key] = []
            fixture_map[key].append((source_name, source_fixture))

    # Consolidate matches into MatchedFixture objects
    matched_fixtures: List[MatchedFixture] = []

    for (home_norm, away_norm, date_key), source_fixtures in fixture_map.items():
        # Extract unique sources
        sources = set(source_name for source_name, _ in source_fixtures)

        # Use the first source's raw data as representative (could be enhanced)
        # For now, collect all raw data
        raw_data_list = [sf.raw_data for _, sf in source_fixtures]

        # Use original team names from first source for display
        first_fixture = source_fixtures[0][1]

        matched_fixture = MatchedFixture(
            home_team=first_fixture.home_team,
            away_team=first_fixture.away_team,
            league=first_fixture.league,
            kickoff_date=date_key,
            sources=sources,
            raw_data_list=raw_data_list
        )

        matched_fixtures.append(matched_fixture)

    return matched_fixtures


def unmatched_report(matched_fixtures: List[MatchedFixture]) -> Dict[str, int]:
    """
    Generate a report showing verification statistics.

    Args:
        matched_fixtures: List of matched fixtures from match_fixtures()

    Returns:
        Dictionary with counts for monitoring
    """
    total_fixtures = len(matched_fixtures)
    verified_fixtures = sum(1 for f in matched_fixtures if f.is_verified)
    single_source_fixtures = sum(1 for f in matched_fixtures if f.source_count == 1)

    return {
        "total_fixtures": total_fixtures,
        "verified_fixtures": verified_fixtures,
        "single_source_fixtures": single_source_fixtures,
        "verification_rate": verified_fixtures / total_fixtures if total_fixtures > 0 else 0.0
    }


# Example usage and testing
if __name__ == "__main__":
    # Test team name normalization
    test_pairs = [
        ("Man Utd", "Manchester United"),
        ("Man United", "Manchester United"),
        ("Newcastle", "Newcastle United"),
        ("Newcastle Utd", "Newcastle United"),
        ("Tottenham", "Tottenham Hotspur"),
        ("Tottenham Hotspurs", "Tottenham Hotspur"),
        ("Wolves", "Wolverhampton Wanderers"),
        ("Man City", "Manchester City"),
        ("Brighton", "Brighton & Hove Albion"),
        ("West Ham", "West Ham United"),
        ("Westham", "West Ham United"),
        ("Leicester", "Leicester City"),
        ("Leeds", "Leeds United"),
        ("Aston Villa", "Aston Villa"),
        ("Everton", "Everton"),
        ("Arsenal", "Arsenal"),
        ("Chelsea", "Chelsea"),
        ("Liverpool", "Liverpool"),
    ]

    print("Team Name Normalization Tests:")
    for name1, name2 in test_pairs:
        match = teams_match(name1, name2)
        norm1 = normalize_team_name(name1)
        norm2 = normalize_team_name(name2)
        status = "✓" if match else "✗"
        print(f"{status} '{name1}' ({norm1}) vs '{name2}' ({norm2}) -> Match: {match}")

    print("\n" + "="*50)

    # Test fixture matching
    flashscore_fixtures = [
        {
            "home": "Man Utd",
            "away": "Liverpool",
            "league": "Premier League",
            "kickoff_date": "2026-09-06T13:00:00Z"
        }
    ]

    bbc_fixtures = [
        {
            "home": "Manchester United",
            "away": "Liverpool",
            "league": "Premier League",
            "kickoff": "13:00"
        }
    ]

    sportybet_fixtures = [
        {
            "home": "Man United",
            "away": "Liverpool FC",
            "league": "Premier League",
            "kickoff_utc": "2026-09-06T13:00:00Z"
        }
    ]

    fixture_lists = {
        "FlashScore": flashscore_fixtures,
        "BBC Sport": bbc_fixtures,
        "SportyBet live": sportybet_fixtures
    }

    matched = match_fixtures(fixture_lists)
    report = unmatched_report(matched)

    print(f"Matching Results:")
    print(f"Total fixtures: {report['total_fixtures']}")
    print(f"Verified fixtures (≥2 sources): {report['verified_fixtures']}")
    print(f"Single-source fixtures: {report['single_source_fixtures']}")
    print(f"Verification rate: {report['verification_rate']:.1%}")

    for fixture in matched:
        print(f"\nFixture: {fixture.home_team} vs {fixture.away_team}")
        print(f"League: {fixture.league}")
        print(f"Date: {fixture.kickoff_date}")
        print(f"Sources: {', '.join(sorted(fixture.sources))}")
        print(f"Verified: {fixture.is_verified}")