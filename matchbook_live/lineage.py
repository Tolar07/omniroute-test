"""
HEARTBEAT LINEAGE ON MATCHBOOK — the AI Survivor (framework standing order 23,
engine/survivor.py) carried onto the exchange. LIVE CAPITAL.

Kept from the survivor and the Polymarket engine:
  - lineages with an id, a parent and a generation; the dead stay on record
  - at most MAX_LINEAGES alive; strongest lineage gets the strongest edge,
    one new position per lineage per run, one position per event across the
    whole population (the event lock)
  - every position kept in history.jsonl and graded in place; a market
    Matchbook has not settled stays OPEN — never guessed (HR35)

Money rules ("earn your keep", £50 agent):
  - lifeforce is real GBP on the ledger; genesis £50 is the only money that
    ever comes in from outside. A lineage dies when its equity falls under
    the £5 survival floor
  - MITOSIS: equity >= 2x genesis and cash >= genesis -> a child is born with
    genesis cash taken from the parent. A child is a ledger row inside the
    same Matchbook account: no new account, no deposit
  - the population halts (no new positions) when total equity net of oracle
    burn falls under the floor, or when, after 10+ settled positions, the last
    48 h of realised P&L does not cover the last 48 h of burn. The reason goes
    to post_mortem.log. Nothing restarts it but the Architect (--reseed)

Open positions are carried at cost: a back bet has no honest mark without
trading out, and the agent never trades out.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from matchbook_live import config as C
from matchbook_live import risk_gate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(t: datetime) -> str:
    return t.isoformat(timespec="seconds")


def new_lineage(parent: Optional[str] = None, generation: int = 0,
                cash: float = C.GENESIS_BANKROLL_GBP, born: Optional[str] = None) -> dict:
    return {"lineage_id": "mb_" + uuid.uuid4().hex[:10], "parent_id": parent,
            "generation": generation, "cash_gbp": round(cash, 2), "alive": True,
            "born": born or _iso(_now()), "died": None, "death_reason": None,
            "wins": 0, "losses": 0, "children": 0}


# ---------------------------------------------------------------- persistence
def load(state_dir: Path = C.STATE_DIR) -> tuple[dict, list[dict]]:
    lf, hf = state_dir / "lineage.json", state_dir / "history.jsonl"
    pop = (json.loads(lf.read_text(encoding="utf-8")) if lf.exists() else
           {"lineages": [new_lineage()], "burn": [], "halted": None,
            "capital_in_gbp": C.GENESIS_BANKROLL_GBP, "loan_gbp": C.LOAN_GBP})
    pop.setdefault("loan_gbp", C.LOAN_GBP)          # state written before the loan existed
    hist = ([json.loads(x) for x in hf.read_text(encoding="utf-8").splitlines() if x.strip()]
            if hf.exists() else [])
    return pop, hist


def save(pop: dict, hist: list[dict], state_dir: Path = C.STATE_DIR) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    tmp = state_dir / "lineage.json.tmp"
    tmp.write_text(json.dumps(pop, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(state_dir / "lineage.json")
    tmp = state_dir / "history.jsonl.tmp"
    tmp.write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in hist), encoding="utf-8")
    tmp.replace(state_dir / "history.jsonl")


def living(pop: dict) -> list[dict]:
    return [ln for ln in pop["lineages"] if ln["alive"]]


def open_positions(hist: list[dict], lineage_id: Optional[str] = None) -> list[dict]:
    return [h for h in hist if h["status"] == "OPEN"
            and (lineage_id is None or h["lineage_id"] == lineage_id)]


def _ln(pop: dict, lineage_id: str) -> Optional[dict]:
    return next((x for x in pop["lineages"] if x["lineage_id"] == lineage_id), None)


# ---------------------------------------------------------------- valuation
def deployed(hist: list[dict], lineage_id: str) -> float:
    return round(sum(h["cost_gbp"] for h in open_positions(hist, lineage_id)), 2)


def equity(ln: dict, hist: list[dict]) -> float:
    return round(ln["cash_gbp"] + deployed(hist, ln["lineage_id"]), 2)


def burn_total(pop: dict, since: Optional[datetime] = None) -> tuple[float, bool]:
    """Oracle burn in GBP; known=False when any call's cost is PENDING."""
    gbp, known = 0.0, True
    for b in pop.get("burn", []):
        if since and datetime.fromisoformat(b["ts"]) < since:
            continue
        if b["gbp"] is None:
            known = False
        else:
            gbp += b["gbp"]
    return round(gbp, 6), known


