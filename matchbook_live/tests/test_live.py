"""Matchbook live agent tests — offline, no network, a fake exchange.

    python -m unittest matchbook_live.tests.test_live -v
"""
from __future__ import annotations

import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from matchbook_live import config as C
from matchbook_live import executor, framework_feed
from matchbook_live import lineage as L
from matchbook_live import notify, oracle, risk_gate, run, scanner

NOW = datetime(2026, 10, 14, 21, 0, tzinfo=timezone.utc)
PKG = Path(__file__).resolve().parents[1]


def book(back=2.0, lay=2.04, depth=100.0):
    return {"best_back": back, "best_lay": lay, "implied": round(1 / back, 6),
            "spread": round(1 / back - 1 / lay, 6), "back_depth_gbp": depth, "backs": [(back, depth)]}


def gate(**kw):
    args = dict(true_prob=0.65, confidence=0.80, book=book(), equity_gbp=50.0, cash_gbp=50.0,
                deployed_gbp=0.0, event_held=False, free_funds_gbp=None, commission=0.02)
    args.update(kw)
    return risk_gate.evaluate(**args)


class RiskGate(unittest.TestCase):
    def test_edge_is_over_commission_adjusted_break_even(self):
        # break-even at 2.0 with 2% volume commission = 1.02 / 2 = 0.51
        self.assertFalse(gate(true_prob=0.59).execute)              # edge 0.08, not greater
        self.assertTrue(gate(true_prob=0.60).execute)

    def test_half_kelly_capped_at_6pct_of_equity(self):
        d = gate(true_prob=0.80)
        self.assertAlmostEqual(d.capped_fraction, 0.06)
        self.assertAlmostEqual(d.stake_gbp, 3.00)                   # 6% of £50

    def test_stake_capped_by_cash_exposure_and_free_funds(self):
        self.assertAlmostEqual(gate(true_prob=0.80, cash_gbp=2.5).stake_gbp, 1.50)
        self.assertAlmostEqual(gate(true_prob=0.80, deployed_gbp=31.0).stake_gbp, 1.50)  # 32.5 ceiling
        self.assertAlmostEqual(gate(true_prob=0.80, free_funds_gbp=3.0).stake_gbp, 2.00)
        self.assertIn("minimum", gate(true_prob=0.80, free_funds_gbp=1.5).reason)

    def test_rejections(self):
        self.assertIn("Confidence", gate(confidence=0.69).reason)
        self.assertIn("lock", gate(event_held=True).reason)
        self.assertIn("exposure", gate(deployed_gbp=50 * 0.65).reason)
        self.assertIn("outside", gate(true_prob=0.99, book=book(1.10, 1.11)).reason)
        self.assertIn("depth", gate(book=book(depth=10)).reason)


def event(start, back=2.0, lay=2.04, depth=40.0, market="Match Odds", status="open"):
    def runner(i, name):
        return {"id": 100 + i, "name": name, "status": "open",
                "prices": [{"side": "back", "odds": back, "available-amount": depth},
                           {"side": "back", "odds": back - 0.04, "available-amount": 5},
                           {"side": "lay", "odds": lay, "available-amount": 20}]}
    return {"id": 9, "name": "A v B", "start": start.isoformat().replace("+00:00", "Z"), "status": status,
            "markets": [{"id": 77, "name": market, "status": "open",
                         "runners": [runner(0, "A"), runner(1, "B"), runner(2, "Draw")]}]}


class Scanner(unittest.TestCase):
    def test_best_back_is_highest_odds(self):
        b = scanner.runner_book({"prices": [{"side": "back", "odds": 1.24, "available-amount": 9},
                                            {"side": "back", "odds": 1.26, "available-amount": 10},
                                            {"side": "lay", "odds": 1.28, "available-amount": 5},
                                            {"side": "lay", "odds": 1.27, "available-amount": 5}]})
        self.assertEqual((b["best_back"], b["best_lay"], b["back_depth_gbp"]), (1.26, 1.27, 19.0))

    def test_filters(self):
        ok = NOW + timedelta(hours=5)
        self.assertEqual(len(scanner.candidates_from_event(event(ok), NOW)), 3)
        self.assertEqual(scanner.candidates_from_event(event(NOW + timedelta(hours=1)), NOW), [])
        self.assertEqual(scanner.candidates_from_event(event(ok, market="Correct Score"), NOW), [])
        self.assertEqual(scanner.candidates_from_event(event(ok, lay=2.4), NOW), [])      # wide spread
        self.assertEqual(scanner.candidates_from_event(event(ok, depth=5), NOW), [])      # thin
        c = scanner.candidates_from_event(event(ok), NOW)[0]
        self.assertEqual(c["other_runners"], ["B", "Draw"])


