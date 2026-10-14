"""
HEARTBEAT LINEAGE ON POLYMARKET — the AI Survivor (framework standing order 23,
engine/survivor.py) carried onto prediction markets. PAPER ONLY.

What is kept from the football survivor:
  - lineages with an id, a parent and a generation; the dead stay on record
  - at most MAX_LINEAGES alive; strongest lineage gets the strongest pick,
    one new position per lineage per run, one position per event across the
    whole population (the event lock)
  - every position kept in history.jsonl and graded in place; a market that
    has not resolved stays OPEN — never guessed (HR35)

What changes for Polymarket (the "earn your keep" spec):
  - a lineage's lifeforce is paper USD (genesis $66 ~ GBP 50), sized by the
    deterministic Kelly gate, so one loss is not death; a lineage dies when
    its equity falls under the survival floor ($6.50)
  - MITOSIS: equity >= 2x genesis and cash >= genesis -> a child is born with
    genesis cash taken from the parent (the parent lives on). No wallet is
    created: a child is a ledger row, not a keypair.
  - the population halts (no new positions) when total equity net of oracle
    burn falls under the floor, or when, after 10+ settled positions, the
    last 48 h of realised PnL does not cover the last 48 h of burn. The
    reason is written to post_mortem.log. Nothing restarts it but the
    Architect (--reseed).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from polymarket_paper import config as C
from polymarket_paper import paper_exec, risk_gate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def new_lineage(parent: Optional[str] = None, generation: int = 0,
                cash: float = C.GENESIS_BANKROLL_USD, born: Optional[str] = None) -> dict:
    return {"lineage_id": "pm_" + uuid.uuid4().hex[:10], "parent_id": parent,
            "generation": generation, "cash_usd": round(cash, 2), "alive": True,
            "born": born or _iso(_now()), "died": None, "death_reason": None,
            "wins": 0, "losses": 0, "children": 0}


# ---------------------------------------------------------------- persistence
def load(state_dir: Path = C.STATE_DIR) -> tuple[dict, list[dict]]:
    lf, hf = state_dir / "lineage.json", state_dir / "history.jsonl"
    pop = (json.loads(lf.read_text(encoding="utf-8")) if lf.exists() else
           {"lineages": [new_lineage()], "burn": [], "halted": None})
    hist = ([json.loads(x) for x in hf.read_text(encoding="utf-8").splitlines() if x.strip()]
            if hf.exists() else [])
    return pop, hist


def save(pop: dict, hist: list[dict], state_dir: Path = C.STATE_DIR) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_dir / "lineage.json.tmp"
    tmp.write_text(json.dumps(pop, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(state_dir / "lineage.json")
    (state_dir / "history.jsonl").write_text(
        "".join(json.dumps(h, ensure_ascii=False) + "\n" for h in hist), encoding="utf-8")


def living(pop: dict) -> list[dict]:
    return [ln for ln in pop["lineages"] if ln["alive"]]


def open_positions(hist: list[dict], lineage_id: Optional[str] = None) -> list[dict]:
    return [h for h in hist if h["status"] == "OPEN"
            and (lineage_id is None or h["lineage_id"] == lineage_id)]


def _ln(pop: dict, lineage_id: str) -> Optional[dict]:
    return next((x for x in pop["lineages"] if x["lineage_id"] == lineage_id), None)


# ---------------------------------------------------------------- valuation
def deployed(hist: list[dict], lineage_id: str) -> float:
    return round(sum(h["cost_usd"] for h in open_positions(hist, lineage_id)), 2)


def equity(ln: dict, hist: list[dict], marks: dict) -> tuple[float, bool]:
    """Cash + open positions at the live best bid. A position with no bid this
    run is carried at cost and the result flagged (marked=False)."""
    total, marked = ln["cash_usd"], True
    for h in open_positions(hist, ln["lineage_id"]):
        bid = marks.get(h["token_id"])
        if bid is None:
            total += h["cost_usd"]
            marked = False
        else:
            total += h["shares"] * bid
    return round(total, 2), marked


def burn_total(pop: dict, since: Optional[datetime] = None) -> tuple[float, bool]:
    """Oracle burn in USD; known=False when any call's cost is PENDING."""
    usd, known = 0.0, True
    for b in pop.get("burn", []):
        if since and datetime.fromisoformat(b["ts"]) < since:
            continue
        if b["usd"] is None:
            known = False
        else:
            usd += b["usd"]
    return round(usd, 6), known