def record_burn(pop: dict, gbp: Optional[float], tokens: int, now: Optional[datetime] = None) -> None:
    pop.setdefault("burn", []).append({"ts": _iso(now or _now()), "gbp": gbp, "tokens": tokens})


# ---------------------------------------------------------------- settlement
def _close(pop: dict, h: dict, status: str, net: float, now: datetime) -> None:
    """Credit back the recorded cost plus Matchbook's net P&L for the offer."""
    h["status"], h["closed_at"] = status, _iso(now)
    h["pnl_gbp"] = round(net, 2)
    h["proceeds_gbp"] = round(h["cost_gbp"] + net, 2)
    ln = _ln(pop, h["lineage_id"])
    if ln is None:
        return
    ln["cash_gbp"] = round(ln["cash_gbp"] + h["proceeds_gbp"], 2)
    if net > 0:
        ln["wins"] += 1
    elif net < 0:
        ln["losses"] += 1


def settle(pop: dict, hist: list[dict], fetch_settled: Callable, now: Optional[datetime] = None) -> list[str]:
    """fetch_settled(market_ids) -> {offer_id: {'net', 'stake', 'result'}}. Unsettled stay OPEN."""
    now = now or _now()
    opens = open_positions(hist)
    if not opens:
        return []
    try:
        done = fetch_settled(sorted({h["market_id"] for h in opens}))
    except Exception as e:
        return [f"settle: report PENDING ({type(e).__name__}: {str(e)[:120]})"]
    out = []
    for h in opens:
        s = done.get(str(h["offer_id"]))
        if not s:
            continue
        status = {"WIN": "WON", "LOSE": "LOST"}.get(s["result"], s["result"])
        if s["stake"] and abs(s["stake"] - h["cost_gbp"]) >= 0.01:
            h["matched_at_settlement_gbp"] = s["stake"]
        _close(pop, h, status, s["net"], now)
        out.append(f"{status}: {h['runner_name']} ({h['event_name'][:50]}) net £{h['pnl_gbp']:+.2f}")
    return out


def void(pop: dict, h: dict, now: Optional[datetime] = None) -> None:
    """An offer that never matched and is now cancelled: nothing at risk."""
    _close(pop, h, "VOID", 0.0, now or _now())


# ---------------------------------------------------------------- the loan
def loan_check(pop: dict, hist: list[dict], now: datetime) -> list[str]:
    """Tell the Architect, once, when the £50 loan can be repaid."""
    loan = pop.get("loan_gbp", 0)
    if loan <= 0 or pop.get("repay_ready"):
        return []
    eq = sum(equity(ln, hist) for ln in living(pop))
    cash = sum(ln["cash_gbp"] for ln in living(pop))
    if eq >= C.REPAY_AT_EQUITY_GBP and cash >= loan:
        pop["repay_ready"] = _iso(now)
        return [f"LOAN REPAYABLE: agent equity £{eq:.2f} (cash £{cash:.2f}) covers your £{loan:.2f} loan and leaves "
                f"it £{eq - loan:.2f} of its own. Withdraw £{loan:.2f} on matchbook.com, then run the workflow "
                "with mode 'repaid'. Until then it keeps trading; no lineage splits before you are repaid."]
    return []


