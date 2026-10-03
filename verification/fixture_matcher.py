"""
Fixture matcher for cross-source verification with team name normalization.

This module provides improved fixture matching that handles team name variations
while maintaining the OLP XDV verification standard of >=2 independent sources.

The matcher is deliberately dependency-free (standard library only) so it can be
imported by any collector/agent regardless of the runtime environment.
"""

from typing import List, Dict, Set, Tuple, Optional
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date


# Keys that different sources use to carry the kickoff timestamp/date.
# Checked in priority order; the first non-empty value wins.
KICKOFF_KEYS: Tuple[str, ...] = (
    "kickoff_utc",
    "commence_time",
    "start_time",
    "datetime",
    "kickoff_date",
    "date",
    "kickoff",
)

# Common club affixes stripped from the start/end of a normalized name so that,
# e.g., "Liverpool FC" matches "Liverpool". Only stripped when at least one other
# token remains, so a club literally named after an affix is never emptied.
CLUB_AFFIXES: Set[str] = {
    "fc", "afc", "cf", "sc", "ac", "as", "ss", "us", "sv", "fk", "if",
    "bk", "rc", "ud", "sd", "ec", "cp", "cd", "club", "calcio",
}

# Whole-name alias map: short/variant forms -> canonical long form. Keys and
# values are stored in already-cleaned form (lowercase, accent-folded, no
# punctuation, "and" spelled out). Lookup is exact on the cleaned name, so a name
# that is already canonical (e.g. "manchester united") is never re-expanded.
_TEAM_ALIASES: Dict[str, str] = {
    "man utd": "manchester united",
    "man united": "manchester united",
    "man u": "manchester united",
    "newcastle": "newcastle united",
    "newcastle utd": "newcastle united",
    "tottenham": "tottenham hotspur",
    "tottenham hotspurs": "tottenham hotspur",
    "spurs": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "man city": "manchester city",
    "brighton": "brighton and hove albion",
    "west ham": "west ham united",
    "westham": "west ham united",
    "leicester": "leicester city",
    "leeds": "leeds united",
    "nott m forest": "nottingham forest",
    "nottm forest": "nottingham forest",
}


@dataclass
class SourceFixture:
    """Represents a fixture from a single source."""
    home_team: str
    away_team: str
    league: str
    kickoff_utc: str  # ISO timestamp / date / time string, or empty string
    raw_data: Dict  # Original source data for provenance
    resolved_date: str = ""  # YYYY-MM-DD after key/target-date resolution

    @property
    def kickoff_date(self) -> str:
        """Date portion used for matching (resolved at creation time)."""
        if self.resolved_date:
            return self.resolved_date
        extracted = _date_from_kickoff(self.kickoff_utc)
        return extracted or str(date.today())


@dataclass
class MatchedFixture:
    """Represents a fixture matched across multiple sources."""
    home_team: str
    away_team: str
    league: str
    kickoff_date: str
    sources: Set[str]  # Names of sources that reported this fixture
    raw_data_list: List[Dict] = field(default_factory=list)  # Raw data per source

    @property
    def is_verified(self) -> bool:
        """Fixture is verified if >=2 independent sources agree."""
        return len(self.sources) >= 2

    @property
    def source_count(self) -> int:
        """Number of sources reporting this fixture."""
        return len(self.sources)


