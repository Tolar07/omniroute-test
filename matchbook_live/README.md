# Matchbook live agent — the heartbeat lineage on a betting exchange

**LIVE CAPITAL.** This is the one agent the Architect carved out of the
capital bright line, on 2026-10-14 (amendment quoted in the workspace
`CLAUDE.md`, "Capital bright line — Matchbook agent amendment"). £50 in,
Matchbook (UK), back bets only. It replaces the Polymarket paper engine
(`polymarket_paper/`, commit `955c9819`).

Orders go out only when `MATCHBOOK_LIVE=1`. Without it, or with a `STOP` file
in the state directory, a cycle scans, evaluates and logs what it would send,
and sends nothing.

## What it is

| Piece | File | Rule |
|---|---|---|
| Client | `client.py` | Matchbook REST: login (session reused ~5 h), events, balance, submit/get/cancel offer, settled-bets report. No deposit, withdrawal, transfer or settings endpoint: the tests fail on any endpoint off the allow-list |
| Scanner | `scanner.py` | Soccer (sport 15) "Match Odds", kick-off 2 h–7 d away, read without login; per runner: back–lay spread ≤ 4 pts, implied 0.10–0.88, best-two back depth ≥ £15 |
| Framework feed | `framework_feed.py` | Every single in the framework's daily `picks_<date>.json` (every acca leg is one): SportyBet market → Matchbook (Total, Double Chance, half-line Handicap, Match Odds, BTTS, Draw No Bet; team totals, win-to-nil, multigoals, combos skipped and logged), match found by kick-off ±20 min and both team names, bet 10 min–12 h before kick-off, AI Survivor rules: model chance 80%+ and MEDIUM certainty measured on Matchbook (model 3–7 pts over Matchbook break-even net of commission) → ½-Kelly. Runs before the oracle each cycle |
| Oracle | `oracle.py` | Blue / Red / Judge through an OpenAI-compatible gateway. **Blind**: event, kick-off, market and selection names only, never a price. No gateway → PENDING, nothing trades |
| Delta cache | `run.py` | An answer is reused for 4 h unless the implied price moved 3+ pts |
| Risk gate | `risk_gate.py` | break-even = (1 + 2%) / odds; edge > 8 pts, confidence ≥ 0.70, ½-Kelly (commission-adjusted) capped at 6% of equity, ≤ cash − £1, ≤ 65% exposure, ≤ Matchbook free funds − £1, ≥ £1, one position per event |
| Execution | `executor.py` | Fill-and-kill: back offer at the best back price, unmatched part cancelled at once (a failed cancel is retried next run). Settlement pays recorded cost + Matchbook's own net P&L for the offer |
| Lineage | `lineage.py` | genesis £50; dies under £5; **mitosis** at £100 equity with £50 cash → a child with £50 of the parent's cash (a ledger row in the same account, no new money); max 16 alive; strongest lineage gets the strongest edge, one new position per lineage per run; an order error stops the run's orders |
| Earn your keep | `lineage.py` | population halts when equity net of oracle burn < £5, or after 10+ settled positions the last 48 h of P&L doesn't cover 48 h of burn; reason to `post_mortem.log`; only `--reseed` (the Architect) restarts it |
| Heartbeat | `run.py` | Run ID + timestamp; mode, Matchbook balance/exposure/free funds, lineages, open positions, this run's orders and settlements; `heartbeat_latest.txt` and `heartbeats.log` in the state dir |

## Run

```bash
pip install requests
python -m unittest matchbook_live.tests.test_live   # offline, fake exchange
python -m matchbook_live.run --once                 # one cycle
python -m matchbook_live.run --loop                 # every 600 s ± 45 s
python -m matchbook_live.run --reseed               # Architect only
```

Environment: `MATCHBOOK_USERNAME`, `MATCHBOOK_PASSWORD`, `MATCHBOOK_LIVE=1`,
`OPENAI_BASE_URL`, `OPENAI_MODEL`, optional `OPENAI_API_KEY`,
`ORACLE_GBP_PER_1K_TOKENS` (without it burn reads PENDING and the burn rule
can't fire), `MB_STATE_DIR` (default `matchbook_live/data/`, git-ignored).
Optional: `MB_MARKET_NAMES` (default `Match Odds`), `MB_COMMISSION` (default `0.02`).

Stop at once: create `<state dir>\STOP`. Delete it to resume.

## Deploy — self-hosted runner on the Architect's UK machine

1. **Private repo.** Create one (e.g. `Tolar07/matchbook-agent`, *Private*). Copy
   `matchbook_live/` into it, and `matchbook_live/deploy/matchbook-agent.yml`
   to `.github/workflows/matchbook-agent.yml`. Never attach a self-hosted
   runner to a public repo.
2. **Runner.** Repo → Settings → Actions → Runners → *New self-hosted runner*
   → Windows. Follow GitHub's commands on the UK machine; when `config.cmd`
   asks for labels add `matchbook-uk`; install it as a service so it survives
   reboots. Python 3 must be on the machine (`py -3`).
3. **Secrets** (Settings → Secrets and variables → Actions):
   `MATCHBOOK_USERNAME`, `MATCHBOOK_PASSWORD`, `OPENAI_BASE_URL`,
   `OPENAI_MODEL`, `OPENAI_API_KEY`.
4. **Variables:** `MB_STATE_DIR` = `C:\olp\matchbook_state`,
   `ORACLE_GBP_PER_1K_TOKENS`, and last of all `MATCHBOOK_LIVE` = `1`.
5. **Check:** Actions → matchbook-agent → *Run workflow* (once). The log's
   heartbeat should read `Mode: LIVE`, show the Matchbook balance, and list
   any orders.
6. **Matchbook account:** £50 in, VPN off, API access enabled on the account.
   Commission is charged on matched stake; the gate assumes 2%.

## Not built

- Lay bets, trading out, in-play: the agent backs pre-match and holds to settlement.
- News search in the oracle; the framework's FotMob team news (`engine/team_news.py`)
  is the obvious source.
