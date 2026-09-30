# Morning brief — 2026-09-30 overnight

_You said "you're in charge, I'm sleeping." Here's what I did, and the one
30-second thing I need from you to finish the combine._

## Bottom line

The framework is **not actually two frameworks** — it's **one codebase that
diverged**. GitHub (`Tolar07/framework`) runs the automation and is up to date
on the engine; your laptop is ahead only on the **output layer** (the
`##########OLP XDV#########` TABLE board + ACCA route + SportyBet booking codes).
That newer output code was never pushed, which is why it "feels split."

**Nothing is being retired. All automation stays running.** Telegram delivery is
switched OFF for now on purpose, so no wrong-format board can reach you while
we finish.

## What I did overnight (no laptop needed)

- Confirmed GitHub `main` is healthy and carries all this session's fixes
  (softness removed, free SportyBet odds, CLV fix, form context, production-only
  delivery). The engine side is already unified.
- Searched every repo I can reach for your canonical `#####` generator:
  - `closing_edge` → separate CLV tool, not it.
  - `clv-log-and-framework-docs.` → **empty**.
  - `omniroute-test` → only the board *outputs*, not the generator.
- Diagnosed last night's push: it said **"Everything up-to-date"**, which means
  you pushed from a folder that's already identical to GitHub — **not** the
  canonical one. The canonical output code is in a different laptop folder.
- Wrote the file-by-file merge plan (below) so the merge is fast and low-risk
  once the right folder lands.
- I did **not** invent the board format. I only have empty-day `#####` samples,
  and guessing the populated layout is exactly how a wrong board would reach you.
  So I'm waiting for your real code instead.

## The 30 seconds I need from you

Find the folder that actually produces the `#####` board, then push it. In
**PowerShell**:

```powershell
# 1) Locate the generator (the .py file, not the .txt outputs)
cd "C:\Users\Motunrayo\omniroute test"
Select-String -Path .\* -Pattern "##########OLP XDV" -List -Recurse | Select-Object Path
```

Look at the results for a **`.py`** file (my bet: under `olp_xdv_agent\olp_xdv\`).
Then, from **that .py file's folder**:

```powershell
cd <the folder that .py is in>
git rev-parse --show-toplevel      # confirms which repo it belongs to
git check-ignore .env              # MUST print ".env" (so creds don't get pushed)
git remote -v
git checkout -b laptop-canonical
git add -A
git commit -m "snapshot: canonical output layer for merge"
git push -u origin laptop-canonical
```

- If `git check-ignore .env` prints **nothing**, STOP and tell me — I'll give you
  a one-liner so your bot token / API keys don't get pushed.
- If it's the `olp_xdv_agent\olp_xdv` submodule, its remote is
  `Tolar07/framework` and the push will land there — perfect, I can reach it.
- Then just say **"pushed"** and I take over the merge.

## What I do the moment it lands

1. Fetch `laptop-canonical`, diff it against `main`.
2. Bring **only the diverged pieces** into `Tolar07/framework` on a merge branch:
   the `#####` output renderer, the ACCA-route builder, and the SportyBet
   booking-code bridge.
3. Keep everything already converged on `main` (engine, odds, CLV, softness
   removal, form).
4. Generate a sample board and check it against your saved artifacts before
   anything goes live.
5. Show you the unified board. **Only after you approve** do I flip Telegram
   delivery back on — one framework, correct format, automation intact.

## Merge plan (file-level, for reference)

| Concern | Take from | Notes |
|---------|-----------|-------|
| Board/Telegram format (`#####` TABLE 1–4) | laptop `output/…` | replaces `render_telegram_board` in `output/produce_bet.py` |
| ACCA route builder | laptop | new module; wire into `run_daily.py` |
| SportyBet booking-code bridge (`read_betslip_combined_odds`) | laptop | the one piece with no reachable equivalent; was itself failing at last capture — I'll confirm it works before relying on it |
| Model engine (DC + Elo + MES + cross-league) | `main` (keep) | already converged |
| Odds (SportyBet free + fallbacks) | `main` (keep) | #8 |
| CLV grading / cache | `main` (keep) | #3 |
| Softness removal | `main` (keep) | #12 |
| Telegram delivery gate | `main` (keep, stays OFF) | re-enable only after your sign-off |

_No changes were made to `main` or to any running automation overnight._
