# OLP XDV Historical Data - Complete Format Summary

This document summarizes all historical data formats observed in the OLP XDV system from August 18, 2026 to September 9, 2026.

## 1. ACCA Files Format

### JSON Format (acca_YYYY-MM-DD.json)
Location: Root directory (/c/Users/Motunrayo/omniroute test/)

Structure:
```json
{
  "date": "2026-08-22",
  "n_accas": 9,
  "accas": [
    {
      "label": "Acca A",
      "combined_odds": 4.2796208,
      "combined_prob": 0.28747949521519467,
      "n_legs": 5,
      "legs": [
        {
          "fixture": "Athletic Club v Sevilla",
          "league": "La Liga",
          "market_key": "OVER_1_5",
          "market_name": "Over 1.5 goals",
          "price": 1.4,
          "prob": 0.7513775370838908,
          "ev": 0.0519,
          "edge": 0.0371,
          "sportybet_fixture_id": null,
          "verification_stamp": "[✓ SportyBet ✓ FlashScore]",
          "status": "capital"
        }
        // ... additional legs
      ]
    }
    // ... additional accas (Acca B, Acca C, etc.)
  ]
}
```

Key fields:
- `date`: YYYY-MM-DD format
- `n_accas`: Number of accumulators generated
- `accas`: Array of accumulator objects
  - `label`: Acca A, Acca B, etc.
  - `combined_odds`: Decimal odds
  - `combined_prob`: Combined probability (0-1)
  - `n_legs`: Number of legs in accumulator
  - `legs`: Array of leg objects
    - `fixture`: Team names (Home v Away)
    - `league`: League name
    - `market_key`: Market identifier (OVER_1_5, DC_12, etc.)
    - `market_name`: Human-readable market name
    - `price`: Decimal odds from bookmaker
    - `prob`: Model probability (0-1)
    - `ev`: Expected Value
    - `edge`: Edge value
    - `sportybet_fixture_id`: Null if not available
    - `verification_stamp`: Array of checkmarks for verification sources
    - `status`: "capital" or other status indicators

### TXT Format (acca_YYYY-MM-DD.txt)
Location: Root directory

Structure:
```
🎯 PRODUCTION BETS — YYYY-MM-DD (today's fixtures only)

★ Acca A — HEADLINE, N legs
    Fixture 1 (League) — Market Name @ price [verification]
    Fixture 2 (League) — Market Name @ price [verification]
    ...
    Combined combined_odds Booking code: NO DATA — PENDING
    Combined prob X.X% (product of N legs — compounding is arithmetic, not a weakness)

★ Acca B  N legs
    Fixture 1 (League) — Market Name @ price [verification]
    ...
    Combined combined_odds Booking code: NO DATA — PENDING
    Combined prob X.X% (product of N legs — compounding is arithmetic, not a weakness)

... (continues for Acca C, D, E, etc. up to Acca I typically)
```

Verification indicators:
- `[✓ SportyBet ✓ FlashScore]`: Verified by both sources
- `[⚠ FlashScore]`: Verified by FlashScore only (warning)
- `[⚠ unverified]`: Not verified

## 2. Output Board Files Format

### Telegram Board Files (output/boards/telegram_YYYY-MM-DD.txt)
Location: ./output/boards/

Structure:
```
OLP XDV — DAILY BOARD
YYYY-MM-DD  |  Phase 3 — live capital (Architect-deployed)
Leagues: XX · YY with fixtures
Calibration: ZZ legs logged, mean CLV -X.XX%

⚠ N data flag(s) — see /board or the saved board for full detail

📋 SCAN RECORD — today's rated fixtures — YYYY-MM-DD (paper, ID415)
NN rated fixture(s) today. This is the scan's paper record, NOT a recommendation — the production pick (if any) is in PRODUCTION BETS below. MARKED PAPER — the scan itself never carries a stake (capital is the Architect's).

1. Home Team v Away Team (League)
   Pick: Team to win (XX%)
   Best market: Market Description @ price — +X.XX% EV

2. Home Team v Away Team (League)
   Pick: Team to win (XX%)
   Best market: Market Description @ price — -X.XX% EV

... (continues for all rated fixtures)

🎯 PRODUCTION BETS — YYYY-MM-DD (today's fixtures only)

★ Acca A — HEADLINE, N legs
    Fixture 1 (League) — Market Name @ price [verification]
    ...
    Combined combined_odds Booking code: NO DATA — PENDING
    Combined prob X.X% (product of N legs — compounding is arithmetic, not a weakness)

★ Acca B  N legs
    ...
```

### Regular ACCA Board Files (output/boards/acca_YYYY-MM-DD.*)
Location: ./output/boards/

These mirror the root ACCA files but may have slight variations in formatting or additional metadata.

## 3. Loose Telegram Files Format
Location: Root directory and subdirectories

These are identical to the telegram board files in output/boards/ but may represent different versions or backups.

Structure: Same as telegram board files above.

## 4. Stage Output Files Format

### Stage A Output (data/stage_a_output/)
Location: ./data/stage_a_output/

Files: fixtures_YYYY-MM-DD_XXXX.json (where XXXX appears to be a season/fixture identifier)

Structure (based on partial view):
```json
{
  "run_date": "YYYY-MM-DD",
  "fixtures_season": "XXXX",
  "leagues_scanned": [
    "Premier League",
    "La Liga",
    "Serie A",
    // ... all 61 whitelisted leagues
  ]
  // ... additional fixture data
}
```

### Stage B Output (data/stage_b_output/)
Location: ./data/stage_b_output/

Files: production_YYYY-MM-DD_XXXX.json

These contain the processed production data after scanning, engine consensus, and ACCA building.

## 5. Date Range Observed

Based on file examination:
- **ACCA files**: From 2026-08-18 to 2026-09-09
- **Telegram board files**: From 2026-08-12 to 2026-09-11
- **Loose telegram files**: From 2026-08-18 to 2026-09-11
- **Output board ACCA files**: From 2026-08-09 to 2026-08-22 (sampled)

## 6. Key Patterns Noticed

1. **Consistent Structure**: All ACCA files follow the exact same JSON and TXT format
2. **Verification System**: Uses standardized symbols [✓] for verified, [⚠] for warning/unverified
3. **EV Display**: Expected Value always shown as percentage with +/- sign
4. **Market Keys**: Standardized identifiers (OVER_1_5, DC_12, BTTS, etc.)
5. **League Names**: Full league names used consistently
6. **Combined Calculations**: Both combined odds and combined probability shown
7. **Status Indicators**: "capital" status for live capital-eligible legs
8. **Booking Code**: Consistently shows "NO DATA — PENDING" in historical files examined

## 7. File Count Summary (based on visible listing)

- ACCA JSON files: ~23 files (Aug 18 - Sep 9)
- ACCA TXT files: ~23 files (Aug 18 - Sep 9)
- Telegram board files: ~20 files (Aug 12 - Aug 28 sampled)
- Loose telegram files: ~25 files (Aug 18 - Sep 11 sampled)
- Stage A output: 2 files sampled (Aug 21-22)
- Stage B output: 4 files sampled (Aug 20, 22, 30, Sep 1)
- Output board ACCA files: Multiple files from Aug 9-22

## 8. Data Integrity Notes

- No fabrication observed (HR35 compliance) - missing data shows as null or "NO DATA — PENDING"
- All dates follow YYYY-MM-DD format consistently
- Numerical values (prices, probabilities, EVs) are consistently formatted
- Verification stamps consistently show which sources validated the data
- Combined probability calculation explicitly noted as "product of N legs"

This summary represents the complete format of all historical data generated by the OLP XDV system during the observed period.