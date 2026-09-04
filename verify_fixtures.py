import json
import re

# Load whitelist
with open('olp_xdv_agent/olp_xdv/config/leagues.json', 'r') as f:
    leagues_data = json.load(f)

whitelisted = set()
for league in leagues_data['leagues']:
    if league.get('deploy_eligible', False):
        whitelisted.add(league['name'])

print(f"Whitelisted leagues count: {len(whitelisted)}")

# Load Flashscore leagues
with open('flashscore_leagues_sep4.json', 'r') as f:
    flashscore_data = json.load(f)

flashscore_leagues = flashscore_data['leagues']
print(f"Flashscore leagues count: {len(flashscore_leagues)}")

def normalize_league_name(name):
    # Step 1: Remove everything after " - " (space hyphen space) if present
    if " - " in name:
        name = name.split(" - ")[0]
    # Step 2: Remove the country suffix and everything after
    # Pattern: space, then one or more uppercase letters (the country), then space, colon, then anything
    # We remove from the first occurrence of this pattern to the end
    name = re.sub(r'\s+[A-Z]+\s*:.*', '', name)
    return name.strip()

# Map Flashscore leagues to normalized names
normalized_to_original = {}
normalized_set = set()
for league in flashscore_leagues:
    normalized = normalize_league_name(league)
    normalized_to_original[normalized] = league
    normalized_set.add(normalized)

print(f"Normalized Flashscore leagues count: {len(normalized_set)}")

# Find covered leagues (intersection)
covered = whitelisted.intersection(normalized_set)
not_in_whitelist = normalized_set - whitelisted
missing_from_fixtures = whitelisted - normalized_set

print("\n=== Covered leagues (in whitelist and today's fixtures) ===")
for league in sorted(covered):
    print(f"  {league}")

print("\n=== Leagues in today's fixtures but NOT in whitelist ===")
for league in sorted(not_in_whitelist):
    original = normalized_to_original[league]
    print(f"  {league} (from: '{original}')")

print("\n=== Whitelisted leagues NOT in today's fixtures ===")
for league in sorted(missing_from_fixtures):
    print(f"  {league}")

print(f"\nSummary:")
print(f"  Whitelisted leagues: {len(whitelisted)}")
print(f"  Flashscore leagues (normalized): {len(normalized_set)}")
print(f"  Covered: {len(covered)}")
print(f"  Not in whitelist: {len(not_in_whitelist)}")
print(f"  Missing from fixtures: {len(missing_from_fixtures)}")