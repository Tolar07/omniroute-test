import re

# Read the file content
with open(r'c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\data\thesportsdb_fixtures.py', 'r', encoding='utf-8') as f:
    text = f.read()

all_teams = set()

# Extract teams from TEAM_ALIASES - pattern: "Team Name": "Model Key"
# This matches the key names in the inner dicts
team_alias_pattern = r'"([^"]+)":\s*"([^"]+)"'
matches = re.findall(team_alias_pattern, text)
for tsdb_name, model_key in matches:
    all_teams.add(tsdb_name)

# Extract teams from KNOWN_NEW_TO_DIVISION_2627 - pattern: ("Team Name", "Team Name")
known_new_pattern = r'"([^"]+)"\s*,\s*"([^"]+)"'
matches = re.findall(known_new_pattern, text)
for t1, t2 in matches:
    all_teams.add(t1)
    all_teams.add(t2)

# Also find tuples with single elements
single_pattern = r'\("([^"]+)",\)'
matches = re.findall(single_pattern, text)
for t in matches:
    all_teams.add(t)

# Filter out things that are clearly not team names
# Remove league names, country names, etc. by filtering common non-team patterns
filtered = {t for t in all_teams if len(t) > 1 and not t.isdigit()}

# Sort and print
for team in sorted(filtered):
    print(team)
print(f'\nTotal unique teams: {len(filtered)}')