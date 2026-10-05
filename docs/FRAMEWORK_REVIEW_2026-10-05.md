# OLP XDV framework review — 2026-10-05

Full read-only review of Tolar07/framework `main` (code as of `1b7473c`, two
merges before today's `fa23da2`: #77 draw guard + team profiles + national-team
Elo, #78 codes frozen at 10pm). Covers fixtures and prices, the model, pick
selection, booking, Telegram delivery, GitHub Actions, tests and documents.
Nothing in the framework was changed by this review.

**Bottom line:** the plumbing mostly works; the system has not shown an edge,
and the way it picks makes an edge almost impossible to show.

## 1. What the record shows (3 Oct, the only fully graded day)

| Measure | Value |
|---|---|
| Singles graded / hit rate | 71 / 80.3% |
| Mean price / break-even hit rate | 1.24 / ~81% |
| Singles profit at 1 unit flat | −0.53 u (−0.7%) |
| Picks the system rated +EV | 3 of 76 (mean recorded EV −3.3%) |
| Accas | 4 won, 9 lost, −1.20 u |
| 3-leg 50%+ accas | 0 of 2 |
| Mega slips (25–26 legs) | 0 of 3 |
| BANKER picks (the only tier with a backtest case) | 0 on 3, 4 and 5 Oct |
| Closing price recorded | 1 of 76 on 3 Oct; 11 of 13 on 4 Oct after the pre-kickoff loop fix |

Stated chances (75% SportyBet, 25% model) scored Brier 0.1586 against 0.1574
for the bookmaker's raw price: no better than the price itself.

Expected return of a slip at the system's own per-leg EV (−3.3%):

| Slip | Expected return |
|---|---|
| 4-leg acca | −12.6% |
| 5-leg acca | −15.5% |
| 26-leg mega | −58% |

Sample needed to prove an edge (80% power): ~930 graded singles at a true +4%,
~3,700 at +2%; ~120 picks with a sharp closing price for CLV.

## 2. Backtest evidence

- Studies are walk-forward (no fitting on the predicted matches) — sound.
- Every rule loses 3–7% except BANKER. Production-like BANKER70: 332 picks,
  78.3% hit, +0.67% ROI, standard error ~±2.9 pts — indistinguishable from
  zero. Order 11's "~+4%" comes from a narrower, contaminated holdout (Over 2.5
  dropped after seeing it); the truly held-out half gives t ≈ 0.9.
- Backtests price bet365/market average on top leagues; live play is SportyBet
  NG, 40 of 89 picks FA Cup, and most live markets (O/U 1.5 & 3.5, BTTS,
  handicaps, combos) have no historical prices at all.
- ANCHOR_STUDY: a pure-market weight beats w=0.25 on ROI — the model adds no
  measurable value yet.

## 3. Improvements, in priority order

Items marked **[A]** change a standing order, a stake or the capital gate and
need the Architect's explicit decision. The rest are fixes that keep every
standing order as written.

### 3.1 Make the edge measurable
1. Closing price for every published pick (now ~85% after the 4 Oct loop fix);
   record a margin-free closing probability per pick (de-vig the whole
   SportyBet market at close) and score "closing EV" = price × fair close − 1,
   alongside the raw ratio. Add Pinnacle's close from football-data where it
   exists. (`news_check.py capture_closing`, `engine/picks_ledger.py`)
2. One walk-forward harness that runs the live selection code over history,
   with a locked season, pre-registered measures (closing EV first, ROI
   second), bootstrap intervals and a count of every rule tried.
3. Label unvalidated markets and competitions on the board (no historical
   prices behind them).
4. Store the model chance, the margin-free market chance and the pre-learning
   chance separately on every pick, so the model's added value can be scored.

### 3.2 Pick selection
5. **[A]** The 7-pt agreement rule blocks value: at a 6% margin and price 1.50
   a pick needs the model ~15 pts above the market to be +EV. Either let the
   model disagree (and prove it pays) or say plainly the board is the
   bookmaker's favourites.
6. The few "+EV" picks come from the ladder's approximate scoreline grid
   (independent Poisson fitted to 1X2 + O/U 2.5 only). Fit more lines and
   de-vig exotic markets on their own prices. (`engine/full_markets.py`)
7. One EV formula for both selection routes (the learning shift enters one and
   not the other). (`run_daily.py`)
8. Price drift is counted three times (anchor, LOW demotion, switch); a switched
   pick is reset to SAFE even when it started as BOOK.
