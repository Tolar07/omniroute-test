#!/bin/bash
# MCP Server Key Validation & Startup Script
# Run this before starting Claude Code to verify all keys are present

set -e

echo "🔍 Validating MCP Server Configuration..."
echo ""

# Load .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Loaded .env file"
else
    echo "⚠️  No .env file found. Copy .env.example to .env and add your keys"
    echo "   cp .env.example .env"
fi

echo ""
echo "📋 Checking API Keys:"
echo ""

# Perplexity
if [ -n "$PERPLEXITY_API_KEY" ] && [ "$PERPLEXITY_API_KEY" != "your_perplexity_key_here" ]; then
    echo "✅ PERPLEXITY_API_KEY: Set (${PERPLEXITY_API_KEY:0:8}...)"
else
    echo "❌ PERPLEXITY_API_KEY: MISSING — Get key at https://www.perplexity.ai/settings/api"
fi

# Firecrawl
if [ -n "$FIRECRAWL_API_KEY" ] && [ "$FIRECRAWL_API_KEY" != "your_firecrawl_key_here" ]; then
    echo "✅ FIRECRAWL_API_KEY: Set (${FIRECRAWL_API_KEY:0:8}...)"
else
    echo "⚠️  FIRECRAWL_API_KEY: Not set (optional — keyless mode works with rate limits)"
    echo "   Get key at https://firecrawl.dev for full features"
fi

echo ""
echo "🌐 Checking Chrome/Playwright Setup:"
echo ""

# Check Chrome
if command -v google-chrome &> /dev/null || command -v chromium &> /dev/null || command -v "C:\Program Files\Google\Chrome\Application\chrome.exe" &> /dev/null; then
    echo "✅ Chrome/Chromium: Found"
else
    echo "⚠️  Chrome/Chromium: Not found in PATH (chromecp needs it)"
fi

# Check Playwright Extension (can only verify by user confirmation)
echo "ℹ️  Playwright Extension: Install from https://playwright.dev/docs/browsers#playwright-extension"
echo "   Required for Chrome MCP (chromecp) to connect to open tabs"

echo ""
echo "🎭 Playwright MCP: Ready (no keys needed)"
echo ""

# Summary
MISSING=0
if [ -z "$PERPLEXITY_API_KEY" ] || [ "$PERPLEXITY_API_KEY" = "your_perplexity_key_here" ]; then
    MISSING=1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $MISSING -eq 0 ]; then
    echo "✅ All required keys present — MCP servers should connect"
    exit 0
else
    echo "❌ Missing required keys — fix .env then re-run"
    exit 1
fi