def _strip_accents(text: str) -> str:
    """Fold accented characters to ASCII (e.g. 'Malmö' -> 'malmo')."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_team_name(name: str) -> str:
    """
    Normalize a team name for robust matching across sources.

    Pipeline: lowercase -> accent-fold -> alias expansion -> '&'/'and' unify ->
    punctuation removal -> club-affix stripping -> whitespace collapse.
    """
    if not name:
        return ""

    # Lowercase, strip, fold accents.
    name = _strip_accents(name.strip().lower())

    # Unify ampersand with the word "and" so "Brighton & Hove" == "Brighton and Hove".
    name = name.replace("&", " and ")

    # Drop any remaining punctuation, keep alphanumerics and spaces.
    name = re.sub(r"[^a-z0-9]+", " ", name)

    # Tokenize and strip leading/trailing club affixes (never emptying the name).
    tokens = [t for t in name.split() if t]
    while len(tokens) > 1 and tokens[0] in CLUB_AFFIXES:
        tokens.pop(0)
    while len(tokens) > 1 and tokens[-1] in CLUB_AFFIXES:
        tokens.pop()
    cleaned = " ".join(tokens)

    # Map recognised short/variant forms to a single canonical name. Exact lookup
    # avoids re-expanding a name that is already in canonical long form.
    return _TEAM_ALIASES.get(cleaned, cleaned)


def teams_match(name1: str, name2: str) -> bool:
    """Check if two team names refer to the same team after normalization."""
    if not name1 or not name2:
        return False
    return normalize_team_name(name1) == normalize_team_name(name2)


def _date_from_kickoff(value: str) -> str:
    """Extract a YYYY-MM-DD date from an arbitrary kickoff string, or ''."""
    if not value:
        return ""
    match = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
    return match.group(0) if match else ""


def _extract_kickoff(fixture_dict: Dict) -> str:
    """Return the first non-empty kickoff-like value from a fixture dict."""
    for key in KICKOFF_KEYS:
        value = fixture_dict.get(key)
        if value:
            return str(value)
    return ""


def create_source_fixture(
    fixture_dict: Dict,
    source_name: str,
    target_date: Optional[str] = None,
) -> SourceFixture:
    """
    Convert a fixture dictionary from a source into a SourceFixture.

    Handles the different team keys ("home"/"home_team", "away"/"away_team") and
    kickoff keys used across sources. When a source omits a parseable date, the
    supplied ``target_date`` (the day being scanned) is used as the fallback so
    that same-day fixtures from different sources still line up.
    """
    home = fixture_dict.get("home") or fixture_dict.get("home_team") or ""
    away = fixture_dict.get("away") or fixture_dict.get("away_team") or ""
    league = fixture_dict.get("league") or fixture_dict.get("competition") or ""

    kickoff = _extract_kickoff(fixture_dict)
    resolved_date = _date_from_kickoff(kickoff) or target_date or str(date.today())

    return SourceFixture(
        home_team=home,
        away_team=away,
        league=league,
        kickoff_utc=kickoff,
        raw_data=fixture_dict,
        resolved_date=resolved_date,
    )


def match_fixtures(
    fixture_lists: Dict[str, List[Dict]],
    target_date: Optional[str] = None,
) -> List[MatchedFixture]:
    """
    Match fixtures across multiple sources using normalized team names.

    Args:
        fixture_lists: Mapping of source name -> list of fixture dictionaries.
        target_date: Optional YYYY-MM-DD scan date used as the date fallback for
            sources that omit a parseable kickoff date.

    Returns:
        List of MatchedFixture objects with consolidated sources.
    """
    fixture_map: Dict[Tuple[str, str, str], List[Tuple[str, SourceFixture]]] = {}

    for source_name, fixtures in fixture_lists.items():
        for fixture_dict in fixtures:
            source_fixture = create_source_fixture(
                fixture_dict, source_name, target_date=target_date
            )

            home_norm = normalize_team_name(source_fixture.home_team)
            away_norm = normalize_team_name(source_fixture.away_team)

            # A fixture with no identifiable teams cannot be matched.
            if not home_norm or not away_norm:
                continue

            key = (home_norm, away_norm, source_fixture.kickoff_date)
            fixture_map.setdefault(key, []).append((source_name, source_fixture))

    matched_fixtures: List[MatchedFixture] = []
    for (_home_norm, _away_norm, date_key), source_fixtures in fixture_map.items():
        sources = {source_name for source_name, _ in source_fixtures}
        raw_data_list = [sf.raw_data for _, sf in source_fixtures]
        first_fixture = source_fixtures[0][1]

        matched_fixtures.append(
            MatchedFixture(
                home_team=first_fixture.home_team,
                away_team=first_fixture.away_team,
                league=first_fixture.league,
                kickoff_date=date_key,
                sources=sources,
                raw_data_list=raw_data_list,
            )
        )

    return matched_fixtures


def unmatched_report(matched_fixtures: List[MatchedFixture]) -> Dict[str, float]:
    """
    Generate verification statistics for monitoring.

    Returns counts plus the verification rate (verified / total).
    """
    total_fixtures = len(matched_fixtures)
    verified_fixtures = sum(1 for f in matched_fixtures if f.is_verified)
    single_source_fixtures = sum(1 for f in matched_fixtures if f.source_count == 1)

    return {
        "total_fixtures": total_fixtures,
        "verified_fixtures": verified_fixtures,
        "single_source_fixtures": single_source_fixtures,
        "verification_rate": (
            verified_fixtures / total_fixtures if total_fixtures > 0 else 0.0
        ),
    }


# Example usage and manual smoke test.
if __name__ == "__main__":
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
        ("Liverpool FC", "Liverpool"),
        ("Malmö FF", "Malmo FF"),
    ]

    print("Team Name Normalization Tests:")
    for name1, name2 in test_pairs:
        match = teams_match(name1, name2)
        status = "OK " if match else "XX "
        print(
            f"{status}'{name1}' ({normalize_team_name(name1)}) vs "
            f"'{name2}' ({normalize_team_name(name2)}) -> Match: {match}"
        )

    print("\n" + "=" * 50)

    scan_date = "2026-09-06"
    fixture_lists = {
        "FlashScore": [
            {
                "home": "Man Utd",
                "away": "Liverpool",
                "league": "Premier League",
                "kickoff_date": "2026-09-06T13:00:00Z",
            }
        ],
        "BBC Sport": [
            {
                "home": "Manchester United",
                "away": "Liverpool",
                "league": "Premier League",
                "kickoff": "13:00",  # time only -> uses target_date
            }
        ],
        "SportyBet live": [
            {
                "home": "Man United",
                "away": "Liverpool FC",
                "league": "Premier League",
                "kickoff_utc": "2026-09-06T13:00:00Z",
            }
        ],
    }

    matched = match_fixtures(fixture_lists, target_date=scan_date)
    report = unmatched_report(matched)

    print("Matching Results:")
    print(f"Total fixtures: {report['total_fixtures']}")
    print(f"Verified fixtures (>=2 sources): {report['verified_fixtures']}")
    print(f"Single-source fixtures: {report['single_source_fixtures']}")
    print(f"Verification rate: {report['verification_rate']:.1%}")

    for fixture in matched:
        print(f"\nFixture: {fixture.home_team} vs {fixture.away_team}")
        print(f"League: {fixture.league}")
        print(f"Date: {fixture.kickoff_date}")
        print(f"Sources: {', '.join(sorted(fixture.sources))}")
        print(f"Verified: {fixture.is_verified}")
