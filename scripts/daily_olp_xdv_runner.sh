#!/bin/bash
# Script to run OLP XDV pipeline and schedule tomorrow's run

echo "Running OLP XDV pipeline at $(date)"
cd olp_xdv_agent/olp_xdv && python run_daily.py

# Schedule tomorrow's run at 10:00 PM
TOMORROW_10PM=$(date -d "tomorrow 22:00" +"%M %H %d %m *" 2>/dev/null ||
                date -v +1d -v 22H -v 0M +"%M %H %d %m *" 2>/dev/null ||
                echo "0 22 * * *")  # fallback

# Use the fallback for safety
SCHEDULE_TIME="0 22 * * *"

echo "Scheduling next run for tomorrow at 10:00 PM with schedule: $SCHEDULE_TIME"
claude cron create --cron "$SCHEDULE_TIME" --prompt "$(pwd)/scripts/daily_olp_xdv_runner.sh" --durable true

echo "Daily runner completed and next run scheduled"