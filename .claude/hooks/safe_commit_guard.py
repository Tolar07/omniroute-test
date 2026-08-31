#!/usr/bin/env python3
"""
PreToolUse hook. Wire to matcher "Bash".

Fixes the exact bug your own memory already names:
"git commit sweeps staged files from other session's changes."

The root cause is `git add -A` (or `git add .`) run by an automated commit
loop -- it stages literally everything dirty in the working tree, including
another session's in-progress edits that were never meant to be committed
yet. Then whichever session's cron-style commit fires next scoops them up
under its own commit message.

This hook does two things:
  1. Blocks `git add -A`, `git add --all`, and bare `git add .` outright.
     The model is told to stage explicit paths instead.
  2. Serializes `git commit` itself with a short-lived mutex, so two
     sessions can't run `git commit` at the literal same instant and race
     on the index/HEAD. This is a real but narrow race; the -A block above
     is the fix that matters more.

This does not stop a human (or an auto-sync script outside Claude Code,
e.g. the vault-memory-sync.js cron) from running `git add -A` directly in
a terminal. If that script is what's actually doing the sweeping, fix it
at the source: change its `git add -A` to add only the specific vault/
memory paths it's meant to sync.
"""
from __
"""