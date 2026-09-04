import sys
sys.path.insert(0, r'C:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv')

try:
    from output.produce_bet import render_live_matches_section
    print('SUCCESS: render_live_matches_section imported')
    from fixtures_agent import fetch_flashscore
    from datetime import date
    today = date.today().isoformat()
    fixtures = fetch_flashscore(today)
    print(f'Found {len(fixtures)} FlashScore fixtures for {today}')
    for f in fixtures[:5]:
        print(f)
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()