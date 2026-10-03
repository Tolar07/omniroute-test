#!/bin/bash
# RETIRED 2026-10-03: the laptop nightly loop is retired. The OLP XDV board
# runs only in GitHub Actions (Tolar07/framework .github/workflows/daily.yml).
# This script used to run run_daily.py and (re)create the 10pm `claude cron`
# job; doing either now would produce a duplicate board. See docs/STATE.md.
echo "OLP XDV laptop scheduler is retired; the daily board runs in GitHub Actions (daily.yml). Nothing to do."
exit 0
