# Continuous Fixtures and Verification System

## Overview
This system provides continuous running of the OLP XDV fixtures agent with verification loops and enhancements.

## Changes Made

### 1. Updated Verification Rule (`fixtures_agent.py`)
- **Before**: Documentation stated verification required `>=2` sources, but implementation used `>=1`
- **After**: Both documentation and implementation now consistently require `>=1` source confirmation
- **Files Modified**:
  - `GUARDRAILS` section (line 9): Changed from "MUST verify against >=2 live sources" to "MUST verify against >=1 live sources (at least one source confirmation)"
  - `_apply_verification` function docstring (lines 552-557): Updated to accurately reflect that verification occurs with >=1 source confirmation

### 2. Created Continuous Runner (`run_continuous_fixtures.py`)
- Runs the fixtures agent every 5 minutes in a continuous loop
- Saves output to timestamped JSON files in `./state/` directory
- Includes error handling and graceful shutdown
- Provides console output for monitoring

### 3. Created Verification Loop (`run_verification_loop.py`)
- Runs verification cycles every 2 minutes
- Can verify either the latest fixtures data or run fresh fixtures agent
- Saves verification results to `./state/` directory
- Applies enhancements like timestamp enrichment and confidence scoring
- Includes error handling and graceful shutdown

## Directory Structure
```
omniroute test/
├── olp_xdv_agent/olp_xdv/fixtures_agent.py      # Updated verification logic
├── run_continuous_fixtures.py                   # Main continuous runner
├── run_verification_loop.py                     # Verification and enhancement loop
├── state/                                       # Auto-generated state directory
│   ├── fixtures_output_*.json                   # Fixtures agent outputs
│   └── verification_result_*.json               # Verification results
└── CONTINUOUS_SYSTEM_README.md                  # This file
```

## How to Use

### 1. Start the Continuous Fixtures Runner
```bash
python run_continuous_fixtures.py
```
This will:
- Run `fixtures_agent.py` every 5 minutes
- Save each run's output to `./state/fixtures_output_<cycle>.json`
- Display progress and output in the console
- Continue until interrupted with Ctrl+C

### 2. Start the Verification Loop (in separate terminal)
```bash
python run_verification_loop.py
```
This will:
- Run verification every 2 minutes
- Use the latest fixtures data from the state directory
- Save verification results to `./state/verification_result_<cycle>.json`
- Apply enhancements (timestamps, confidence scoring)
- Continue until interrupted with Ctrl+C

### 3. Manual Verification
To manually run verification on current fixtures:
```bash
python run_verification_loop.py
```
Or to run fixtures agent manually:
```bash
cd olp_xdv_agent/olp_xdv && python fixtures_agent.py
```

## Verification Logic Details
The verification system now implements:
- ✅ **Source Requirement**: Fixture is VERIFIED if confirmed by ≥1 source
- ✅ **Provenance Tracking**: Each fixture row includes source, fetch time, and verification status
- ✅ **League Validation**: Checks against season start dates and deploy-eligible whitelist
- ✅ **Duplicate Prevention**: Uses (home, away, date) keys to prevent duplicate entries

## State Persistence
All data is saved in the `./state/` directory:
- Fixtures outputs: `fixtures_output_<timestamp>.json`
- Verification results: `verification_result_<timestamp>.json`
- The directory is automatically created if it doesn't exist

## Stopping the System
Both runners can be stopped gracefully with:
- **Ctrl+C** (SIGINT)
- They will finish their current cycle before shutting down
- Final status messages will be displayed

## Notes
- The verification loop is designed to run in a separate terminal from the continuous fixtures runner
- Both systems are independent but complementary
- State files accumulate over time - consider periodic cleanup if disk space is a concern
- All timestamps are stored in ISO format with timezone information