def repaid(pop: dict, hist: list[dict], now: Optional[datetime] = None) -> str:
    """Architect withdrew the loan: take it off the books, strongest lineages' cash first."""
    loan = pop.get("loan_gbp", 0)
    if loan <= 0:
        return "no loan outstanding"
    cash = sum(ln["cash_gbp"] for ln in living(pop))
    if cash < loan:
        return f"NOT recorded: lineage cash £{cash:.2f} is under the £{loan:.2f} loan — wait for the REPAYABLE message"
    left = loan
    for ln in sorted(living(pop), key=lambda x: -x["cash_gbp"]):
        take = min(left, ln["cash_gbp"])
        ln["cash_gbp"] = round(ln["cash_gbp"] - take, 2)
        left = round(left - take, 2)
        if left <= 0:
            break
    pop["loan_gbp"], pop["repaid_at"], pop["repay_ready"] = 0.0, _iso(now or _now()), None
    pop["capital_in_gbp"] = round(pop.get("capital_in_gbp", C.GENESIS_BANKROLL_GBP) - loan, 2)
    return f"LOAN REPAID: £{loan:.2f} back to the Architect; the agent now trades only money it made"


# ---------------------------------------------------------------- life cycle
def life_cycle(pop: dict, hist: list[dict], now: Optional[datetime] = None) -> list[str]:
    """Deaths, mitosis, and the population's earn-your-keep check."""
    now = now or _now()
    out = []
    for ln in living(pop):
        eq = equity(ln, hist)
        if eq < C.SURVIVAL_FLOOR_GBP and not open_positions(hist, ln["lineage_id"]):
            ln["alive"], ln["died"] = False, _iso(now)
            ln["death_reason"] = f"equity £{eq:.2f} under the £{C.SURVIVAL_FLOOR_GBP:.2f} floor"
            out.append(f"EXTINCT {ln['lineage_id']} gen {ln['generation']}: {ln['death_reason']}")
    out += loan_check(pop, hist, now)
    for ln in sorted(living(pop), key=lambda x: -equity(x, hist)):
        if pop.get("loan_gbp", 0) > 0 or len(living(pop)) >= C.MAX_LINEAGES:
            break                                   # the lender is repaid before any lineage splits
        if equity(ln, hist) >= C.GENESIS_BANKROLL_GBP * C.MITOSIS_MULTIPLE \
                and ln["cash_gbp"] >= C.GENESIS_BANKROLL_GBP:
            ln["cash_gbp"] = round(ln["cash_gbp"] - C.GENESIS_BANKROLL_GBP, 2)
            ln["children"] += 1
            kid = new_lineage(ln["lineage_id"], ln["generation"] + 1, C.GENESIS_BANKROLL_GBP, _iso(now))
            pop["lineages"].append(kid)
            out.append(f"MITOSIS {ln['lineage_id']} -> {kid['lineage_id']} (gen {kid['generation']}, "
                       f"£{C.GENESIS_BANKROLL_GBP:.2f} from the parent's cash)")

    if pop.get("halted"):
        return out
    total_eq = sum(equity(ln, hist) for ln in living(pop))
    burn, _ = burn_total(pop)
    if not living(pop):
        pop["halted"] = f"{_iso(now)} every lineage extinct"
    elif total_eq - burn < C.SURVIVAL_FLOOR_GBP:
        pop["halted"] = f"{_iso(now)} equity £{total_eq:.2f} net of burn £{burn:.2f} under the floor"
    else:
        since = now - timedelta(hours=C.BURN_WINDOW_HOURS)
        settled = [h for h in hist if h["status"] not in ("OPEN", "VOID") and h.get("closed_at")]
        recent = [h for h in settled if datetime.fromisoformat(h["closed_at"]) >= since]
        burn48, known = burn_total(pop, since)
        pnl48 = sum(h["pnl_gbp"] for h in recent)
        if len(settled) >= C.MIN_SETTLED_FOR_BURN_RULE and known and burn48 > 0 and pnl48 < burn48:
            pop["halted"] = (f"{_iso(now)} 48h P&L £{pnl48:+.2f} did not cover 48h burn £{burn48:.2f} "
                             f"after {len(settled)} settled positions")
    if pop.get("halted"):
        out.append(f"HALTED: {pop['halted']}")
    return out


