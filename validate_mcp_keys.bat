@echo off
REM MCP Server Key Validation & Startup Script for Windows
REM Run this before starting Claude Code to verify all keys are present

echo 🔍 Validating MCP Server Configuration...
echo.

REM Load .env if it exists
if exist .env (
    for /f "tokens=* delims=" %%a in ('type .env ^| findstr /v "^#"') do (
        set "%%a"
    )
    echo ✅ Loaded .env file
) else (
    echo ⚠️  No .env file found. Copy .env.example to .env and add your keys
    echo    copy .env.example .env
)

echo.
echo 📋 Checking API Keys:
echo.

REM Perplexity
if defined PERPLEXITY_API_KEY (
    if "%PERPLEXITY_API_KEY%" NEQ "your_perplexity_key_here" (
        echo ✅ PERPLEXITY_API_KEY: Set (%PERPLEXITY_API_KEY:~0,8%...)
    ) else (
        echo ❌ PERPLEXITY_API_KEY: MISSING - Get key at https://www.perplexity.ai/settings/api
        set MISSING=1
    )
) else (
    echo ❌ PERPLEXITY_API_KEY: MISSING - Get key at https://www.perplexity.ai/settings/api
    set MISSING=1
)

REM Firecrawl
if defined FIRECRAWL_API_KEY (
    if "%FIRECRAWL_API_KEY%" NEQ "your_firecrawl_key_here" (
        echo ✅ FIRECRAWL_API_KEY: Set (%FIRECRAWL_API_KEY:~0,8%...)
    ) else (
        echo ⚠️  FIRECRAWL_API_KEY: Not set (optional - keyless mode works with rate limits)
        echo    Get key at https://firecrawl.dev for full features
    )
) else (
    echo ⚠️  FIRECRAWL_API_KEY: Not set (optional - keyless mode works with rate limits)
    echo    Get key at https://firecrawl.dev for full features
)

echo.
echo 🌐 Checking Chrome/Playwright Setup:
echo.

REM Check Chrome
where google-chrome >nul 2>&1 && echo ✅ Chrome: Found || (
    where chromium >nul 2>&1 && echo ✅ Chromium: Found || (
        if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
            echo ✅ Chrome: Found
        ) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
            echo ✅ Chrome: Found
        ) else (
            echo ⚠️  Chrome/Chromium: Not found in PATH (chromecp needs it)
        )
    )
)

echo ℹ️  Playwright Extension: Install from https://playwright.dev/docs/browsers#playwright-extension
echo    Required for Chrome MCP (chromecp) to connect to open tabs

echo.
echo 🎭 Playwright MCP: Ready (no keys needed)
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if defined MISSING (
    echo ❌ Missing required keys - fix .env then re-run
    exit /b 1
) else (
    echo ✅ All required keys present - MCP servers should connect
    exit /b 0
)