class Oracle(unittest.TestCase):
    def test_brief_carries_no_price(self):
        c = scanner.candidates_from_event(event(NOW + timedelta(hours=5)), NOW)[0]
        brief = oracle.blind_brief(c)
        self.assertIn("RUNNER NAME: A", brief)
        for price in ("2.0", "2.04", "1.96", "40", "0.5"):           # back, lay, depth, implied
            self.assertNotIn(price, brief)
        self.assertNotRegex(brief, re.compile(r"\bback\b|\blay\b|depth|implied", re.I))


class FakeExchange:
    """Matches `match` of each offer at once; records every call."""

    def __init__(self, match=1.0, settled=None, free=50.0):
        self.match, self.calls, self.token = match, [], "t"
        self.settled_rows, self.free, self.offers = settled or [], free, {}

    def events(self, offset=0, per_page=50):
        return {"events": [event(datetime.now(timezone.utc) + timedelta(hours=5))] if offset == 0 else [],
                "total": 1}

    def back(self, runner_id, odds, stake):
        self.calls.append(("back", runner_id, odds, stake))
        m = round(stake * self.match, 2)
        oid = 5000 + len(self.calls)
        o = {"id": oid, "status": "matched" if m == stake else "open", "remaining": round(stake - m, 2),
             "matched-bets": [{"stake": m, "decimal-odds": odds}] if m else []}
        self.offers[oid] = o
        return o

    def cancel(self, offer_id):
        self.calls.append(("cancel", offer_id))
        return {}

    def offer(self, offer_id):
        return self.offers[offer_id]

    def balance(self):
        return {"balance": 50, "exposure": 0, "free-funds": self.free}

    def settled(self, market_ids):
        return self.settled_rows


class Execution(unittest.TestCase):
    def test_full_match(self):
        fx = FakeExchange()
        fill, note = executor.back_fak(fx, 101, 2.0, 3.0)
        self.assertEqual(fill["matched_gbp"], 3.0)
        self.assertNotIn("cancel", [c[0] for c in fx.calls])

    def test_partial_match_cancels_the_rest(self):
        fx = FakeExchange(match=0.5)
        fill, note = executor.back_fak(fx, 101, 2.0, 3.0)
        self.assertEqual(fill["matched_gbp"], 1.5)
        self.assertIn(("cancel", fill["offer_id"]), fx.calls)

    def test_nothing_matched(self):
        fill, note = executor.back_fak(FakeExchange(match=0.0), 101, 2.0, 3.0)
        self.assertIsNone(fill)


def opp(prob=0.70, conf=0.8, event_id="9", runner_id=100):
    c = scanner.candidates_from_event(event(NOW + timedelta(hours=5)), NOW)[0]
    c.update(event_id=event_id, runner_id=runner_id)
    c["oracle"] = {"true_prob": prob, "confidence": conf, "reasoning": ""}
    return c