def record_burn(pop: dict, usd: Optional[float], tokens: int, now: Optional[datetime] = None) -> None:
    pop.setdefault("burn", []).append({"ts": _iso(now or _now()), "usd": usd, "tokens": tokens})


# ---------------------------------------------------------------- settlement
def _close(pop: dict, h: dict, status: str, proceeds: float, now: datetime) -> None:
    h["status"], h["closed_at"] = status, _iso(now)
    h["proceeds_usd"] = round(proceeds, 2)
    h["pnl_usd"] = round(proceeds - h["cost_usd"], 2)
    ln = _ln(pop, h["lineage_id"])
    if ln is None:
        return
    ln["cash_usd"] = round(ln["cash_usd"] + proceeds, 2)
    if h["pnl_usd"] > 0:
        ln["wins"] += 1
    elif h["pnl_usd"] < 0:
        ln["losses"] += 1


def settle(pop: dict, hist: list[dict], fetch_market: Callable, now: Optional[datetime] = None) -> list[str]:
    """Pay out resolved markets ($1 a winning share). Unresolved stay OPEN."""
    now = now or _now()
    out = []
    for h in open_positions(hist):
        try:
            m = fetch_market(h["market_id"])
        except Exception as e:                     # a failed fetch leaves it OPEN
            out.append(f"settle: market {h['market_id']} PENDING ({type(e).__name__})")
            continue
        res = paper_exec.resolution(m)
        if res is None:
            continue
        pay = 0.5 if res == "SPLIT" else (1.0 if res == h["side"] else 0.0)
        status = "SPLIT" if res == "SPLIT" else ("WON" if pay else "LOST")
        _close(pop, h, status, h["shares"] * pay, now)
        out.append(f"{status}: {h['question'][:60]} ({h['side']}) pnl ${h['pnl_usd']:+.2f}")
    return out


def take_profit(pop: dict, hist: list[dict], books: dict, now: Optional[datetime] = None) -> list[str]:
    """Sell a position on the book once its best bid reaches 0.985."""
    now = now or _now()
    out = []
    for h in open_positions(hist):
        book = books.get(h["token_id"])
        if not book or book["best_bid"] is None or book["best_bid"] < C.TAKE_PROFIT_BID:
            continue
        fill = paper_exec.sell_fak(book["bids"], h["shares"], C.TAKE_PROFIT_BID)
        if not fill or fill["shares"] < h["shares"] - 1e-6:
            continue                               # not enough bids at 0.985+: keep holding
        _close(pop, h, "SOLD", fill["proceeds_usd"], now)
        out.append(f"SOLD early @ {fill['avg_price']:.3f}: {h['question'][:60]} pnl ${h['pnl_usd']:+.2f}")
    return out


# ---------------------------------------------------------------- life cycle
def life_cycle(pop: dict, hist: list[dict], marks: dict, now: Optional[datetime] = None) -> list[str]:
    """Deaths, mitosis, and the population's earn-your-keep check."""
    now = now or _now()
    out = []
    for ln in living(pop):
        eq, _ = equity(ln, hist, marks)
        if eq < C.SURVIVAL_FLOOR_USD:
            ln["alive"], ln["died"] = False, _iso(now)
            ln["death_reason"] = f"equity ${eq:.2f} under the ${C.SURVIVAL_FLOOR_USD:.2f} floor"
            out.append(f"EXTINCT {ln['lineage_id']} gen {ln['generation']}: {ln['death_reason']}")
    for ln in sorted(living(pop), key=lambda x: -equity(x, hist, marks)[0]):
        if len(living(pop)) >= C.MAX_LINEAGES:
            break
        eq, _ = equity(ln, hist, marks)
        if eq >= C.GENESIS_BANKROLL_USD * C.MITOSIS_MULTIPLE and ln["cash_usd"] >= C.GENESIS_BANKROLL_USD:
            ln["cash_usd"] = round(ln["cash_usd"] - C.GENESIS_BANKROLL_USD, 2)
            ln["children"] += 1
            kid = new_lineage(ln["lineage_id"], ln["generation"] + 1, C.GENESIS_BANKROLL_USD, _iso(now))
            pop["lineages"].append(kid)
            out.append(f"MITOSIS {ln['lineage_id']} -> {kid['lineage_id']} (gen {kid['generation']}, "
                       f"${C.GENESIS_BANKROLL_USD:.2f})")

    if pop.get("halted"):
        return out
    total_eq = sum(equity(ln, hist, marks)[0] for ln in living(pop))
    burn, _ = burn_total(pop)
    if not living(pop):
        pop["halted"] = f"{_iso(now)} every lineage extinct"
    elif total_eq - burn < C.SURVIVAL_FLOOR_USD:
        pop["halted"] = f"{_iso(now)} equity ${total_eq:.2f} net of burn ${burn:.2f} under the floor"
    else:
        since = now - timedelta(hours=C.BURN_WINDOW_HOURS)
        settled = [h for h in hist if h["status"] != "OPEN" and h.get("closed_at")]
        recent = [h for h in settled if datetime.fromisoformat(h["closed_at"]) >= since]
        burn48, known = burn_total(pop, since)
        pnl48 = sum(h["pnl_usd"] for h in recent)
        if len(settled) >= C.MIN_SETTLED_FOR_BURN_RULE and known and burn48 > 0 and pnl48 < burn48:
            pop["halted"] = (f"{_iso(now)} 48h PnL ${pnl48:+.2f} did not cover 48h burn ${burn48:.2f} "
                             f"after {len(settled)} settled positions")
    if pop.get("halted"):
        out.append(f"HALTED: {pop['halted']}")
    return out


