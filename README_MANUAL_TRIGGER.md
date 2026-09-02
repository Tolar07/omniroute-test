# Manual Pipeline Trigger via Telegram

The `telegram_trigger_listener.py` script enables manual triggering and status checking of the OLP XDV nightly pipeline via Telegram commands.

## Commands

- `/run_now` - Triggers `run_night_pipeline.py` immediately and replies when done
- `/status` - Reports today's completion marker without running anything

## Setup

1. Ensure the following environment variables are set (they are already in `olp_xdv_agent/olp_xdv/.env`):
   - `TELEGRAM_BOT_TOKEN` (from `olp_xdv_agent/olp_xdv/.env`)
   - `TELEGRAM_CHAT_ID` (from `olp_xdv_agent/olp_xdv/.env`)

2. The listener can be run in the same process as your existing Telegram bot to avoid needing two persistent processes.

3. Ensure `run_night_pipeline.py`, `auto_remediate.py`, and `git_sync.py` are present in the workspace root.

## Files Created

- `telegram_trigger_listener.py` - Main listener script
- `auto_remediate.py` - Auto-remediation hook (already existed)
- `run_night_pipeline.py` - Stage-based pipeline wrapper (already existed)
- `INCIDENTS.md` - Auto-remediation audit log (already existed)
- `PROTECTED_RULES.md` - Protected constants reference (already existed)

## Notes

- The listener uses long-polling and must remain running to hear commands.
- It deliberately runs the pipeline in foreground to prevent overlapping runs.
- All stage failures trigger Telegram alerts and auto-remediation attempts.
- Completion markers are written to `run_markers/` for watchdog and status checking.
- The listener respects `PIPELINE_SCRIPT`, `PIPELINE_MARKER_DIR`, and other environment variables for configurability.

## Verification

Syntax verified for all Python files:
- `telegram_trigger_listener.py`: OK
- `auto_remediate.py`: OK
- `run_night_pipeline.py`: OK

Environment variables are present in `olp_xdv_agent/olp_xdv/.env`.

To start the listener:
```bash
# From workspace root, ensure you have the olp_xdv agent's .env loaded
export $(grep -v '^#' olp_xdv_agent/olp_xdv/.env | xargs)
python telegram_trigger_listener.py
```