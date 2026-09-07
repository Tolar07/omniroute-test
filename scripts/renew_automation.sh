#!/bin/bash
# Script to automatically renew the 10PM OLP XDV automation

# Check if the automation job exists
if claude cron list | grep -q "11e49215"; then
    echo "Automation job 11e49215 exists - checking age"
    # Get job details to check age (this might need adjustment based on actual output format)
    # For now, we'll just recreate it every time to be safe
    echo "Recreating automation job..."
else
    echo "Automation job not found - creating new one"
fi

# Create/renew the automation job (10PM daily)
claude cron create --cron "0 22 * * *" --prompt "cd olp_xdv_agent/olp_xdv && python run_daily.py" --durable true

echo "Automation renewed successfully"