# ---------------------------------------------------------------- allocation
def allocate(pop: dict, hist: list[dict], opportunities: list[dict], marks: dict, run_id: str,
             now: Optional[datetime] = None) -> list[dict]:
    """opportunities: candidates carrying 'oracle' {true_prob_yes, confidence, reasoning}.
    Strongest lineage gets the strongest opportunity; one new position per
    lineage per run; one position per event across the population."""
    now = now or _now()
    if pop.get("halted"):
        return []
    held_events = {h["event_id"] for h in open_positions(hist)}
    free = sorted(living(pop), key=lambda x: -equity(x, hist, marks)[0])
    opened, decisions = [], []
    for c in opportunities:
        o = c["oracle"]
        # rank on the edge the gate would see, for the strongest lineage
        d = risk_gate.evaluate(true_prob_yes=o["true_prob_yes"], confidence=o["confidence"],
                               book_yes=c["book_yes"], book_no=c["book_no"], tick_size=c["tick_size"],
                               equity_usd=C.GENESIS_BANKROLL_USD, cash_usd=C.GENESIS_BANKROLL_USD,
                               deployed_usd=0.0, event_held=False)
        decisions.append((d.edge, c))
    for _, c in sorted(decisions, key=lambda x: -x[0]):
        if not free:
            break
        for ln in list(free):
            eq, _ = equity(ln, hist, marks)
            o = c["oracle"]
            d = risk_gate.evaluate(true_prob_yes=o["true_prob_yes"], confidence=o["confidence"],
                                   book_yes=c["book_yes"], book_no=c["book_no"], tick_size=c["tick_size"],
                                   equity_usd=eq, cash_usd=ln["cash_usd"],
                                   deployed_usd=deployed(hist, ln["lineage_id"]),
                                   event_held=c["event_id"] in held_events)
            c.setdefault("decisions", []).append({"lineage_id": ln["lineage_id"], **d.to_dict()})
            if not d.execute:
                if d.reason.startswith(("Event lock", "Confidence", "Oracle", "Edge")) or "outside" in d.reason \
                        or "depth" in d.reason:
                    break                                  # same answer for every lineage
                continue
            book = c["book_yes"] if d.side == "YES" else c["book_no"]
            fill = paper_exec.buy_fak(book["asks"], d.stake_usd, d.limit_price)
            if not fill:
                break
            ln["cash_usd"] = round(ln["cash_usd"] - fill["cost_usd"], 2)
            rec = {"pos_id": "pp_" + uuid.uuid4().hex[:10], "lineage_id": ln["lineage_id"],
                   "generation": ln["generation"], "run_id": run_id, "opened_at": _iso(now),
                   "market_id": c["market_id"], "condition_id": c["condition_id"],
                   "event_id": c["event_id"], "question": c["question"], "end_date": c["end_date"],
                   "side": d.side, "token_id": c["token_yes"] if d.side == "YES" else c["token_no"],
                   "neg_risk": c["neg_risk"], "ask_at_entry": book["best_ask"],
                   "book_fetched_at": c.get("fetched_at"),
                   "oracle_p_yes": o["true_prob_yes"], "confidence": o["confidence"],
                   "edge": d.edge, "kelly_raw": d.kelly_raw, "stake_fraction": d.capped_fraction,
                   **fill, "status": "OPEN"}
            hist.append(rec)
            opened.append(rec)
            held_events.add(c["event_id"])
            free.remove(ln)
            break
    return opened
