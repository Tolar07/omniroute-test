# Framework Reconciliation — "combine into one, don't retire"

_Last updated: 2026-09-30 · Author: Claude Code session_

## The key correction

There are **not two separate frameworks**. `Tolar07/framework` (the GitHub
repo that runs the daily automation) and the "laptop canonical" framework are
**one codebase lineage that diverged**. Evidence: both carry the same engine —
`engine/dixon_coles.py`, `engine/elo.py`, `engine/mes.py`,
`engine/cross_league.py`, `data/thesportsdb_fixtures.py`, `clv/`, `engine/slate.py`.
The Aug‑22 canonical artifact (`telegram_2026-08-22.txt`) is produced by this
repo's own `output/produce_bet.py::render_telegram_board` (header
`OLP XDV — DAILY BOARD`). So the GitHub repo *is* the framework, at an older
point on the same line.

## What actually diverged

The divergence is almost entirely in the **presentation / output layer**, not
the model:

| Layer | GitHub `Tolar07/framework` (reachable) | Laptop canonical (not reachable) |
|-------|----------------------------------------|----------------------------------|
| Model engine (DC + Elo + MES + cross-league) | ✅ present, converged this session | same lineage |
| Odds (SportyBet free + football-data + odds-api) | ✅ wired this session (PRs #5–#8) | same idea |
| CLV grading / cache staleness | ✅ fixed this session (PR #3) | same |
| Softness tiering | ✅ **removed** this session (PR #12) | already removed on laptop |
| Production-only Telegram delivery | ✅ gate added (PR #7), delivery currently **killed** (PR #11) | — |
| **Telegram output format** | `OLP XDV — DAILY BOARD` (older) **and** `PART 0–5` board | **`##########OLP XDV#########` TABLE 1–4** (newer) |
| **ACCA route + per-row SportyBet booking codes** | ❌ not present | ✅ present (but was itself failing — see below) |

The newest canonical format (`board_2026-09-04.txt`, `telegram_2026-09-08.txt`)
uses:

```
##########OLP XDV#########
TABLE 1 · LAYER 2 — FULL MARKET GRID + AI PICK
TABLE 2 · LAYER 1 — DEPLOY-ELIGIBLE SINGLES
TABLE 3 · ACCA ROUTE
TABLE 4 · THE PICK
```

Note: in those artifacts the booking codes were **already broken** on the
laptop — every code reads `NO DATA — PENDING` with
_"booking-code read postponed — technical issue … once read_betslip_combined_odds is fixed."_
So even the canonical laptop output was not fully working at last capture.

## Why it "feels split into two"

The laptop's presentation-layer evolution (the `#####` TABLE format + ACCA +
booking-code bridge) was **never pushed** to `Tolar07/framework`. GitHub Actions
therefore keeps emitting the older format, while the laptop shows the newer one.
Same engine, two faces.

## What "combine into one" means concretely

Keep `Tolar07/framework` as the single running framework (per your instruction —
**do not retire it**) and bring the laptop's divergent pieces into it:

1. **Output format** — port the `##########OLP XDV#########` TABLE 1–4 layout
   into `output/produce_bet.py`. Fully specified by the artifacts here; can be
   done from this environment. TABLE 1/2/4 map onto existing `BoardFixture`
   data.
2. **ACCA route + booking codes** — needs the laptop's SportyBet booking-code
   bridge (`read_betslip_combined_odds` and the ACCA-grouping logic). This code
   is **not in any repo I can reach**, and was failing at last capture. This is
   the one piece that genuinely requires the laptop code to be pushed.

## The access blocker (honest)

I can reach exactly: `Tolar07/framework`, `Tolar07/omniroute-test`, and (on
request) the private `Tolar07/closing_edge` and
`Tolar07/CLV-log-and-framework-docs.`. The laptop's current working tree is not
on any of them — the `olp_xdv_agent/olp_xdv` submodule points back at
`Tolar07/framework` and is pinned to a **dangling pre‑rewrite commit**. I cannot
read the laptop directly. To merge the laptop's actual code (not a
reconstruction), it has to be pushed somewhere I can reach.
