"""
API-Football client for structured fixture and odds data.

This client provides reliable access to fixture data via the API-Football service
with proper error handling, rate limit management, and environment-based configuration.
"""

import os
import time
import requests
from typing import List, Dict, Optional
from datetime import date, datetime
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Placeholder for league ID mapping - to be populated with actual IDs
# Format: {"League Name": league_id, ...}
LEAGUE_ID_MAP = {
    # These need to be confirmed via --list-leagues helper
    "Premier League": None,
    "La Liga": None,
    "Serie A": None,
    "Bundesliga": None,
    "Ligue 1": None,
    "Eredivisie": None,
    "Primeira Liga": None,
    "Belgian Pro League": None,
    "Scottish Premiership": None,
    "Swiss Super League": None,
    "Turkish Super Lig": None,
    # Add more as needed
}


class APIFootballError(Exception):
    """Custom exception for API-Football errors."""
    pass


class APIFootballClient:
    """
    Client for accessing API-Football fixtures and odds data.

    Features:
    - Environment-based API key configuration
    - Rate limit handling with exponential backoff
    - Comprehensive error handling
    - Structured data output compatible with fixture matcher
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the API-Football client.

        Args:
            api_key: API-Football API key. If None, reads from APIFOOTBALL_KEY env var.
        """
        self.api_key = api_key or os.getenv('APIFOOTBALL_KEY')
        if not self.api_key:
            raise ValueError("APIFOOTBALL_KEY environment variable must be set")

        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-apisports-key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Rate limit tracking
        self.requests_made = 0
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        Make a rate-limited request to the API-Football endpoint.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            APIFootballError: For API errors or rate limit issues
        """
        # Rate limiting: ensure minimum interval between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            self.requests_made += 1
            self.last_request_time = time.time()

            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited by API-Football. Waiting {retry_after} seconds.")
                time.sleep(retry_after)
                # Retry the request
                response = self.session.get(url, params=params, timeout=30)

            # Handle other HTTP errors
            if response.status_code != 200:
                error_msg = f"API-Football request failed: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('errors', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text}"
                raise APIFootballError(error_msg)

            data = response.json()

            # Check for API-level errors
            if data.get('errors'):
                raise APIFootballError(f"API-Football API error: {data['errors']}")

            return data

        except requests.exceptions.RequestException as e:
            raise APIFootballError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise APIFootballError(f"Invalid JSON response: {str(e)}")

    def get_fixtures(self, date_str: str, league_id: Optional[int] = None,
                     team_id: Optional[int] = None) -> List[Dict]:
        """
        Get fixtures for a specific date, optionally filtered by league or team.

        Args:
            date_str: Date in YYYY-MM-DD format
            league_id: Optional league ID to filter by
            team_id: Optional team ID to filter by

        Returns:
            List of fixture dictionaries in standardized format
        """
        params = {
            'date': date_str,
            'timezone': 'UTC'
        }

        if league_id is not None:
            params['league'] = league_id
        if team_id is not None:
            params['team'] = team_id

        try:
            data = self._make_request('fixtures', params)
            fixtures = []

            for item in data.get('response', []):
                fixture_info = item.get('fixture', {})
                league_info = item.get('league', {})
                teams_info = item.get('teams', {})

                # Extract fixture data
                fixture_date = fixture_info.get('date', '')
                fixture_timestamp = fixture_info.get('timestamp', 0)

                # Format kickoff time
                kickoff_time = "TBD"
                if fixture_date:
                    try:
                        dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
                        kickoff_time = dt.strftime('%H:%M')
                    except:
                        pass

                fixture_data = {
                    'league': league_info.get('name', 'Unknown'),
                    'home': teams_info.get('home', {}).get('name', ''),
                    'away': teams_info.get('away', {}).get('name', ''),
                    'kickoff': kickoff_time,
                    'kickoff_date': fixture_date[:10] if fixture_date else str(date.today()),
                    'fixture_id': str(fixture_info.get('id', '')),
                    'source': 'API-Football',
                    'fetched_at': datetime.utcnow().isoformat() + 'Z',
                    'status': fixture_info.get('status', {}).get('short', 'NS'),
                    'venue': fixture_info.get('venue', {}).get('name', ''),
                    'referee': fixture_info.get('referee', '')
                }

                fixtures.append(fixture_data)

            logger.info(f"Retrieved {len(fixtures)} fixtures from API-Football for {date_str}")
            return fixtures

        except APIFootballError as e:
            logger.error(f"Failed to get fixtures from API-Football: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting fixtures: {e}")
            return []

    def get_odds(self, fixture_id: str) -> List[Dict]:
        """
        Get odds for a specific fixture.

        Args:
            fixture_id: The fixture ID to get odds for

        Returns:
            List of odds dictionaries
        """
        if not fixture_id:
            return []

        params = {
            'fixture': fixture_id,
            'bet': '1'  # 1X2 market
        }

        try:
            data = self._make_request('odds', params)
            odds_list = []

            for item in data.get('response', []):
                bookmakers = item.get('bookmakers', [])
                for bookmaker in bookmakers:
                    bets = bookmaker.get('bets', [])
                    for bet in bets:
                        if bet.get('name') == 'Match Winner':  # 1X2 market
                            values = bet.get('values', [])
                            odds_data = {
                                'bookmaker': bookmaker.get('name', ''),
                                'market': bet.get('name', ''),
                                'fixture_id': fixture_id
                            }

                            # Extract 1X2 odds
                            for value in values:
                                if value.get('value') == 'Home':
                                    odds_data['home_odds'] = float(value.get('odd', 0))
                                elif value.get('value') == 'Draw':
                                    odds_data['draw_odds'] = float(value.get('odd', 0))
                                elif value.get('value') == 'Away':
                                    odds_data['away_odds'] = float(value.get('odd', 0))

                            odds_list.append(odds_data)

            return odds_list

        except APIFootballError as e:
            logger.error(f"Failed to get odds for fixture {fixture_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting odds: {e}")
            return []

    def get_leagues(self, country: Optional[str] = None,
                    name: Optional[str] = None) -> List[Dict]:
        """
        Get available leagues, optionally filtered by country or name.

        Args:
            country: Optional country name to filter by
            name: Optional league name to filter by

        Returns:
            List of league dictionaries
        """
        params = {}
        if country is not None:
            params['country'] = country
        if name is not None:
            params['name'] = name

        try:
            data = self._make_request('leagues', params)
            return data.get('response', [])
        except APIFootballError as e:
            logger.error(f"Failed to get leagues: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting leagues: {e}")
            return []

    def list_available_leagues(self) -> None:
        """
        Helper method to list all available leagues for ID mapping discovery.
        Run this once to populate LEAGUE_ID_MAP with correct IDs.
        """
        print("Fetching available leagues from API-Football...")
        leagues = self.get_leagues()

        if not leagues:
            print("No leagues retrieved.")
            return

        print("\nAvailable Leagues:")
        print("-" * 80)
        for league in leagues:
            league_info = league.get('league', {})
            country_info = league.get('country', {})
            league_id = league_info.get('id')
            league_name = league_info.get('name', 'Unknown')
            country_name = country_info.get('name', 'Unknown')

            print(f"ID: {league_id:>6} | {league_name:<30} | {country_name}")

        print("\nTo populate LEAGUE_ID_MAP, set the IDs for your target leagues:")
        print("Example:")
        print('LEAGUE_ID_MAP = {')
        print('    "Premier League": 39,')
        print('    "La Liga": 140,')
        print('    # ... etc.')
        print('}')

    def close(self):
        """Close the HTTP session."""
        self.session.close()


# Convenience functions for easy usage
def fetch_fixtures_for_date(date_str: str) -> List[Dict]:
    """
    Convenience function to get fixtures for a date using default client.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        List of fixture dictionaries
    """
    client = APIFootballClient()
    try:
        # Get fixtures for all known leagues
        all_fixtures = []
        for league_name, league_id in LEAGUE_ID_MAP.items():
            if league_id is not None:
                fixtures = client.get_fixtures(date_str, league_id=league_id)
                all_fixtures.extend(fixtures)
        return all_fixtures
    finally:
        client.close()


def fetch_odds_for_fixture(fixture_id: str) -> List[Dict]:
    """
    Convenience function to get odds for a fixture.

    Args:
        fixture_id: The fixture ID

    Returns:
        List of odds dictionaries
    """
    client = APIFootballClient()
    try:
        return client.get_odds(fixture_id)
    finally:
        client.close()


# Example usage and testing
if __name__ == "__main__":
    # Example: List available leagues (run once to get IDs)
    # api_key = os.getenv('APIFOOTBALL_KEY')
    # if api_key:
    #     client = APIFootballClient(api_key)
    #     client.list_available_leagues()
    #     client.close()
    # else:
    #     print("APIFOOTBALL_KEY environment variable not set")

    # Example: Get fixtures for today
    # today = date.today().isoformat()
    # fixtures = fetch_fixtures_for_date(today)
    # print(f"Found {len(fixtures)} fixtures for {today}")
    # for fixture in fixtures[:5]:  # Show first 5
    #     print(f"{fixture['home']} vs {fixture['away']} - {fixture['league']} at {fixture['kickoff']}")

    print("API-Football client module loaded successfully")
    print("To use:")
    print("  1. Set APIFOOTBALL_KEY environment variable")
    print("  2. Run list_available_leagues() to get league IDs")
    print("  3. Populate LEAGUE_ID_MAP with actual IDs")
    print("  4. Use fetch_fixtures_for_date() or APIFootballClient directly")