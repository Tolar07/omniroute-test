"""
One cycle of the Matchbook LIVE heartbeat lineage.

  1. sweep     retry any cancel that failed last run
  2. settle    Matchbook's settled-bets report pays the lineages that held them
  3. life      deaths, mitosis, earn-your-keep halt
  4. scan      football events + prices, filtered (no login needed)
  5. oracle    blind Blue/Red/Judge (4 h / 3-pt delta cache); PENDING without a gateway
  6. allocate  deterministic gate, fill-and-kill back offer at the best back price
  7. heartbeat Run ID + timestamp on every line that carries a price (HR59)

Orders go out only when MATCHBOOK_LIVE=1 and <state dir>/STOP does not exist.
Otherwise step 6 logs what it would send and sends nothing.

    python -m matchbook_live.run --once
    python -m matchbook_live.run --loop          # every 600 s +/- 45 s jitter
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

from matchbook_live import config as C
from matchbook_live import executor, framework_feed
from matchbook_live import lineage as L
from matchbook_live import board, multiples, notify, oracle, paper, scanner, scorecard
from matchbook_live.client import Client


def run_id(now: datetime) -> str:
    return f"MBLIVE-{now:%Y%m%d-%H%M}-{secrets.token_hex(3)}"


def live_enabled(state_dir: Path) -> tuple[bool, str]:
    if (state_dir / C.STOP_FILE).exists():
        return False, f"STOPPED — {state_dir / C.STOP_FILE} exists"
    if not C.LIVE:
        return False, "DRY — MATCHBOOK_LIVE is not 1, no order sent"
    if not (C.USERNAME and C.PASSWORD):
        return False, "DRY — Matchbook login not set, no order sent"
    return True, "LIVE — real GBP on Matchbook"


# ---------------------------------------------------------------- delta cache
def _cache_load(d: Path) -> dict:
    f = d / "eval_cache.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _cache_save(d: Path, cache: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "eval_cache.json").write_text(json.dumps(cache, indent=1), encoding="utf-8")


def _key(c: dict) -> str:
    return f"{c['market_id']}:{c['runner_id']}"


def cached(cache: dict, c: dict, now: datetime) -> dict | None:
    e = cache.get(_key(c))
    if not e:
        return None
    fresh = now - datetime.fromisoformat(e["ts"]) < timedelta(hours=C.CACHE_HOURS)
    still = abs(c["book"]["implied"] - e["implied"]) < C.CACHE_MIN_MOVE
    return e if fresh and still else None


# ---------------------------------------------------------------- sweep
def sweep(client, pop: dict, hist: list[dict]) -> list[str]:
    out = []
    for h in L.open_positions(hist):
        if not h.get("cancel_pending"):
            continue
        try:
            client.cancel(h["offer_id"])
            h["cancel_pending"] = False
            matched, _ = executor._matched(client.offer(h["offer_id"]))
        except Exception as e:
            out.append(f"SWEEP: cancel of offer {h['offer_id']} still failing ({type(e).__name__})")
            continue
        extra = round(matched - h["cost_gbp"], 2)
        if extra > 0:                                  # matched more after we looked: debit it
            ln = L._ln(pop, h["lineage_id"])
            if ln:
                ln["cash_gbp"] = round(ln["cash_gbp"] - extra, 2)
            h["cost_gbp"] = matched
        if h["cost_gbp"] <= 0:
            L.void(pop, h)
            out.append(f"SWEEP: offer {h['offer_id']} cancelled unmatched -> VOID")
        else:
            out.append(f"SWEEP: offer {h['offer_id']} cancelled, £{h['cost_gbp']:.2f} matched")
    return out


# ---------------------------------------------------------------- loss stop
def loss_stop(pop: dict, balance: dict | None) -> list[str]:
    """Halt new positions once Matchbook's balance (cash + money in open bets, at
    cost) is under C.LOSS_STOP_GBP. Settling continues; only --reseed lifts it.
    Guards the Architect's £50 loan only: once repaid, the £50 he withdraws would
    otherwise trip it."""
    if pop.get("halted") or not balance or C.LOSS_STOP_GBP <= 0 or pop.get("loan_gbp", 0) <= 0:
        return []
    bal = float(balance.get("balance") or 0)
    if bal >= C.LOSS_STOP_GBP:
        return []
    pop["halted"] = (f"LOSS STOP: Matchbook balance £{bal:.2f} under £{C.LOSS_STOP_GBP:.2f} — "
                     "no new bets; the Architect decides (--reseed resumes)")
    return [f"HALTED — {pop['halted']}"]


# ---------------------------------------------------------------- heartbeat
def heartbeat(rid: str, now: datetime, mode: str, pop: dict, hist: list[dict], events: list[str],
              stats: dict, oracle_note: str, balance: dict | None, picks: list[str] | None = None) -> str:
    alive = L.living(pop)
    burn, known = L.burn_total(pop)
    total = 0.0
    rows = []
    for ln in sorted(alive, key=lambda x: (-x["generation"], x["lineage_id"])):
        eq = L.equity(ln, hist)
        total += eq
        target = C.GENESIS_BANKROLL_GBP * C.MITOSIS_MULTIPLE
        rows.append(f"  {ln['lineage_id']}  g{ln['generation']}  cash £{ln['cash_gbp']:.2f}  "
                    f"deployed £{L.deployed(hist, ln['lineage_id']):.2f}  equity £{eq:.2f}  "
                    f"mitosis {min(100, eq / target * 100):.0f}%  W-L {ln['wins']}-{ln['losses']}")
    gens = max((ln["generation"] for ln in pop["lineages"]), default=0)
    bal = ("PENDING" if not balance else
           f"balance £{float(balance.get('balance') or 0):.2f} · exposure £{float(balance.get('exposure') or 0):.2f}"
           f" · free £{float(balance.get('free-funds') or 0):.2f}")
    lines = [
        "########## OLP XDV · MATCHBOOK HEARTBEAT ##########",
        f"Run ID {rid} · {now.isoformat(timespec='seconds')}",
        f"Mode: {mode}",
        f"Matchbook account: {bal}",
        f"Population: {len(alive)} alive / {len(pop['lineages'])} ever · deepest generation {gens}",
        f"Agent equity £{total:.2f} (capital in £{pop.get('capital_in_gbp', C.GENESIS_BANKROLL_GBP):.2f}) · "
        "oracle burn " + (f"£{burn:.4f}" if known else f"£{burn:.4f} + PENDING (set ORACLE_GBP_PER_1K_TOKENS)"),
        f"Status: {'HALTED — ' + pop['halted'] if pop.get('halted') else 'ALIVE'}",
        ("Loan: £{:.2f} from the Architect outstanding — repaid at £{:.0f} agent equity{}".format(
            pop["loan_gbp"], C.REPAY_AT_EQUITY_GBP, " · REPAYABLE NOW, withdraw it" if pop.get("repay_ready") else "")
         if pop.get("loan_gbp", 0) > 0 else f"Loan: repaid {pop.get('repaid_at', '')[:10]} — trading its own money"),
        "",
        "LINEAGES",
        *(rows or ["  none alive"]),
        "",
        "SCORECARD (source / market: CLV = price taken vs Matchbook closing price)",
        *scorecard.render(hist, pop),
        "",
        "OPEN POSITIONS (at cost)",
    ]
    opens = L.open_positions(hist)
    for h in opens:
        lines.append(f"  BACK {h['runner_name']} £{h['cost_gbp']:.2f} @ {h['avg_odds']:.2f} · "
                     f"{h['event_name'][:50]} · KO {h['start'][:16]} · offer {h['offer_id']} "
                     f"[{h['lineage_id']}, {h['run_id']}]")
    if not opens:
        lines.append("  none")
    lines += ["", "THIS RUN", *(f"  {e}" for e in events or ["no settlements, orders, births or deaths"]),
              "", f"SCAN  events {stats.get('events_read', 'PENDING')} · page errors "
              f"{stats.get('page_errors', 0)} · candidates {stats.get('candidates', 'PENDING')}",
              f"FRAMEWORK {stats.get('framework', 'PENDING')}",
              *(f"  skipped: {x}" for x in (stats.get("framework_skipped") or [])[:12]),
              f"ORACLE {oracle_note}", *stats.get("board", [])]
    if stats.get("paper"):
        lines += ["", *stats["paper"]]
    if picks:
        lines += ["", "PICKS PRICED THIS RUN (estimate vs Matchbook)", *(f"  {x}" for x in picks)]
    return "\n".join(lines)


# ---------------------------------------------------------------- one cycle
def cycle(state_dir: Path = C.STATE_DIR, max_events: int = C.MAX_EVENTS, use_oracle: bool = True,
          max_oracle_calls: int = 20, client=None) -> str:
    now = datetime.now(timezone.utc)
    rid = run_id(now)
    print(f"Run ID {rid}", flush=True)
    pop, hist = L.load(state_dir)
    was_halted = pop.get("halted")
    events: list[str] = []
    live, mode = live_enabled(state_dir)
    has_account = client is not None or bool(C.USERNAME and C.PASSWORD)   # tests inject a client
    client = client or Client(state_dir)

    balance = None
    if has_account:
        try:
            events += sweep(client, pop, hist)
            events += L.settle(pop, hist, lambda ids: executor.settled_by_offer(client, ids), now)
            balance = client.balance()
        except Exception as e:
            events.append(f"ACCOUNT PENDING: {type(e).__name__}: {str(e)[:160]}")
            live, mode = False, f"DRY — account unreachable this run ({type(e).__name__}), no order sent"
    elif L.open_positions(hist):
        events.append("settle: Matchbook login not set — open positions stay OPEN (PENDING)")
    events += L.life_cycle(pop, hist, now)
    events += scorecard.update_pauses(pop, hist, now)
    events += loss_stop(pop, balance)

    stats: dict = {}
    picks: list[str] = []
    oracle_note = "not run (population halted)"
    if not pop.get("halted"):
        try:
            cands, stats, mb_events = scanner.scan(client, now, max_events)
        except Exception as e:
            cands, stats, mb_events = [], {}, []
            events.append(f"SCAN FAILED: {type(e).__name__}: {e} — NO DATA — PENDING")

        if live:
            def place(runner_id, odds, stake):
                return executor.back_fak(client, runner_id, odds, stake)
            free_funds = float(balance.get("free-funds") or 0) if balance else 0.0
        else:
            def place(runner_id, odds, stake):
                return None, mode
            free_funds = None

        # 1. the framework's own picks first: no oracle needed, prices fresh from this scan
        files, fw_notes = framework_feed.fetch_picks(framework_feed.picks_dates(now))
        held = {h.get("fw_key") for h in hist if h.get("fw_key")}
        stats["closing"] = scorecard.record_closing(hist, mb_events, now)
        fw_opps, fw_skipped = framework_feed.candidates(files, mb_events, now, held)
        fw_opps = [c for c in fw_opps if scorecard.allowed(pop, c)]
        stats["framework"] = (f"{len(files)} picks file(s) · {len(framework_feed.legs(files))} legs · "
                              f"{len(fw_opps)} on Matchbook in the betting window · "
                              f"{len(fw_skipped)} skipped" + (f" · {'; '.join(fw_notes)}" if fw_notes else ""))
        for c in fw_opps:
            o = c["oracle"]["true_prob"]
            be = (1 + C.COMMISSION) / c["book"]["best_back"]
            picks.append(f"FRAMEWORK {c['fw_pick']} — {c['event_name'][:45]} (KO {c['start'][5:16]}): "
                         f"model {o:.0%} vs Matchbook {c['book']['best_back']:.2f} (break-even {be:.0%}, "
                         f"edge {o - be:+.1%})")
        stats["framework_skipped"] = fw_skipped
        opened, notes = L.allocate(pop, hist, fw_opps, rid, place, free_funds, now)
        events += notes
        if free_funds is not None:
            free_funds -= sum(r["cost_gbp"] for r in opened)

        # the day's accumulators (£10 budget, bet365's accas moved to Matchbook) — live only
        if live:
            try:
                acca_events, acca_spent = multiples.auto(client, files, mb_events, state_dir, now, free_funds)
                events += acca_events
                if free_funds is not None:
                    free_funds -= acca_spent
            except Exception as e:
                events.append(f"acca: PENDING ({type(e).__name__}: {str(e)[:120]})")

        # the Matchbook board, once per picks date (replaces the bet365 board, framework order 29)
        for f in board.due(pop, files):
            try:
                sent = notify.send_long(board.render(f, mb_events, now))
            except Exception as e:
                sent = f"failed: {type(e).__name__}"
            if sent in ("Telegram sent", "Telegram not configured"):
                board.mark_sent(pop, f["date"])
            stats.setdefault("board", []).append(f"MATCHBOOK BOARD {f['date']}: {sent}")

        # paper study: no orders, and a failure never stops the live cycle
        try:
            stats["paper"], paper_events = paper.cycle(state_dir, files, mb_events, now)
            events += paper_events
        except Exception as e:
            stats["paper"] = [f"PAPER STUDY PENDING: {type(e).__name__}: {str(e)[:120]}"]

        # 2. the blind oracle on Match Odds
        cache = _cache_load(state_dir)
        opps, calls, reused = [], 0, 0
        if not use_oracle:
            oracle_note = "OFF — framework-only (--no-oracle); only framework picks trade"
        elif not oracle.available():
            oracle_note = ("PENDING — no gateway (set OPENAI_BASE_URL + OPENAI_MODEL); "
                           f"{len(cands)} candidates not evaluated, nothing traded")
        else:
            failed = 0
            started = time.monotonic()
            for c in cands:
                e = cached(cache, c, now)
                if e:
                    reused += 1
                elif calls < max_oracle_calls and time.monotonic() - started < C.ORACLE_BUDGET_S:
                    calls += 1
                    r = oracle.evaluate(c)
                    if r is None:
                        failed += 1
                        continue
                    L.record_burn(pop, r.cost_gbp, r.tokens, now)
                    e = {"ts": now.isoformat(timespec="seconds"), "implied": c["book"]["implied"],
                         "true_prob": r.true_prob, "confidence": r.confidence,
                         "reasoning": r.reasoning, "run_id": rid}
                    cache[_key(c)] = e
                    picks.append(f"{c['runner_name']} — {c['event_name'][:45]} (KO {c['start'][5:16]}): "
                                 f"oracle {r.true_prob:.0%} (conf {r.confidence:.2f}) vs market "
                                 f"{c['book']['implied']:.0%} @ {c['book']['best_back']:.2f}")
                else:
                    continue
                c["oracle"] = e
                opps.append(c)
            _cache_save(state_dir, cache)
            oracle_note = (f"{calls} evaluated ({failed} failed → PENDING), {reused} from cache, "
                           f"{len(cands) - calls - reused} left for the next run"
                           + (f" · last failure: {oracle.last_error}" if failed else ""))

        opps = [c for c in opps if scorecard.allowed(pop, c)]
        opened2, notes = L.allocate(pop, hist, opps, rid, place, free_funds, now)
        events += notes
        for rec in opened + opened2:
            who = (f"framework {rec['fw_pick']} (model {rec['oracle_p']:.0%})" if rec.get("source") == "framework"
                   else f"oracle {rec['oracle_p']:.2f}/{rec['confidence']:.2f}")
            events.append(f"OPEN BACK {rec['runner_name']} ({rec['market_name']}) £{rec['cost_gbp']:.2f} "
                          f"@ {rec['avg_odds']:.2f} (edge {rec['edge']:+.1%}, {who}) "
                          f"{rec['event_name'][:50]} → {rec['lineage_id']}")

    reason = notify.due(pop, now, mode, events)
    L.save(pop, hist, state_dir)
    if pop.get("halted") and not was_halted:
        with open(state_dir / "post_mortem.log", "a", encoding="utf-8") as f:
            f.write(f"{rid} {pop['halted']}\n" + "\n".join(events) + "\n\n")
    text = heartbeat(rid, now, mode, pop, hist, events, stats, oracle_note, balance, picks)
    if reason:
        print(notify.send(f"[{reason}]\n{text}"), flush=True)
    # the graded ledger + scorecard, published for the framework to learn from
    (state_dir / "ledger.jsonl").write_text("".join(json.dumps({**h, "clv": scorecard.clv(h)}, ensure_ascii=False)
                                                   + "\n" for h in hist), encoding="utf-8")
    (state_dir / "scorecard.json").write_text(json.dumps({
                                                          "buckets": scorecard.card(hist),
                                                          "paused": pop.get("paused_buckets", {})}, indent=1),
                                              encoding="utf-8")
    (state_dir / "heartbeat_latest.txt").write_text(text + "\n", encoding="utf-8")
    with open(state_dir / "heartbeats.log", "a", encoding="utf-8") as f:
        f.write(text + "\n\n")
    return text


def reseed(state_dir: Path) -> None:
    """Architect only: lift a halt; if every lineage is dead, seed one new
    genesis lineage (another £50 of capital in, recorded)."""
    pop, hist = L.load(state_dir)
    pop["halted"] = None
    if not L.living(pop):
        pop["lineages"].append(L.new_lineage())
        pop["capital_in_gbp"] = round(pop.get("capital_in_gbp", C.GENESIS_BANKROLL_GBP)
                                      + C.GENESIS_BANKROLL_GBP, 2)
    L.save(pop, hist, state_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--state-dir", type=Path, default=C.STATE_DIR)
    ap.add_argument("--max-events", type=int, default=C.MAX_EVENTS)
    ap.add_argument("--max-oracle-calls", type=int, default=20)
    ap.add_argument("--no-oracle", action="store_true")
    ap.add_argument("--reseed", action="store_true", help="Architect only: lift a halt / reseed one lineage")
    ap.add_argument("--check", action="store_true", help="log in and print the balance; no scan, no order")
    ap.add_argument("--repaid", action="store_true",
                    help="Architect only: you withdrew the £50 loan on Matchbook — take it off the books")
    ap.add_argument("--acca", type=float, metavar="STAKE",
                    help="place the framework's strongest Matchbook-eligible accumulator(s) at this stake")
    ap.add_argument("--acca-count", type=int, default=0, metavar="N",
                    help="with --acca: N accas, no match in two, inside the £10 daily acca budget")
    a = ap.parse_args(argv)
    if a.acca is not None:
        now = datetime.now(timezone.utc)
        live, mode = live_enabled(a.state_dir)
        cl = Client(a.state_dir)
        evs, _ = scanner.fetch_events(cl, a.max_events)
        files, _ = framework_feed.fetch_picks(framework_feed.picks_dates(now))
        if a.acca_count:
            msg = multiples.batch(cl, files, evs, a.acca, a.acca_count, a.state_dir, now, live)
        else:
            msg = multiples.place(cl, multiples.strongest(files, evs, now), a.acca, a.state_dir, now, live)
        msg = f"{msg}\n  mode: {mode}"
        print(msg, flush=True)
        print(notify.send(msg), flush=True)
        return 0
    if a.check:
        print(f"Credentials as received: {C.CREDENTIALS_NOTE}", flush=True)
        cl = Client(a.state_dir)
        cl.login(force=True)
        b = cl.balance()
        print(f"LOGIN OK · balance £{float(b.get('balance') or 0):.2f} · exposure £{float(b.get('exposure') or 0):.2f}"
              f" · free £{float(b.get('free-funds') or 0):.2f} · live switch {'ON' if C.LIVE else 'OFF'}")
        return 0
    if a.repaid:
        pop, hist = L.load(a.state_dir)
        msg = L.repaid(pop, hist)
        L.save(pop, hist, a.state_dir)
        print(msg)
        print(notify.send(msg))
        return 0
    if a.reseed:
        reseed(a.state_dir)
        print("reseeded")
        return 0
    if not (a.once or a.loop):
        ap.error("pass --once or --loop")
    while True:
        print(cycle(a.state_dir, a.max_events, not a.no_oracle, a.max_oracle_calls), flush=True)
        if a.once:
            return 0
        time.sleep(max(60.0, 600 + random.uniform(-45, 45)))


if __name__ == "__main__":
    sys.exit(main())