# ---------------------------------------------------------------- allocation
def allocate(pop: dict, hist: list[dict], opportunities: list[dict], run_id: str, place: Callable,
             free_funds: Optional[float] = None, now: Optional[datetime] = None) -> tuple[list[dict], list[str]]:
    """opportunities carry 'oracle' {true_prob, confidence, reasoning}.
    place(runner_id, odds, stake) -> (fill | None, note). Strongest lineage
    gets the strongest edge; one new position per lineage per run; one
    position per event across the population. free_funds (Matchbook) is
    drawn down as stakes go out, so the account is never over-committed."""
    now = now or _now()
    notes: list[str] = []
    if pop.get("halted"):
        return [], notes
    held_events = {h["event_id"] for h in open_positions(hist)}
    free = sorted(living(pop), key=lambda x: -equity(x, hist))
    ranked = sorted(opportunities, key=lambda c: -(c["oracle"]["true_prob"]
                                                   - (1 + C.COMMISSION) / c["book"]["best_back"]))
    opened = []
    for c in ranked:
        if not free:
            break
        o = c["oracle"]
        for ln in list(free):
            d = risk_gate.evaluate(true_prob=o["true_prob"], confidence=o["confidence"], book=c["book"],
                                   equity_gbp=equity(ln, hist), cash_gbp=ln["cash_gbp"],
                                   deployed_gbp=deployed(hist, ln["lineage_id"]),
                                   event_held=c["event_id"] in held_events, free_funds_gbp=free_funds,
                                   min_edge=c.get("min_edge", C.MIN_EDGE))
            c.setdefault("decisions", []).append({"lineage_id": ln["lineage_id"], **d.to_dict()})
            if not d.execute:
                if d.reason.startswith(("Event lock", "Confidence", "Oracle", "Edge", "Odds", "Back depth")):
                    break                                  # same answer for every lineage
                continue
            try:
                fill, note = place(c["runner_id"], d.odds, d.stake_gbp)
            except Exception as e:
                notes.append(f"ORDER ERROR {c['runner_name']} ({c['event_name'][:40]}): "
                             f"{type(e).__name__}: {str(e)[:160]}")
                return opened, notes                        # stop sending orders this run
            notes.append(f"order {c['runner_name']} @ {d.odds:.2f} £{d.stake_gbp:.2f}: {note}")
            if not fill:
                break
            ln["cash_gbp"] = round(ln["cash_gbp"] - fill["matched_gbp"], 2)
            if free_funds is not None:
                free_funds -= fill["matched_gbp"]
            rec = {"pos_id": "mp_" + uuid.uuid4().hex[:10], "lineage_id": ln["lineage_id"],
                   "generation": ln["generation"], "run_id": run_id, "opened_at": _iso(now),
                   "event_id": c["event_id"], "event_name": c["event_name"], "start": c["start"],
                   "market_id": c["market_id"], "market_name": c["market_name"],
                   "runner_id": c["runner_id"], "runner_name": c["runner_name"],
                   "best_back_at_entry": c["book"]["best_back"], "odds_asked": d.odds,
                   "oracle_p": o["true_prob"], "confidence": o["confidence"],
                   "edge": d.edge, "kelly_raw": d.kelly_raw, "stake_fraction": d.capped_fraction,
                   "stake_asked_gbp": d.stake_gbp, "offer_id": fill["offer_id"],
                   "source": c.get("source", "oracle"), "fw_key": c.get("fw_key"),
                   "fw_pick": c.get("fw_pick"), "fw_code": c.get("fw_code"), "fw_price": c.get("fw_price"),
                   "fw_pool": c.get("fw_pool", False),
                   "cost_gbp": fill["matched_gbp"], "avg_odds": fill["avg_odds"],
                   "cancel_pending": fill.get("cancel_pending", False), "status": "OPEN"}
            hist.append(rec)
            opened.append(rec)
            held_events.add(c["event_id"])
            free.remove(ln)
            break
    return opened, notes
