import sys
sys.path.insert(0, '.')
from data.multi_source_concrete import get_odds

print('Fetching odds for Premier League...')
try:
    odds = get_odds('Premier League')
    print(f'Got {len(odds)} fixtures with odds')
    if odds:
        for o in odds[:5]:
            print(f'  {o.home_team} vs {o.away_team}: home={o.home_odds}, draw={o.draw_odds}, away={o.away_odds}, source={o.source}')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()