class Lineage(unittest.TestCase):
    def test_allocate_debits_matched_and_locks_event(self):
        pop, hist = {"lineages": [L.new_lineage(), L.new_lineage()], "burn": [], "halted": None}, []
        fx = FakeExchange()
        place = lambda r, o, s: executor.back_fak(fx, r, o, s)       # noqa: E731
        opened, _ = L.allocate(pop, hist, [opp(), opp(runner_id=101)], "R", place, 50.0, NOW)
        self.assertEqual(len(opened), 1)                              # same event: one position
        self.assertEqual(len([c for c in fx.calls if c[0] == "back"]), 1)
        ln = L._ln(pop, opened[0]["lineage_id"])
        self.assertAlmostEqual(ln["cash_gbp"] + opened[0]["cost_gbp"], 50.0)

    def test_order_error_stops_the_run(self):
        pop, hist = {"lineages": [L.new_lineage(), L.new_lineage()], "burn": [], "halted": None}, []

        def boom(*a):
            raise RuntimeError("HTTP 500")
        opened, notes = L.allocate(pop, hist, [opp(), opp(event_id="10")], "R", boom, 50.0, NOW)
        self.assertEqual(opened, [])
        self.assertTrue(any("ORDER ERROR" in n for n in notes))

    def test_settle_uses_exchange_net_pnl(self):
        pop = {"lineages": [L.new_lineage()], "burn": [], "halted": None}
        ln = pop["lineages"][0]
        ln["cash_gbp"] = 47.0
        h = {"lineage_id": ln["lineage_id"], "status": "OPEN", "offer_id": 5001, "market_id": "77",
             "cost_gbp": 3.0, "runner_name": "A", "event_name": "A v B", "event_id": "9"}
        out = L.settle(pop, [h], lambda ids: {"5001": {"net": 2.88, "stake": 3.0, "result": "WIN"}}, NOW)
        self.assertEqual(h["status"], "WON")
        self.assertAlmostEqual(ln["cash_gbp"], 52.88)
        self.assertTrue(out)

    def test_settled_report_parsing(self):
        fx = FakeExchange(settled=[{"selections": [{"bets": [
            {"offer-id": 5001, "stake": 2.0, "net-profit-and-loss": -2.04, "result": "LOSE"},
            {"offer-id": 5001, "stake": 1.0, "net-profit-and-loss": -1.02, "result": "LOSE"}]}]}])
        s = executor.settled_by_offer(fx, ["77"])["5001"]
        self.assertEqual((s["net"], s["stake"], s["result"]), (-3.06, 3.0, "LOSE"))

    def test_mitosis_funded_from_parent_cash(self):
        pop = {"lineages": [L.new_lineage()], "burn": [], "halted": None}
        pop["lineages"][0]["cash_gbp"] = 100.0
        L.life_cycle(pop, [], NOW)
        self.assertEqual(len(L.living(pop)), 2)
        self.assertAlmostEqual(sum(x["cash_gbp"] for x in L.living(pop)), 100.0)   # no new money

    def test_death_under_floor_and_halt(self):
        pop = {"lineages": [L.new_lineage()], "burn": [], "halted": None}
        pop["lineages"][0]["cash_gbp"] = 4.99
        out = L.life_cycle(pop, [], NOW)
        self.assertTrue(any("EXTINCT" in o for o in out))
        self.assertIn("extinct", pop["halted"])

    def test_earn_your_keep_halt(self):
        pop = {"lineages": [L.new_lineage()], "burn": [{"ts": NOW.isoformat(), "gbp": 1.0, "tokens": 1}],
               "halted": None}
        hist = [{"status": "LOST", "closed_at": NOW.isoformat(), "pnl_gbp": -0.1, "lineage_id": "x"}] * 10
        L.life_cycle(pop, hist, NOW)
        self.assertIn("did not cover", pop["halted"])


class Telegram(unittest.TestCase):
    def test_due_rules(self):
        pop = {}
        night = NOW.replace(hour=2)
        self.assertEqual(notify.due(pop, night, "LIVE — x", []), "mode now LIVE")        # first run
        self.assertIsNone(notify.due(pop, night, "LIVE — x", ["no news"]))                # quiet run
        self.assertEqual(notify.due(pop, night, "LIVE — x", ["OPEN BACK A £2"]), "news")
        self.assertEqual(notify.due(pop, NOW.replace(hour=8), "LIVE — x", []), "daily debrief")
        self.assertIsNone(notify.due(pop, NOW.replace(hour=9), "LIVE — x", []))           # once a day
        self.assertEqual(notify.due(pop, NOW.replace(hour=9), "DRY — y", []), "mode now DRY")

    def test_send_needs_config_and_cuts_long_text(self):
        sent = []
        with mock.patch.object(notify, "TOKEN", ""):
            self.assertIn("not configured", notify.send("x", post=lambda *a, **k: sent.append(1)))
        with mock.patch.object(notify, "TOKEN", "t"), mock.patch.object(notify, "CHAT_ID", "c"):
            notify.send("y" * 5000, post=lambda url, json, timeout: sent.append(json) or
                        mock.Mock(status_code=200))
        self.assertLessEqual(len(sent[-1]["text"]), 4000)


class Cycle(unittest.TestCase):
    fw_files: list = []

    def _run(self, live: bool, stop=False):
        fx = FakeExchange()
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(notify, "send", lambda text: "test: not sent"), \
                mock.patch.object(framework_feed, "fetch_picks", lambda dates: (self.fw_files, [])), \
                mock.patch.object(C, "LIVE", live), mock.patch.object(C, "USERNAME", "u"), \
                mock.patch.object(C, "PASSWORD", "p"), mock.patch.object(oracle, "available", lambda: True), \
                mock.patch.object(oracle, "evaluate",
                                  lambda c: oracle.OracleResult(0.75, 0.9, "r", 10, 0.001)):
            if stop:
                (Path(d) / C.STOP_FILE).write_text("")
            text = run.cycle(Path(d), client=fx)
        return fx, text

    def test_live_sends_orders(self):
        fx, text = self._run(live=True)
        self.assertIn("Mode: LIVE", text)
        self.assertTrue(any(c[0] == "back" for c in fx.calls))
        self.assertIn("OPEN BACK", text)

    def test_dry_and_stop_send_nothing(self):
        for live, stop in ((False, False), (True, True)):
            fx, text = self._run(live=live, stop=stop)
            self.assertFalse(any(c[0] == "back" for c in fx.calls), (live, stop))


