# Parked workspace code (2026-10-03)

These files used to sit at the top of this workspace. They were a second,
laptop-only copy of the OLP XDV pipeline (fixture extraction, odds
collection, heartbeat generation, a trigger server, Telegram listeners,
debug and test scripts) plus their saved outputs and status reports from
August–September 2026.

The one live framework is `olp_xdv_agent/olp_xdv` (Tolar07/framework `main`,
run by GitHub Actions). Nothing here is imported or run. Paths mirror where
each file used to live (`legacy/workspace/server/server.py` was
`server/server.py`). To bring an idea back, build it into the framework as a
PR with a test there, not here.

`legacy/workspace/.claude/` holds the workspace's laptop-era
`olp-xdv-specialist` agent (it described the old `elo-persistence` line,
`brain/`, `webapp/` and the laptop monitors) and the old prompt and board
review notes that sat in `.claude/` (parked 2026-10-03). The live agents are
the framework's, in `olp_xdv_agent/olp_xdv/.claude/agents/`.
