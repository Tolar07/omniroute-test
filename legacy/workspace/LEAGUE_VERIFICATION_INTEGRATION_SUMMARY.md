# League Verification Integration Summary

## Overview
This document summarizes the integration of the league verification system into the OLP XDV framework as requested by the user. The verification system checks today's Flashscore fixtures against the whitelisted leagues configuration to ensure proper coverage.

## Files Created/Modified

### 1. New File: `olp_xdv_agent/olp_xdv/engine/league_verifier.py`
- Created the LeagueVerifier class with methods for:
  - Loading whitelisted leagues from config/leagues.json
  - Normalizing league names for comparison (removing " - " portions and country suffixes)
  - Loading and normalizing Flashscore league data
  - Verifying coverage between whitelisted leagues and today's fixtures
  - Generating verification reports with status determination
  - Providing recommendations for scanning frequency adjustments
  - Convenience function `run_daily_league_verification()` for easy integration

### 2. Modified File: `olp_xdv_agent/olp_xdv/olp_xdv_pipeline.py`
- Added imports for json, logging, pathlib, typing, and the LeagueVerifier
- Added league verification step in the `main()` function that runs before the pipeline starts
- Verification only runs in live mode (not dry-run)
- Uses the existing flashscore_leagues_sep4.json file (to be generated daily by the flashscore scraping process)
- Logs verification results and provides recommendations based on coverage percentage
- Does not halt the pipeline if verification fails (continues with warning)

## How It Works

1. **At Pipeline Start**: Before any agents run, the system checks for today's Flashscore data
2. **Normalization**: Both whitelisted leagues and Flashscore leagues are normalized for fair comparison:
   - Removes everything after " - " (e.g., "FA Cup - Qualification ENGLAND : Draw" → "FA Cup - Qualification")
   - Removes country suffixes (e.g., "Premier League ENGLAND : Standings" → "Premier League")
3. **Comparison**: Calculates intersection between whitelisted leagues and today's fixtures
4. **Reporting**: Generates a report with:
   - Coverage percentage (% of whitelisted leagues with fixtures today)
   - Status (EXCELLENT/GOOD/FAIR/POOR/NONE based on thresholds)
   - Lists of covered leagues, not-in-whitelist leagues, and missing leagues
5. **Recommendations**: Based on coverage percentage:
   - ≥15%: NORMAL scanning mode
   - 10-14%: REDUCED scanning frequency
   - 5-9%: MONITOR mode
   - <5%: PASSIVE mode (minimal scanning)

## Verification Results (Sept 4, 2026)
Based on the flashscore_leagues_sep4.json data:
- **Whitelisted leagues**: 67 (deploy_eligible: true)
- **Flashscore leagues**: 182 total entries
- **Normalized Flashscore leagues**: 116 unique leagues
- **Covered leagues**: 8 leagues
- **Coverage**: ~11.9% (8/67)
- **Status**: GOOD (based on ≥10% threshold)
- **Recommendation**: REDUCED scanning frequency

## Integration Points
The verification is integrated into `olp_xdv_pipeline.py` in the `main()` function, right after the Safe-Move git status check and before the pipeline execution begins. This ensures:
- Early detection of coverage issues
- Ability to adjust scanning behavior before resource-intensive agents run
- Non-blocking verification (pipeline continues even if verification fails)
- Logging of results for monitoring and alerting

## Future Enhancements
1. **Automatic Flashscore File Generation**: Instead of relying on a static file, integrate with the flashscore scraping system to generate today's fixtures file
2. **Configuration Options**: Add verification thresholds to config.py for easy adjustment
3. **Alerting**: Integrate with notification system to alert on low coverage
4. **Historical Tracking**: Store verification results over time for trend analysis
5. **Dynamic Adjustment**: Automatically adjust agent scanning behavior based on verification results

## Usage
The verification runs automatically whenever the OLP XDV pipeline runs:
```bash
python olp_xdv_pipeline.py --season 2526 --fixtures-season 2627
```

Or via run_daily.py:
```bash
python olp_xdv_agent/olp_xdv/run_daily.py
```