class AccountSafety(unittest.TestCase):
    """The agent may stake and cancel. It may never move money in or out."""

    def test_no_funds_movement_endpoint(self):
        src = "\n".join(p.read_text(encoding="utf-8") for p in PKG.glob("*.py"))
        paths = re.findall(r"[\"'](/[a-z0-9/{}_-]+)", src, re.I)
        self.assertTrue(paths)
        allowed = ("/bpapi/rest/security/session", "/edge/rest/events", "/edge/rest/account/balance",
                   "/edge/rest/v2/offers", "/edge/rest/reports/v2/bets/settled", "/chat/completions",
                   "/sendMessage")
        for p in paths:
            self.assertTrue(p.startswith(allowed), f"endpoint not on the allow-list: {p}")

    def test_capital_constants(self):
        self.assertEqual(C.AGENT_CAPITAL_GBP, 50.0)
        self.assertEqual(C.SURVIVAL_FLOOR_GBP, 5.0)
        self.assertEqual(C.MAX_STAKE_FRACTION, 0.06)
        self.assertEqual(C.KELLY_FRACTION, 0.5)
        self.assertEqual(C.MAX_PORTFOLIO_EXPOSURE, 0.65)


def mb_event(start, home="Norwich", away="Southampton"):
    def r(rid, name, back, lay, hcp=None):
        return {"id": rid, "name": name, "status": "open", "handicap": hcp,
                "prices": [{"side": "back", "odds": back, "available-amount": 30},
                           {"side": "back", "odds": back - 0.01, "available-amount": 30},
                           {"side": "lay", "odds": lay, "available-amount": 30}]}
    return {"id": 501, "name": f"{home} vs {away}", "start": start.isoformat().replace("+00:00", "Z"),
            "status": "open", "markets": [
                {"id": 1, "name": "Match Odds", "market-type": "one_x_two", "status": "open",
                 "runners": [r(11, home, 2.5, 2.54), r(12, away, 3.0, 3.05), r(13, "Draw", 3.4, 3.5)]},
                {"id": 2, "name": "Total", "market-type": "total", "handicap": 2.5, "status": "open",
                 "runners": [r(21, "OVER 2.5", 1.9, 1.94, 2.5), r(22, "UNDER 2.5", 2.0, 2.04, 2.5)]},
                {"id": 3, "name": "Handicap", "market-type": "handicap", "handicap": -1.5, "status": "open",
                 "runners": [r(31, f"{home} -1.5", 4.0, 4.1, -1.5), r(32, f"{away} +1.5", 1.30, 1.31, 1.5)]},
                {"id": 4, "name": "Double Chance", "market-type": "other", "status": "open",
                 "runners": [r(41, f"{home} or Draw", 1.45, 1.47), r(42, f"{home} or {away}", 1.35, 1.37),
                             r(43, f"Draw or {away}", 1.6, 1.63)]}]}


def fw_single(market, chance, ko, home="Norwich City", away="Southampton", fixture=None):
    return {"fixture": fixture or f"{home} v {away}", "home": home, "away": away, "market": market,
            "pick": market, "chance": chance, "kickoff_utc": ko.isoformat().replace("+00:00", "Z"),
            "news_level": "OK", "code": "ABC123", "price": 1.3}


