#!/usr/bin/env python
import sys
sys.path.insert(0, r'C:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv')
from data.multi_source_concrete import SportyBetOddsSource
source = SportyBetOddsSource()
result = source.fetch('Premier League')
print(f'Fixtures: {len(result["fixtures"])}')
if result["fixtures"]:
    fx = result["fixtures"][0]
    print(f'First fixture: {fx.home_team} vs {fx.away_team}')
    # Print available odds
    for attr in dir(fx):
        if attr.endswith('_odds') and getattr(fx, attr) is not None:
            print(f'  {attr}: {getattr(fx, attr).price}')
else:
    print('No fixtures')