<#
.SYNOPSIS
    MCP Server Key Validation & Startup Script for PowerShell
    Run this before starting Claude Code to verify all keys are present
#>

Write-Host "🔍 Validating MCP Server Configuration..." -ForegroundColor Cyan
Write-Host ""

# Load .env if it exists
if (Test-Path .env) {
    Get-Content .env | Where-Object { $_ -notmatch '^#' } | ForEach-Object {
        if ($_ -match '^(.+?)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "✅ Loaded .env file" -ForegroundColor Green
} else {
    Write-Host "⚠️  No .env file found. Copy .env.example to .env and add your keys" -ForegroundColor Yellow
    Write-Host "   Copy-Item .env.example .env" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📋 Checking API Keys:" -ForegroundColor Cyan
Write-Host ""

$missing = $false

# Perplexity
$perplexityKey = [Environment]::GetEnvironmentVariable("PERPLEXITY_API_KEY", "Process")
if ($perplexityKey -and $perplexityKey -ne "your_perplexity_key_here") {
    Write-Host "✅ PERPLEXITY_API_KEY: Set ($($perplexityKey.Substring(0,8))...)" -ForegroundColor Green
} else {
    Write-Host "❌ PERPLEXITY_API_KEY: MISSING — Get key at https://www.perplexity.ai/settings/api" -ForegroundColor Red
    $missing = $true
}

# Firecrawl
$firecrawlKey = [Environment]::GetEnvironmentVariable("FIRECRAWL_API_KEY", "Process")
if ($firecrawlKey -and $firecrawlKey -ne "your_firecrawl_key_here") {
    Write-Host "✅ FIRECRAWL_API_KEY: Set ($($firecrawlKey.Substring(0,8))...)" -ForegroundColor Green
} else {
    Write-Host "⚠️  FIRECRAWL_API_KEY: Not set (optional — keyless mode works with rate limits)" -ForegroundColor Yellow
    Write-Host "   Get key at https://firecrawl.dev for full features" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🌐 Checking Chrome/Playwright Setup:" -ForegroundColor Cyan
Write-Host ""

# Check Chrome
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeFound = $false
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        Write-Host "✅ Chrome: Found at $path" -ForegroundColor Green
        $chromeFound = $true
        break
    }
}

if (-not $chromeFound) {
    Write-Host "⚠️  Chrome/Chromium: Not found in standard locations (chromecp needs it)" -ForegroundColor Yellow
}

Write-Host "ℹ️  Playwright Extension: Install from https://playwright.dev/docs/browsers#playwright-extension" -ForegroundColor Gray
Write-Host "   Required for Chrome MCP (chromecp) to connect to open tabs" -ForegroundColor Gray

Write-Host ""
Write-Host "🎭 Playwright MCP: Ready (no keys needed)" -ForegroundColor Green
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ($missing) {
    Write-Host "❌ Missing required keys — fix .env then re-run" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ All required keys present — MCP servers should connect" -ForegroundColor Green
    exit 0
}