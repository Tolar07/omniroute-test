@echo off
REM Auto Sync + Commit - Manual trigger for testing
REM Runs vault-memory sync then commits all changes

set REPO_ROOT=C:\Users\Motunrayo\omniroute test
set SYNC_SCRIPT=%REPO_ROOT%\olp_xdv_agent\olp_xdv\.claude\scripts\hooks\vault-memory-sync.js
set LOG_DIR=%REPO_ROOT%\logs\auto-sync
set LOG_FILE=%LOG_DIR%\auto-sync-%date:~-4,4%%date:~-10,2%%date:~-7,2%.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [====== AUTO SYNC + COMMIT STARTED %date% %time% ======] >> "%LOG_FILE%"
echo [====== AUTO SYNC + COMMIT STARTED %date% %time% ======]

REM Step 1: Vault <-> Memory sync (HR54)
echo [Step 1] Running vault-memory sync... >> "%LOG_FILE%"
echo [Step 1] Running vault-memory sync...
node "%SYNC_SCRIPT%" reconcile >> "%LOG_FILE%" 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Sync had issues (check log) >> "%LOG_FILE%"
)

REM Step 2: Git status
echo [Step 2] Checking git status... >> "%LOG_FILE%"
echo [Step 2] Checking git status...
git -C "%REPO_ROOT%" status --short >> "%LOG_FILE%" 2>&1

REM Step 3: Git add all
echo [Step 3] Staging all changes... >> "%LOG_FILE%"
echo [Step 3] Staging all changes...
git -C "%REPO_ROOT%" add -A >> "%LOG_FILE%" 2>&1

REM Step 4: Check for staged changes
echo [Step 4] Checking for staged changes... >> "%LOG_FILE%"
echo [Step 4] Checking for staged changes...
git -C "%REPO_ROOT%" diff --cached --name-only > "%REPO_ROOT%\staged_files.tmp" 2>&1
set /p STAGED=<"%REPO_ROOT%\staged_files.tmp"
if defined STAGED (
    echo [Step 5] Committing changes... >> "%LOG_FILE%"
    echo [Step 5] Committing changes...
    set TIMESTAMP=%date% %time%
    set MSG=chore(auto): vault-memory sync + changes %TIMESTAMP%
    git -C "%REPO_ROOT%" commit -m "%MSG%" -m "Auto-sync: HR54 bidirectional vault<->memory sync" -m "Co-Authored-By: Claude <noreply@anthropic.com>" >> "%LOG_FILE%" 2>&1
    if %errorlevel% equ 0 (
        echo [SUCCESS] Committed >> "%LOG_FILE%"
        echo [SUCCESS] Committed
    ) else (
        echo [WARN] Commit failed >> "%LOG_FILE%"
        echo [WARN] Commit failed
    )
) else (
    echo [Step 5] No staged changes to commit >> "%LOG_FILE%"
    echo [Step 5] No staged changes to commit
)

REM Step 6: Final status
echo [Step 6] Final status: >> "%LOG_FILE%"
echo [Step 6] Final status:
git -C "%REPO_ROOT%" status --short >> "%LOG_FILE%" 2>&1
git -C "%REPO_ROOT%" status --short

echo [====== AUTO SYNC + COMMIT COMPLETE %date% %time% ======] >> "%LOG_FILE%"
echo [====== AUTO SYNC + COMMIT COMPLETE %date% %time% ======]

del "%REPO_ROOT%\staged_files.tmp" 2>nul