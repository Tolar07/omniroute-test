#!/usr/bin/env python3
"""
Odds collector for OLP XDV - continuously collects odds data from multiple sources
and stores it in the Brain database for continuous availability.
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Add parent to path so we can import OLP XDV modules
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "olp_xdv_agent" / "olp_xdv"))

from brain.store import Brain
from data.apifootball_client import APIFootballClient

def normalize_team_name(name: str) -> str:
    """Normalize team name for consistent matching."""
    if not name:
        return ""
    # Basic normalization - in practice would use more sophisticated matching
    return name.strip().lower()

def main():
    """Main odds collection function."""
    print(f"[odds-collector] Starting odds collection at {datetime.now(timezone.utc).isoformat()}")

    # Initialize Brain and API-Football client
    brain = Brain()
    api_client = APIFootballClient()

    try:
        # Get today's date for filtering
        today = datetime.now(timezone.utc).date().isoformat()

        # Fetch odds data from API-Football (primary source)
        print("[odds-collector] Fetching odds from API-Football...")
        # Limit to first 5 fixtures to avoid rate limits
        odds_data = api_client.get_odds_for_date(today, limit=5)

        if not odds_data:
            print("[odds-collector] No odds data received from API-Football")
            return

        print(f"[odds-collector] Received {len(odds_data)} odds records")

        # Process and store each odds record
        stored_count = 0
        for odds_record in odds_data:
            try:
                # Extract relevant fields
                home_team = normalize_team_name(odds_record.get('home_team', ''))
                away_team = normalize_team_name(odds_record.get('away_team', ''))
                match_date = odds_record.get('match_date', today)

                fixture_key: Tuple[str, str, str] = (home_team, away_team, match_date)

                market_type = odds_record.get('market_type', '1X2')  # Default to 1X2
                bookmaker = odds_record.get('bookmaker', 'API-Football')
                odds_value = odds_record.get('odds_value')
                odds_type = odds_record.get('odds_type', 'decimal')

                # Skip if essential data is missing
                if not all([home_team, away_team, odds_value is not None]):
                    continue

                # Store in Brain
                print(f"[odds-collector] Storing odds for {home_team} vs {away_team} on {match_date}")
                brain.store_odds_snapshot(
                    fixture_key=fixture_key,
                    market_type=market_type,
                    bookmaker=bookmaker,
                    odds_value=float(odds_value),
                    odds_type=odds_type,
                    source='API-Football',
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                print(f"[odds-collector] Stored odds for {home_team} vs {away_team}")

                stored_count += 1

            except (ValueError, TypeError) as e:
                print(f"[odds-collector] Error processing odds record (data issue): {e}")
                continue
            except Exception as e:
                print(f"[odds-collector] Error processing odds record: {e}")
                continue

        print(f"[odds-collector] Successfully stored {stored_count} odds records")

        # Also try to collect from other sources if available
        # For example, TheSportsDB or other odds providers
        # This would be implemented similarly

    except Exception as e:
        print(f"[odds-collector] Error in odds collection: {e}")
        import traceback
        traceback.print_exc()

    finally:
        brain.close()

    print(f"[odds-collector] Odds collection completed at {datetime.now(timezone.utc).isoformat()}")

if __name__ == "__main__":
    main()