class FrameworkFeed(unittest.TestCase):
    def test_map_market(self):
        m = framework_feed.map_market
        self.assertEqual(m("SB:18|total=3.5|Under 3.5"), {"type": "total", "line": 3.5, "want": "under"})
        self.assertEqual(m("OVER_2_5"), {"type": "total", "line": 2.5, "want": "over"})
        self.assertEqual(m("SB:10||Home or Away")["want"], "home_or_away")
        self.assertEqual(m("SB:16|hcp=-1.5|Away (+1.5)"), {"type": "handicap", "line": 1.5, "want": "away"})
        self.assertIsNone(m("SB:16|hcp=-1|Away (+1)"))             # whole line: push rules, skipped
        for unsupported in ("SB:19|total=2.5|Under 2.5", "SB:34||No", "SB:548||1-3", "SB:14|hcp=0:2|Away (0:2)",
                            "SB:547|total=1.5|Home/Draw & Over 1.5"):
            self.assertIsNone(m(unsupported), unsupported)

    def test_team_names(self):
        self.assertGreater(framework_feed.alike("Man City", "Manchester City"), 0.8)
        self.assertGreater(framework_feed.alike("Bodoe/Glimt", "Bodø/Glimt"), 0.8)
        self.assertGreater(framework_feed.alike("Feyenoord", "Feyenoord Rotterdam"), 0.8)
        self.assertLess(framework_feed.alike("Norwich", "Southampton"), 0.5)

    def test_match_event_needs_kickoff_and_both_teams(self):
        ko = NOW + timedelta(hours=3)
        evs = [mb_event(ko)]
        self.assertIsNotNone(framework_feed.match_event("Norwich City", "Southampton", ko, evs))
        self.assertIsNone(framework_feed.match_event("Norwich", "Southampton", ko + timedelta(hours=1), evs))
        self.assertIsNone(framework_feed.match_event("Norwich", "Derby", ko, evs))

    def test_candidates_find_the_right_runner(self):
        ko = NOW + timedelta(hours=3)
        files = [{"date": "d", "singles": [
            fw_single("SB:18|total=2.5|Under 2.5", 0.60, ko),
            fw_single("SB:16|hcp=-1.5|Away (+1.5)", 0.80, ko, fixture="x2"),
            fw_single("SB:10||Home or Away", 0.75, ko, fixture="x3"),
            fw_single("SB:19|total=2.5|Under 2.5", 0.70, ko, fixture="x4"),
            fw_single("SB:10||Draw or Away", 0.70, ko + timedelta(hours=20), fixture="x5")]}]
        got, skipped = framework_feed.candidates(files, [mb_event(ko)], NOW, set())
        self.assertEqual(sorted(c["runner_name"] for c in got),
                         ["Norwich or Southampton", "Southampton +1.5", "UNDER 2.5"])
        self.assertTrue(all(c["source"] == "framework" and c["oracle"]["confidence"] == 1.0 for c in got))
        self.assertEqual(len(skipped), 1)                       # team total; x5 (23 h away) waits quietly
        self.assertIn("not on Matchbook", skipped[0])

    def test_already_bet_leg_is_not_repeated(self):
        ko = NOW + timedelta(hours=3)
        files = [{"date": "d", "singles": [fw_single("SB:18|total=2.5|Under 2.5", 0.60, ko)]}]
        key = "d|Norwich City v Southampton|SB:18|total=2.5|Under 2.5"
        self.assertEqual(framework_feed.candidates(files, [mb_event(ko)], NOW, {key})[0], [])

    def test_framework_edge_rule(self):
        # UNDER 2.5 @ 2.0: break-even 1.02 / 2.0 = 0.51
        ko = NOW + timedelta(hours=3)
        files = [{"date": "d", "singles": [fw_single("SB:18|total=2.5|Under 2.5", 0.52, ko)]}]
        (c,), _ = framework_feed.candidates(files, [mb_event(ko)], NOW, set())

        def gate_at(p):
            return risk_gate.evaluate(true_prob=p, confidence=1.0, book=c["book"], equity_gbp=50, cash_gbp=50,
                                      deployed_gbp=0, event_held=False, min_edge=c["min_edge"])
        self.assertFalse(gate_at(0.50).execute)                     # no edge at Matchbook's price
        self.assertIn("minimum", gate_at(0.52).reason)              # 1 pt edge: ½-Kelly stake under £1
        d = gate_at(0.58)
        self.assertTrue(d.execute)                                  # 7 pts: bets (oracle would need 8+)
        self.assertLessEqual(d.stake_gbp, 3.0)


class FrameworkCycle(unittest.TestCase):
    def test_framework_pick_goes_live(self):
        ko = datetime.now(timezone.utc) + timedelta(hours=3)
        cyc = Cycle()
        cyc.fw_files = [{"date": "d", "singles": [fw_single("SB:18|total=2.5|Under 2.5", 0.60, ko)]}]   # 9 pts edge
        ev = mb_event(ko)
        with mock.patch.object(FakeExchange, "events",
                               lambda self, offset=0, per_page=50: {"events": [ev] if offset == 0 else [],
                                                                    "total": 1}):
            fx, text = cyc._run(live=True)
        self.assertIn(("back", 22, 2.0), [c[:3] for c in fx.calls])  # UNDER 2.5 runner at the best back
        self.assertIn("framework", text)


if __name__ == "__main__":
    unittest.main()
