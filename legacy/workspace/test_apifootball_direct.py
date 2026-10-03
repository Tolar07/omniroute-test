import os
import subprocess

# Load the API key from the olp_xdv .env file
env_path = r"c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\.env"
with open(env_path) as f:
    for line in f:
        if line.startswith("API_FOOTBALL_KEY="):
            os.environ["APIFOOTBALL_KEY"] = line.strip().split("=", 1)[1]
            break

# Run a quick test of just API-Football
import sys
sys.path.insert(0, r"c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv")
from data.apifootball_client import APIFootballClient, LEAGUE_ID_MAP

client = APIFootballClient()
today = "2026-09-07"

print(f"Testing API-Football for {today}...")
print(f"League IDs: {LEAGUE_ID_MAP}")

total_fixtures = 0
for league_name, league_id in LEAGUE_ID_MAP.items():
    if league_id is not None:
        try:
            fixtures = client.get_fixtures(today, league_id=league_id, season=2026)
            if fixtures:
                print(f"\n{league_name} (ID: {league_id}): {len(fixtures)} fixtures")
                for f in fixtures:
                    print(f"  {f.kickoff_utc[11:16] if len(f.kickoff_utc) >= 16 else 'TBD'} {f.home} vs {f.away} [{f.status}]")
                total_fixtures += len(fixtures)
        except Exception as e:
            print(f"  Error: {e}")

print(f"\nTotal API-Football fixtures for {today}: {total_fixtures}")