#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Register team-name-audit.js as a Windows Task Scheduler job (daily at 5am)

.DESCRIPTION
    Creates a scheduled task "OLP_XDV_TeamNameAudit" that runs daily at 05:00
    to audit club name discrepancies between TheSportsDB, SportyBet, Bet365,
    and model keys. Outputs JSON + Markdown reports and auto-applies safe fixes.

.NOTES
    Run as Administrator for best results (required for some Task Scheduler operations).
    The task runs under the current user context with highest privileges.
#>

param(
    [string]$ScriptPath = "c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\scripts\team-name-audit.js",
    [string]$NodePath = "node",
    [string]$TaskName = "OLP_XDV_TeamNameAudit",
    [string]$Description = "Daily 5am team name cross-reference audit (TheSportsDB, SportyBet, Bet365, model keys)",
    [string]$StartTime = "05:00",
    [switch]$Force
)

# Require admin for task registration
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "Not running as Administrator. Task registration may fail or run with limited privileges."
    Write-Host "Re-run PowerShell as Administrator for guaranteed success."
}

# Verify script exists
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

# Verify node exists
$nodeExe = (Get-Command $NodePath -ErrorAction SilentlyContinue).Source
if (-not $nodeExe) {
    Write-Error "Node.js not found in PATH. Install Node.js or provide -NodePath."
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask -and -not $Force) {
    Write-Host "Task '$TaskName' already exists. Use -Force to overwrite."
    exit 0
}

# Delete existing if forcing
if ($existingTask -and $Force) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed existing task '$TaskName'."
}

# Create action
$action = New-ScheduledTaskAction -Execute $nodeExe -Argument "`"$ScriptPath`"" -WorkingDirectory (Split-Path $ScriptPath)

# Create trigger (daily at 5am)
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Register task
$principal = New-ScheduledTaskPrincipal -UserId (Get-CimInstance Win32_ComputerSystem).UserName -LogonType Interactive -RunLevel Highest

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description $Description `
        -Force
    Write-Host "✅ Task '$TaskName' registered successfully."
    Write-Host "   Schedule: Daily at $StartTime"
    Write-Host "   Script: $ScriptPath"
    Write-Host "   Node: $nodeExe"
}
catch {
    Write-Error "Failed to register task: $_"
    exit 1
}

# Show task info
Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State, Triggers, Actions, Settings