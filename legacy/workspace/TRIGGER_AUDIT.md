# OLP XDV Automated Trigger Audit

This document enumerates all automated triggers in the OLP XDV system as requested in task 11.

## Summary of Automated Triggers

| Trigger Name | Schedule | Purpose | Script/Batch File |
|--------------|----------|---------|-------------------|
| **OLP XDV Daily Prefetch** | Daily 20:00 | Pre-fetch and cache external data | `run_daily.bat --prefetch-only` |
| **OLP XDV Daily Board** | Daily 22:00 | Full production cycle: SCAN → ingest → odds → engine → verify → board → log → notify | `run_daily.bat` |
| **OLP XDV Data Steward** | Daily 06:00, 15:00 | Data quality monitoring and maintenance | `steward.bat` |
| **OLP XDV Health Monitor** | Every 2 hours | System health checks and alerts | `health_monitor.bat` |
| **OLP XDV Dead Man's Switch** | Daily 08:00 | Safety mechanism to detect stalled processes | `dead_mans_switch.bat` |
| **OLP XDV Telegram Poller** | At logon (resident) | Telegram bot polling for commands | `telegram_poller.bat` |
| **OLP XDV Fixture Watcher** | (Not fully specified in install script) | Watch for fixture changes | `fixture_watcher.bat` |
| **Hourly Fixture Check** | Hourly (from JS script) | Refresh odds for upcoming matches | `hourly-fixture-check.js` |
| **Results Verification Agent** | Daily 22:00 (new) | Grade predictions against real results | `grade_results.py` (batch: `grade_results.bat`) |

## Detailed VERIFY RESULTS table output + running record summary` |

## Detailed Trigger Information

### 1. Daily Prefetch Task (20:00)
- **Script**: `run_daily.bat --prefetch-only`
- **Purpose**: Pre-fetch and cache all external data before the main 22:00 run
- **Location**: Defined in `setup_daily_board_task.ps1`

### 2. Daily Board Task (22:00)
- **Script**: `run_daily.bat`
- **Purpose**: Full production cycle including:
  - SCAN → ingest → odds → engine → verify → board → log → notify
  - Generates `output/boards/board_YYYY-MM-DD.json`
  - Delivers to Telegram (and WhatsApp/email if configured)
  - Updates brain runs table with full telemetry
- **Location**: Defined in `setup_daily_board_task.ps1`

### 3. Data Steward Task (06:00, 15:00)
- **Script**: `steward.bat`
- **Purpose**: Data quality monitoring and maintenance
- **Location**: Defined in `setup_steward_task.ps1`

### 4. Health Monitor Task (Every 2 hours)
- **Script**: `health_monitor.bat`
- **Purpose**: System health checks and alerts
- **Location**: Defined in `setup_health_monitor_task.ps1`

### 5. Dead Man's Switch (08:00)
- **Script**: `dead_mans_switch.bat`
- **Purpose**: Safety mechanism to detect stalled processes
- **Location**: Defined in `setup_dead_mans_switch_task.ps1`

### 6. Telegram Poller (At logon)
- **Script**: `telegram_poller.bat`
- **Purpose**: Telegram bot polling for commands (resident process)
- **Location**: Defined in `setup_poller_task.ps1`

### 7. Fixture Watcher
- **Script**: `fixture_watcher.bat`
- **Purpose**: Watch for fixture changes
- **Location**: Defined in `setup_fixture_watcher_task.ps1`

### 8. Hourly Fixture Check
- **Script**: `scripts/hourly-fixture-check.js`
- **Purpose**: 
  - Find fixtures in the database that haven't kicked off yet
  - Refresh their odds and verify data freshness
  - Run a lightweight pipeline pass on upcoming matches only
  - Update board if new fixtures appear or odds change significantly
  - Skip matches that have already kicked off
- **Schedule**: Hourly (implemented via Windows Task Scheduler)

### 9. Results Verification Agent (NEW - 22:00)
- **Script**: `grade_results.py`
- **Purpose**: 
  - Daily 22:00 run: grades logged predictions against real results
  - Tracks true win/loss record and CLV
  - Flags unconfirmed fixtures
  - Outputs frozen VERIFY RESULTS table + running record summary
  - Persists graded rows (CSV + JSON)
  - Sends Telegram/email/desktop notification
- **Schedule**: Daily at 22:00 (to be added)

## Implementation Notes for New Results Verification Agent

To add the Results Verification Agent to the automated triggers:

1. **Create a batch file**: `grade_results.bat` that calls:
   ```
   python grade_results.py --date %DATE%
   ```

2. **Create a setup script**: `setup_grade_results_task.ps1` following the pattern of other setup scripts

3. **Add to the scheduler**: Include in `install_scheduler_tasks.ps1` with:
   ```powershell
   @{ Name = "OLP XDV Results Verification"; Bat = "grade_results.bat"; Trigger = "Daily 22:00" }
   ```

4. **Timezone handling**: The system uses Africa/Lagos timezone (UTC+1) as evidenced by:
   - GitHub workflow showing "22:00 Africa/Lagos == 21:00 UTC"
   - All schedules should be specified in local time

## Files Related to Scheduling

- `scripts/install_scheduler_tasks.ps1` - Main installation script
- `scripts/setup_*.ps1` - Individual task setup scripts
- `.github/workflows/daily.yml` - GitHub Actions equivalent (21:00 UTC = 22:00 Africa/Lagos)
- `olp_xdv_agent/olp_xdv/docs/obsidian-vault/Loops.md` - Documentation of recurring loops

## Verification

All triggers can be verified by:
1. Checking Windows Task Scheduler for the listed tasks
2. Reviewing the `.ps1` setup scripts in `scripts/`
3. Checking the batch files they reference exist and are executable
4. Reviewing `Loops.md` in the obsidian vault for architectural intent

This audit covers all identifiable automated triggers in the OLP XDV system as of the current codebase state.