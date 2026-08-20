<#
.SYNOPSIS
    Sets up hourly match analysis service via Windows Task Scheduler

.DESCRIPTION
    Creates a scheduled task that runs hourly-match-analysis.js every hour.
    This teaches the framework from match results for continuous learning.

.NOTES
    Run as Administrator for Task Scheduler to work properly.
    Requires Node.js in PATH and SQLite3 installed.
#>

param()

$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\Motunrayo\omniroute test"
$ScriptPath = Join-Path $RepoRoot "olp_xdv_agent\olp_xdv\scripts\hourly-match-analysis.js"
$NodePath = (Get-Command node).Source

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

# Check for sqlite3
$SqlitePath = (Get-Command sqlite3 -ErrorAction SilentlyContinue).Source
if (-not $SqlitePath) {
    Write-Warning "sqlite3 not found in PATH. Install with: winget install sqlite"
    Write-Warning "The analysis script requires sqlite3 to query the brain database."
}

$TaskName = "OLP_XDV_HourlyMatchAnalysis"
$Action = New-ScheduledTaskAction -Execute $NodePath -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

# Check if task exists
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "Task '$TaskName' already exists. Updating..."
    Set-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings
} else {
    Write-Host "Creating new task '$TaskName'..."
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "OLP XDV: Hourly match analysis for continuous learning (checks settled matches, updates weights)"
}

Write-Host "✅ Task '$TaskName' configured to run every hour"
Write-Host "   Script: $ScriptPath"
Write-Host "   Node:   $NodePath"
Write-Host ""
Write-Host "To verify: Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host "To run now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To disable: Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host ""
Write-Host "Logs: $RepoRoot\logs\hourly-analysis\"
Write-Host "Learning data: $RepoRoot\olp_xdv_agent\olp_xdv\data\learning\"