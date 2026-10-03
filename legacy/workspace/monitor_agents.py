#!/usr/bin/env python3
"""
Continuous monitoring agent for OLP XDV fixtures and odds collection
"""

import time
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import os

# Add OLP XDV modules to path
sys.path.insert(0, str(Path(__file__).parent / "olp_xdv_agent" / "olp_xdv"))

from brain.store import Brain
from fixtures_agent import FixturesAgent
from collect_odds import collect_odds  # This would be the odds collection function

def get_current_timestamp():
    """Get current UTC timestamp for comparison"""
    return datetime.now(timezone.utc).isoformat()

def check_new_odds(brain: Brain, last_check_time: str = None):
    """Check for new odds data in the database"""
    if last_check_time is None:
        # First run, check all odds
        count = brain._conn.execute("SELECT COUNT(*) FROM odds_history").fetchone()[0]
        print(f"[{get_current_timestamp()}] Initial odds check: {count} records")
        return count

    # Get the last check time
    last_check = datetime.fromisoformat(last_check_time)

    # Count records with newer timestamps
    query = """
    SELECT COUNT(*) FROM odds_history
    WHERE retrieved_at > ?
    """
    count = brain._conn.execute(query, (last_check,)).fetchone()[0]
    print(f"[{get_current_timestamp()}] New odds records since {last_check_time}: {count}")
    return count

def check_new_fixtures(brain: Brain, last_check_time: str = None):
    """Check for new verified fixtures"""
    if last_check_time is None:
        # First run, check all fixtures
        count = brain._conn.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
        print(f"[{get_current_timestamp()}] Initial fixtures check: {count} records")
        return count

    # Get the last check time
    last_check = datetime.fromisoformat(last_check_time)

    # Count fixtures with newer timestamps (simplified - in reality would check verification status)
    query = """
    SELECT COUNT(*) FROM fixtures
    WHERE retrieved_at > ?
    """
    count = brain._conn.execute(query, (last_check,)).fetchone()[0]
    print(f"[{get_current_timestamp()}] New fixtures since {last_check_time}: {count}")
    return count

def monitor_loop():
    """Main monitoring loop"""
    print(f"[{get_current_timestamp()}] Starting continuous monitoring...")

    brain = Brain()
    last_odds_check = None
    last_fixture_check = None

    try:
        while True:
            # Check for new odds
            new_odds_count = check_new_odds(brain, last_odds_check)
            if new_odds_count > 0:
                print(f"[{get_current_timestamp()}] New odds data detected - triggering refresh")
                # In a real system, this would trigger data processing

            # Check for new fixtures
            new_fixture_count = check_new_fixtures(brain, last_fixture_check)
            if new_fixture_count > 0:
                print(f"[{get_current_timestamp()}] New fixtures detected - updating status")

            # Update last check times
            last_odds_check = get_current_timestamp()
            last_fixture_check = get_current_timestamp()

            # Wait 5 minutes before next check
            time.sleep(300)

    except KeyboardInterrupt:
        print(f"[{get_current_timestamp()}] Monitoring stopped by user")
    except Exception as e:
        print(f"[{get_current_timestamp()}] Monitoring error: {e}")
        raise
    finally:
        brain.close()

if __name__ == "__main__":
    monitor_loop()