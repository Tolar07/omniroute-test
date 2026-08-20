<#
.SYNOPSIS
    Sets up automated vault-memory sync + git commit every 5 minutes via Windows Task Scheduler

.DESCRIPTION
    Creates a scheduled task that runs auto-sync-commit.js every 5 minutes.
    This ensures HR54 compliance (vault<->memory sync) and the commit-always rule are enforced automatically.

.NOTES
    Run as Administrator for Task Scheduler to work properly.
    Requires Node.js in PATH.
#>

param()

$ErrorActionPreference = "Stop"

$RepoRoot = "C:\Users\Motunrayo\omniroute test"
$ScriptPath = Join-Path $RepoRoot "scripts\auto-sync-commit.js"
$NodePath = (Get-Command node).Source

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

$TaskName = "OLP_XDV_AutoSyncCommit"
$Action = New-ScheduledTaskAction -Execute $NodePath -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

# Check if task exists
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "Task '$TaskName' already exists. Updating..."
    Set-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings
} else {
    Write-Host "Creating new task '$TaskName'..."
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "OLP XDV: Auto vault-memory sync + git commit every 5 minutes (HR54 + commit-always)"
}

Write-Host "✅ Task '$TaskName' configured to run every 5 minutes"
Write-Host "   Script: $ScriptPath"
Write-Host "   Node:   $NodePath"
Write-Host ""
Write-Host "To verify: Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host "To run now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To disable: Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"