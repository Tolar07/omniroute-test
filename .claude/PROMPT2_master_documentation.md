# Prompt for Claude Code — Full Master Documentation

Paste this to Claude Code as-is.

---

I need everything about the current state of this framework explained to me in one master document, downloadable, so I understand what's actually built rather than what I think is built. Cover:

1. **Every rule as currently coded** — every HR, every ID, status (active/superseded/shelved/proposed), version introduced, where it lives in the repo. Where the docs and the actual code disagree, tell me — don't pick one silently.
2. **Full architecture** — the engine, the SCAN → trigger production → publish pipeline, how softness/deploy-eligibility worked before I cancelled it and what changed in code when I did, calibration/CLV logging, the admin dashboard, the Telegram/client-facing board.
3. **Every agent in the system** — Claude, Gemini, DeepSeek, Claude Code, any bot or script that runs autonomously — what each one is authorized to do, what each is explicitly barred from doing.
4. **Repo structure** — every major file/module and what it does, in plain language.
5. **Where things stand right now** — legs logged, CLV gate progress, mean CLV, what's scanned vs eligible vs blocked today, any unresolved findings from recent reviews (including the ID405 scope question and calibration-league-scope question raised after the softness cancellation).

Output as a single downloadable markdown file. I want this to double as the reference doc I hand to anyone — human or AI — who needs to get up to speed on this system without me re-explaining it from scratch every time.
