"""
One cycle of the Polymarket PAPER heartbeat lineage.

  1. settle    resolved markets pay the lineages that held them
  2. books     live book for every open position (marks + take-profit)
  3. exit      sell at 0.985+ bids
  4. life      deaths, mitosis, earn-your-keep halt
  5. scan      Gamma + CLOB, filtered
  6. oracle    blind Blue/Red/Judge (4 h / 3-pt delta cache); PENDING without a gateway
  7. allocate  deterministic gate, paper FAK fill against the live asks
  8. heartbeat Run ID + timestamp on every line that carries a price (HR59)

    python -m polymarket_paper.run --once
    python -m polymarket_paper.run --loop          # every 600 s +/- 45 s jitter
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket_paper import config as C
from polymarket_paper import lineage as L
from polymarket_paper import oracle, scanner


def run_id(now: datetime) -> str:
    return f"PMPAPER-{now:%Y%m%d-%H%M}-{secrets.token_hex(3)}"


# ---------------------------------------------------------------- delta cache
def _cache_load(d: Path) -> dict:
    f = d / "eval_cache.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _cache_save(d: Path, cache: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "eval_cache.json").write_text(json.dumps(cache, indent=1), encoding="utf-8")


def cached(cache: dict, c: dict, now: datetime) -> dict | None:
    e = cache.get(c["condition_id"] or c["market_id"])
    if not e:
        return None
    fresh = now - datetime.fromisoformat(e["ts"]) < timedelta(hours=C.CACHE_HOURS)
    still = abs(c["book_yes"]["best_ask"] - e["best_ask_yes"]) < C.CACHE_MIN_MOVE
    return e if fresh and still else None


# ---------------------------------------------------------------- heartbeat
def heartbeat(rid: str, now: datetime, pop: dict, hist: list[dict], marks: dict, events: list[str],
              stats: dict, oracle_note: str) -> str:
    alive = L.living(pop)
    burn, known = L.burn_total(pop)
    total = 0.0
    rows = []
    for ln in sorted(alive, key=lambda x: (-x["generation"], x["lineage_id"])):
        eq, marked = L.equity(ln, hist, marks)
        total += eq
        target = C.GENESIS_BANKROLL_USD * C.MITOSIS_MULTIPLE
        rows.append(f"  {ln['lineage_id']}  g{ln['generation']}  cash ${ln['cash_usd']:.2f}  "
                    f"deployed ${L.deployed(hist, ln['lineage_id']):.2f}  equity ${eq:.2f}"
                    f"{'' if marked else ' (some at cost: no bid)'}  "
                    f"mitosis {min(100, eq / target * 100):.0f}%  W-L {ln['wins']}-{ln['losses']}")
    gens = max((ln["generation"] for ln in pop["lineages"]), default=0)
    lines = [
        "########## OLP XDV · POLYMARKET HEARTBEAT (PAPER) ##########",
        f"Run ID {rid} · {now.isoformat(timespec='seconds')}",
        "Mode: PAPER — no wallet, no key, no order sent. Prices fetched this run.",
        f"Population: {len(alive)} alive / {len(pop['lineages'])} ever · deepest generation {gens}",
        f"Paper equity ${total:.2f} · oracle burn "
        + (f"${burn:.4f}" if known else f"${burn:.4f} + PENDING (set ORACLE_USD_PER_1K_TOKENS)"),
        f"Status: {'HALTED — ' + pop['halted'] if pop.get('halted') else 'ALIVE'}",
        "",
        "LINEAGES",
        *(rows or ["  none alive"]),
        "",
        "OPEN POSITIONS",
    ]
    opens = L.open_positions(hist)
    for h in opens:
        bid = marks.get(h["token_id"])
        lines.append(f"  {h['side']} {h['shares']:.2f} @ {h['avg_price']:.3f} (${h['cost_usd']:.2f}) "
                     f"bid {'PENDING' if bid is None else f'{bid:.3f}'} · ends {h['end_date'][:16]} · "
                     f"{h['question'][:70]} [{h['lineage_id']}, {h['run_id']}]")
    if not opens:
        lines.append("  none")
    lines += ["", "THIS RUN", *(f"  {e}" for e in events or ["no settlements, exits, births or deaths"]),
              "", f"SCAN  markets {stats.get('markets_read', 'PENDING')} · in 2h–14d window "
              f"{stats.get('in_window', 'PENDING')} · books {stats.get('books_read', 0)} "
              f"(errors {stats.get('book_errors', 0)}) · candidates {stats.get('candidates', 'PENDING')}",
              f"ORACLE {oracle_note}"]
    return "\n".join(lines)


# ---------------------------------------------------------------- one cycle
def cycle(state_dir: Path = C.STATE_DIR, max_markets: int = C.MAX_MARKETS, use_oracle: bool = True,
          max_oracle_calls: int = 20) -> str:
    now = datetime.now(timezone.utc)
    rid = run_id(now)
    print(f"Run ID {rid}", flush=True)
    pop, hist = L.load(state_dir)
    was_halted = pop.get("halted")
    events: list[str] = []

    events += L.settle(pop, hist, scanner.fetch_market, now)

    books: dict = {}
    for h in L.open_positions(hist):
        try:
            books[h["token_id"]] = scanner.parse_book(scanner.fetch_book(h["token_id"]))
        except Exception:
            books[h["token_id"]] = None
    events += L.take_profit(pop, hist, books, now)
    marks = {t: (b["best_bid"] if b else None) for t, b in books.items()}
    events += L.life_cycle(pop, hist, marks, now)

    stats: dict = {}
    oracle_note = "not run (population halted)"
    if not pop.get("halted"):
        try:
            cands, stats = scanner.scan(now, max_markets)
        except Exception as e:
            cands, stats = [], {}
            events.append(f"SCAN FAILED: {type(e).__name__}: {e} — NO DATA — PENDING")
        cache = _cache_load(state_dir)
        opps, calls, reused = [], 0, 0
        if not (use_oracle and oracle.available()):
            oracle_note = ("PENDING — no gateway (set OPENAI_BASE_URL + OPENAI_MODEL to your OmniRoute); "
                           f"{len(cands)} candidates not evaluated, nothing traded")
        else:
            failed = 0
            for c in cands:
                e = cached(cache, c, now)
                if e:
                    reused += 1
                elif calls < max_oracle_calls:
                    calls += 1
                    r = oracle.evaluate(c)
                    if r is None:
                        failed += 1
                        continue
                    L.record_burn(pop, r.cost_usd, r.tokens, now)
                    e = {"ts": now.isoformat(timespec="seconds"), "best_ask_yes": c["book_yes"]["best_ask"],
                         "true_prob_yes": r.true_prob_yes, "confidence": r.confidence,
                         "reasoning": r.reasoning, "run_id": rid}
                    cache[c["condition_id"] or c["market_id"]] = e
                else:
                    continue
                c["oracle"] = e
                opps.append(c)
            _cache_save(state_dir, cache)
            oracle_note = (f"{calls} evaluated ({failed} failed → PENDING), {reused} from cache, "
                           f"{len(cands) - calls - reused} left for the next run")
        for rec in L.allocate(pop, hist, opps, marks, rid, now):
            marks[rec["token_id"]] = None
            events.append(f"OPEN {rec['side']} ${rec['cost_usd']:.2f} @ {rec['avg_price']:.3f} "
                          f"(edge {rec['edge']:+.1%}, oracle {rec['oracle_p_yes']:.2f}/{rec['confidence']:.2f}) "
                          f"{rec['question'][:60]} → {rec['lineage_id']}")

    L.save(pop, hist, state_dir)
    if pop.get("halted") and not was_halted:
        with open(state_dir / "post_mortem.log", "a", encoding="utf-8") as f:
            f.write(f"{rid} {pop['halted']}\n" + "\n".join(events) + "\n\n")
    text = heartbeat(rid, now, pop, hist, marks, events, stats, oracle_note)
    (state_dir / "heartbeat_latest.txt").write_text(text + "\n", encoding="utf-8")
    return text


def reseed(state_dir: Path) -> None:
    pop, hist = L.load(state_dir)
    pop["halted"] = None
    if not L.living(pop):
        pop["lineages"].append(L.new_lineage())
    L.save(pop, hist, state_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--state-dir", type=Path, default=C.STATE_DIR)
    ap.add_argument("--max-markets", type=int, default=C.MAX_MARKETS)
    ap.add_argument("--max-oracle-calls", type=int, default=20)
    ap.add_argument("--no-oracle", action="store_true")
    ap.add_argument("--reseed", action="store_true", help="Architect only: lift a halt / reseed one lineage")
    a = ap.parse_args(argv)
    if a.reseed:
        reseed(a.state_dir)
        print("reseeded")
        return 0
    if not (a.once or a.loop):
        ap.error("pass --once or --loop")
    while True:
        print(cycle(a.state_dir, a.max_markets, not a.no_oracle, a.max_oracle_calls), flush=True)
        if a.once:
            return 0
        time.sleep(max(60.0, 600 + random.uniform(-45, 45)))


if __name__ == "__main__":
    sys.exit(main())
