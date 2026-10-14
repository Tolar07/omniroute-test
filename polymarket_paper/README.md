# Polymarket paper engine — the heartbeat lineage on prediction markets

**PAPER ONLY.** It reads Polymarket's public APIs (no account, no key) and
simulates fills against the live order book. It holds no private key, signs
nothing, sends nothing on-chain and posts no order. That is the framework's
capital bright line ("no code routes a real stake"; it does not yield to
directives), and `tests/test_paper.py::PaperOnly` fails if a signing or
order library or an order endpoint is ever added.

## What it is

The framework's AI Survivor (standing order 23, `engine/survivor.py`, the
"heartbeat lineage") carried onto Polymarket, using the money rules of the
"$50 agent / earn your keep" spec:

| Piece | File | Rule |
|---|---|---|
| Scanner | `scanner.py` | Gamma markets ending in 2 h–14 d (100 a page, 0.25 s apart), binary YES/NO, CLOB book both sides: spread ≤ 0.04, ask 0.10–0.88, top-2 ask depth ≥ $15 |
| Oracle | `oracle.py` | Blue (YES) / Red (NO) / Judge via an OpenAI-compatible gateway (OmniRoute). **Blind**: only question, rules, event title and end date go in, never a price. No gateway → PENDING, nothing trades |
| Delta cache | `run.py` | An answer is reused for 4 h unless the YES ask moved 3+ pts |
| Risk gate | `risk_gate.py` | edge > 8 pts, confidence ≥ 0.70, ½-Kelly capped at 6% of equity, ≤ cash − $1, ≤ 65% exposure, ≥ $1, one position per event, limit = ask + 1 tick |
| Paper fill | `paper_exec.py` | FAK: walks the live asks up to the limit; sells at bids ≥ 0.985; a resolved market pays $1 a winning share (50/50 pays $0.50) |
| Lineage | `lineage.py` | genesis $66 (~£50); dies under $6.50; **mitosis** at 2× genesis with $66 cash → a child with $66 (a ledger row, not a wallet); max 16 alive; strongest lineage gets the strongest edge, one new position per lineage per run |
| Earn your keep | `lineage.py` | population halts when equity net of oracle burn < $6.50, or after 10+ settled positions the last 48 h of PnL doesn't cover 48 h of burn; reason to `post_mortem.log`; only `--reseed` (the Architect) restarts it |
| Heartbeat | `run.py` | Run ID + timestamp; lineages, equity, mitosis progress, open positions at live bid (PENDING when no bid), this run's events |

## Run

```bash
pip install requests
python -m polymarket_paper.run --once                  # one cycle
python -m polymarket_paper.run --loop                  # every 600 s ± 45 s
python -m unittest polymarket_paper.tests.test_paper   # offline tests
```

Oracle: `OPENAI_BASE_URL` (e.g. your OmniRoute `http://localhost:<port>/v1`),
`OPENAI_MODEL`, optional `OPENAI_API_KEY`, and `ORACLE_USD_PER_1K_TOKENS`
(without it burn reads PENDING and the burn rule can't fire). State goes to
`polymarket_paper/data/` (git-ignored) or `PM_PAPER_STATE_DIR`.

## Not built (on purpose or not yet)

- Live orders, wallets, approvals, on-chain transfers, redemption: the bright line.
- Proxy routing to dodge Polymarket's country block: against Polymarket's terms. Check
  your own connection at `https://polymarket.com/api/geoblock`.
- News search in the oracle and the football/NBA team-news check: not wired yet; the
  framework's FotMob team news (`engine/team_news.py`) is the obvious source.
