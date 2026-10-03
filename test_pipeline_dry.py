from olp_xdv_pipeline import run_pipeline
from datetime import date
today = date.today().isoformat()
print(f'Running pipeline for {today} in dry-run mode')
state = run_pipeline(season='2526', fixtures_season='2627', dry_run=True, date_str=today)
print('Pipeline completed')
# Optionally, we can check the state
print(f'State halted: {state.halted}')
print(f'Number of agent payloads: {len(state.payloads)}')