import sys
sys.path.insert(0, 'olp_xdv_agent/olp_xdv')
from booking.bridge import load_sportybet_fixtures

print('Loading Premier League fixtures from SportyBet cache...')
try:
    fixtures = load_sportybet_fixtures('Premier League', days_ahead=3)
    print(f'Got {len(fixtures)} fixtures')
    if fixtures:
        for f in fixtures[:5]:
            print(f'  {f.home_team} vs {f.away_team} ({f.league}) - home:{f.home_odds} draw:{f.draw_odds} away:{f.away_odds}')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()