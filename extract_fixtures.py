import json
import os

fixtures_dir = "/c/Users/Motunrayo/omniroute test/olp_xdv_agent/olp_xdv/data/cache/sportybet/fixtures/"

for filename in sorted(os.listdir(fixtures_dir)):
    if not filename.endswith('.json'):
        continue
    league = filename[:-5]  # Remove .json
    filepath = os.path.join(fixtures_dir, filename)

    with open(filepath) as f:
        data = json.load(f)

    fixtures = data.get('fixtures', [])
    seen = set()
    for m in fixtures:
        if isinstance(m, dict):
            home = m.get('sportybet_home') or m.get('home_team') or '?'
            away = m.get('sportybet_away') or m.get('away_team') or '?'
            key = f"{home} vs {away}"
            seen.add(key)

    if seen:
        print(f"=== {league} ===")
        for s in sorted(seen):
            print(f"  {s}")
        print()