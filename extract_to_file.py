import re

with open(r'c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\data\thesportsdb_fixtures.py', 'r', encoding='utf-8') as f:
    text = f.read()

all_teams = set()

team_alias_pattern = r'"([^"]+)":\s*"([^"]+)"'
matches = re.findall(team_alias_pattern, text)
for tsdb_name, model_key in matches:
    all_teams.add(tsdb_name)

known_new_pattern = r'"([^"]+)"\s*,\s*"([^"]+)"'
matches = re.findall(known_new_pattern, text)
for t1, t2 in matches:
    all_teams.add(t1)
    all_teams.add(t2)

single_pattern = r'\("([^"]+)",\)'
matches = re.findall(single_pattern, text)
for t in matches:
    all_teams.add(t)

filtered = {t for t in all_teams if len(t) > 1 and not t.isdigit()}

with open(r'c:\Users\Motunrayo\omniroute test\team_output.txt', 'w', encoding='utf-8') as out:
    for team in sorted(filtered):
        out.write(team + '\n')
    out.write(f'\nTotal unique teams: {len(filtered)}')