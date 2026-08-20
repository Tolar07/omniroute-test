@echo off
REM Install Windows Task Scheduler job for auto-sync-commit
REM Run as Administrator for best results

set TASK_NAME=OLP_XDV_AutoSyncCommit
set NODE_EXE=C:\Program Files\nodejs\node.exe
set SCRIPT_PATH=C:\Users\Motunrayo\omniroute test\scripts\auto-sync-commit.js
set REPO_ROOT=C:\Users\Motunrayo\omniroute test

echo Creating scheduled task: %TASK_NAME%
echo   Every 5 minutes, runs: %NODE_EXE% "%SCRIPT_PATH%"
echo   Working directory: %REPO_ROOT%

schtasks /Create /TN "%TASK_NAME%" /TR "\"%NODE_EXe%\" \"%SCRIPT_PATH%\"" /SC MINUTE /MO 5 /ST 00:00 /RU "%USERNAME%" /F

if %errorlevel% equ 0 (
    echo.
    echo ✅ Task created successfully!
    echo.
    echo To verify: schtasks /Query /TN "%TASK_NAME%"
    echo To run now:  schtasks /Run /TN "%TASK_NAME%"
    echo To disable:  schtasks /Change /TN "%TASK_NAME%" /DISABLE
    echo To remove:   schtasks /Delete /TN "%TASK_NAME%" /F
) else (
    echo.
    echo ❌ Failed to create task. Try running as Administrator.
)

pause