9. **[A]** Learning: it learns from already-shifted chances, adds family and
   league shifts on the same picks, and acts on 10 results. Store the
   pre-shift chance; require 50–100 results. (`engine/learning.py`, order 22)

### 3.3 Stakes and capital — all **[A]**
10. Phase 3 is a fixed setting; the CLV gate is 9 of 30 legs, NOT MET, with
    three definitions on record (MAP §12). Choose one and link capital to it.
11. Stakes are suggested on picks with negative EV. Stake nothing where a
    tier's return is ≤ 0 or unproven; record a real bankroll. (`engine/staking.py`)
12. Prove singles first; treat accas and megas as entertainment until singles
    show an edge.

### 3.4 Reliability of the daily loop
13. State saving fails silently: `git pull --rebase || true; git push || echo`
    in `daily.yml` and `commands.yml`. A lost push loses the picks ledger,
    Survivor state and the sent marker, and the next start re-sends the board.
    Retry, fail loudly, save on failure too, one queue for all writers.
14. Telegram: no 429 / retry_after handling; a failed part leaves a hole and
    the whole pipeline re-runs. Resend only missing parts. (`output/notify.py`)
15. Validate the board before sending (band, 50% floor, codes, kickoff, target
    date); supervisor and watchdog should check the run that triggered them and
    the marker on main, not "any success".
16. Sources: season hard-coded "2526" (stale next summer); SportyBet pages not
    retried; picks can be chosen on football-data prices and booked on
    SportyBet; stale caches and missed Flashscore days are not flagged.
17. `run_daily.py --no-send` (and `tests/stress_test.py`, which calls it)
    rewrites the real picks ledger, CLV log and boards. A dry run must work on
    a scratch copy. (This is what wrote the second 5 Oct board kept in
    `docs/local-runs/2026-10-05-stress-test/`.)
18. Keep the run log (Run ID) as an Actions artifact (order 30).

### 3.5 Security
19. Command whitelist fails open if `TELEGRAM_CHAT_ID` is unset; make it refuse.
20. Chat IDs are printed into public Actions logs by the command job.
21. `/log` entries count toward the CLV gate.
22. Rotate the leaked bot token and keys (MAP §10).

### 3.6 Tests and housekeeping
23. No behavioural test of the 800-line daily run; ruff covers 3 files and mypy
    skips the decision and delivery code. Add an offline end-to-end test.
24. bet365 board never graded; results older than Flashscore's 7-day window
    never graded.
25. Model: ratings after 4 matches with no shrinkage; promoted clubs start from
    scratch; international friendlies weighted as competitive games.
26. `.claude/rules/*.md` are TypeScript rules; the protected-file hook guards
    files that no longer exist; docs contradict code in several places.

## 4. Decisions waiting on the Architect
1. Which Phase 3 CLV gate stands, and whether capital depends on it.
2. Stop suggesting stakes on negative-EV picks?
3. Singles first while the edge is tested?
4. May the model disagree with the bookmaker by more than 7 pts (backtest first)?

## 5. Status
- Workspace synced: every recent branch in both repos is on main; no other
  session running (2026-10-05 13:50 UTC).
- Done 2026-10-05: item 17. Dry runs and the stress test now write to scratch
  copies; the real ledger, CLV log, boards and frozen codes are never touched.
  Framework branch `claude/olpxdv-framework-improvements-40hlc8` (`9e2c42f`),
  39/39 test files pass. Not merged into framework main yet (needs a PR).
- Built 2026-10-05 (Architect: "go ahead and build"), framework branch
  `claude/olpxdv-framework-improvements-40hlc8`, every step tested on past
  seasons first and the full test suite green after each:
  - BTTS and Over/Under 1.5 / 2.5 calibrated (`engine/calibration.py`).
  - $ VALUE picks: BTTS-yes / over-goals priced above fair take the pick
    (standing order 36).
  - Champions, Europa and Conference League and Croatia's HNL scanned,
    market-implied; Turkey, Greece, Austria and Switzerland added, model-rated.
  - Season follows the date (switches 1 July).
  - Learning: 50 results over 5 days and a 2-sd gap; no double counting;
    learns from the chance before its own correction (order 22).
  - Sharp check: every main-league pick against the Betfair Exchange's fair
    odds, recorded and shown (`pipeline/sharp.py`).
  - Tested and NOT adopted: rest days / congestion (`backtest/REST_STUDY.md`).
  - Not on framework main until a pull request is merged.
- Item 19 (command whitelist fails closed) was refused by this session's
  permission check and left alone. The rest of 3.1 and 3.4-3.6 is not started.
