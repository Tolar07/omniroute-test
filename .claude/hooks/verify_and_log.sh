#!/usr/bin/env bash
# Usage: bash .claude/hooks/verify_and_log.sh "<command to run>"
#
# Runs the command for real and appends timestamp|command|exit_code to
# .claude/state/verify.log based on ACTUAL execution. Use this instead
# of running a verification command raw when you intend to cite it as a
# [CLAIM: COMMAND_VERIFIED ...] in Handoff.md -- an unlogged command has
# no way to satisfy that claim type at Stop time.
set -o pipefail
CMD="$1"
mkdir -p .claude/state
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
OUT=$(eval "$CMD" 2>&1)
CODE=$?
printf '%s|%s|%s\n' "$TS" "$CMD" "$CODE" >> .claude/state/verify.log
echo "$OUT"
exit $CODE