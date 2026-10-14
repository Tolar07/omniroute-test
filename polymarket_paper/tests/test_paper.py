"""Polymarket paper engine tests — offline, no network.

    python -m unittest polymarket_paper.tests.test_paper -v
"""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from polymarket_paper import config as C
from polymarket_paper import lineage as L
from polymarket_paper import oracle, paper_exec, risk_gate, scanner

NOW = datetime(2026, 10, 14, 21, 0, tzinfo=timezone.utc)
PKG = Path(__file__).resolve().parents[1]


def book(bid, ask, depth=100.0):
    return {"best_bid": bid, "best_ask": ask, "spread": round(ask - bid, 6),
            "top2_ask_depth_usd": depth, "bids": [(bid, 500.0)], "asks": [(ask, 500.0), (ask + 0.01, 500.0)]}


def gate(**kw):
    args = dict(true_prob_yes=0.60, confidence=0.80, book_yes=book(0.48, 0.50), book_no=book(0.49, 0.51),
                tick_size="0.01", equity_usd=66.0, cash_usd=66.0, deployed_usd=0.0, event_held=False)
    args.update(kw)
    return risk_gate.evaluate(**args)


class RiskGate(unittest.TestCase):
    def test_edge_must_be_strictly_greater_than_8pts(self):
        self.assertFalse(gate(true_prob_yes=0.58).execute)          # edge exactly 0.08
        self.assertTrue(gate(true_prob_yes=0.59).execute)

    def test_kelly_half_capped_at_6pct(self):
        d = gate(true_prob_yes=0.75)                                # kelly 0.5 -> half 0.25 -> cap 0.06
        self.assertEqual(d.side, "YES")
        self.assertAlmostEqual(d.kelly_raw, 0.5)
        self.assertAlmostEqual(d.capped_fraction, 0.06)
        self.assertAlmostEqual(d.stake_usd, 3.96)
        d = gate(true_prob_yes=0.59)                                # kelly 0.18 -> half 0.09 -> cap 0.06
        self.assertAlmostEqual(d.stake_usd, 3.96)

    def test_no_side_chosen_when_its_edge_is_bigger(self):
        d = gate(true_prob_yes=0.30)                                # NO chance 0.70 vs ask 0.51
        self.assertTrue(d.execute)
        self.assertEqual(d.side, "NO")
        self.assertAlmostEqual(d.limit_price, 0.52)

    def test_rejections(self):
        self.assertIn("Confidence", gate(confidence=0.69).reason)
        self.assertIn("lock", gate(event_held=True).reason)
        self.assertIn("exposure", gate(deployed_usd=66 * 0.65).reason)
        self.assertIn("outside", gate(true_prob_yes=0.99, book_yes=book(0.89, 0.90)).reason)
        self.assertIn("depth", gate(book_yes=book(0.48, 0.50, depth=10)).reason)
        self.assertIn("minimum", gate(cash_usd=1.5).reason)

    def test_stake_respects_exposure_room(self):
        d = gate(true_prob_yes=0.75, deployed_usd=66 * 0.65 - 2.0)
        self.assertLessEqual(d.stake_usd, 2.0)

    def test_round_to_tick(self):
        self.assertEqual(risk_gate.round_to_tick(0.5149, "0.01"), 0.51)
        self.assertEqual(risk_gate.round_to_tick(0.51234, "0.001"), 0.512)
        self.assertEqual(risk_gate.round_to_tick(1.2, "0.01"), 0.99)
        self.assertEqual(risk_gate.round_to_tick(0.0, "0.01"), 0.01)


class Books(unittest.TestCase):
    def test_parse_book_takes_best_regardless_of_order(self):
        raw = {"bids": [{"price": "0.40", "size": "10"}, {"price": "0.45", "size": "10"}],
               "asks": [{"price": "0.60", "size": "10"}, {"price": "0.50", "size": "20"}]}
        b = scanner.parse_book(raw)
        self.assertEqual((b["best_bid"], b["best_ask"]), (0.45, 0.50))
        self.assertAlmostEqual(b["spread"], 0.05)
        self.assertAlmostEqual(b["top2_ask_depth_usd"], 0.5 * 20 + 0.6 * 10)

    def test_empty_asks_is_none(self):
        self.assertIsNone(scanner.parse_book({"bids": [], "asks": []}))

    def test_prefilter_window_and_binary(self):
        m = {"id": 1, "enableOrderBook": True, "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]',
             "endDate": (NOW + timedelta(days=3)).isoformat(), "spread": 0.02, "events": [{"id": "e1"}]}
        self.assertEqual(scanner.prefilter(m, NOW)["event_id"], "e1")
        self.assertIsNone(scanner.prefilter({**m, "endDate": (NOW + timedelta(hours=1)).isoformat()}, NOW))
        self.assertIsNone(scanner.prefilter({**m, "endDate": (NOW + timedelta(days=20)).isoformat()}, NOW))
        self.assertIsNone(scanner.prefilter({**m, "spread": 0.05}, NOW))
        self.assertIsNone(scanner.prefilter({**m, "outcomes": '["Up","Down"]'}, NOW))


class Execution(unittest.TestCase):
    def test_fak_buy_walks_book_to_limit(self):
        f = paper_exec.buy_fak([(0.50, 4.0), (0.51, 100.0), (0.60, 100.0)], 3.0, 0.51)
        self.assertAlmostEqual(f["cost_usd"], 3.0)
        self.assertAlmostEqual(f["shares"], 4 + 1.0 / 0.51, places=3)

    def test_fak_buy_under_one_dollar_is_no_fill(self):
        self.assertIsNone(paper_exec.buy_fak([(0.50, 1.0), (0.70, 100.0)], 3.0, 0.51))

    def test_resolution(self):
        self.assertEqual(paper_exec.resolution({"closed": True, "outcomePrices": '["1","0"]'}), "YES")
        self.assertEqual(paper_exec.resolution({"closed": True, "outcomePrices": '["0","1"]'}), "NO")
        self.assertIsNone(paper_exec.resolution({"closed": False, "outcomePrices": '["1","0"]'}))
        self.assertIsNone(paper_exec.resolution({"closed": True, "outcomePrices": '["0.6","0.4"]'}))


class Oracle(unittest.TestCase):
    def test_brief_never_carries_prices(self):
        c = {"question": "Will X happen?", "event_title": "X", "end_date": "2026-10-20T00:00:00Z",
             "description": "Resolves YES if X.", "book_yes": book(0.4321, 0.4567),
             "outcomePrices": '["0.4567","0.5433"]', "bestAsk": 0.4567}
        brief = oracle.blind_brief(c)
        for s in ("0.4321", "0.4567", "0.5433", "ask", "bid"):
            self.assertNotIn(s, brief.lower())

    def test_all_three_prompts_get_only_the_blind_brief(self):
        seen = []

        def chat(system, user):
            seen.append(user)
            if system is oracle.JUDGE:
                return '{"true_prob_yes": 0.7, "confidence": 0.8, "reasoning": "r"}', 10
            return "case", 10
        c = {"question": "Q?", "event_title": "E", "end_date": "d", "description": "rules",
             "book_yes": book(0.1234, 0.5678), "book_no": book(0.4, 0.4)}
        r = oracle.evaluate(c, chat=chat)
        self.assertEqual((r.true_prob_yes, r.confidence, r.tokens), (0.7, 0.8, 30))
        self.assertTrue(all("0.1234" not in u and "0.5678" not in u for u in seen))

    def test_bad_judge_is_pending(self):
        self.assertIsNone(oracle.parse_judge("no json here"))
        self.assertIsNone(oracle.parse_judge('{"true_prob_yes": 1.4, "confidence": 0.8}'))


def opp(event="e1", p=0.75):
    return {"market_id": "m1", "condition_id": "c1", "event_id": event, "question": "Q?",
            "end_date": "2026-10-20T00:00:00Z", "token_yes": "ty", "token_no": "tn", "tick_size": "0.01",
            "neg_risk": False, "book_yes": book(0.48, 0.50), "book_no": book(0.49, 0.51),
            "oracle": {"true_prob_yes": p, "confidence": 0.8}}


class Lineage(unittest.TestCase):
    def setUp(self):
        self.pop = {"lineages": [L.new_lineage()], "burn": [], "halted": None}
        self.hist: list[dict] = []

    def test_allocate_opens_paper_position_and_event_lock(self):
        opened = L.allocate(self.pop, self.hist, [opp(), opp()], {}, "RID", NOW)
        self.assertEqual(len(opened), 1)
        self.assertAlmostEqual(opened[0]["cost_usd"], 3.96)
        self.assertAlmostEqual(self.pop["lineages"][0]["cash_usd"], 66.0 - 3.96)
        self.assertEqual(L.allocate(self.pop, self.hist, [opp()], {}, "RID2", NOW), [])

    def test_win_settles_at_one_dollar_a_share(self):
        L.allocate(self.pop, self.hist, [opp()], {}, "RID", NOW)
        out = L.settle(self.pop, self.hist, lambda _id: {"closed": True, "outcomePrices": '["1","0"]'}, NOW)
        h = self.hist[0]
        self.assertEqual(h["status"], "WON")
        self.assertAlmostEqual(h["proceeds_usd"], round(h["shares"], 2))
        self.assertEqual(self.pop["lineages"][0]["wins"], 1)
        self.assertTrue(out)

    def test_unresolved_stays_open_and_fetch_error_is_pending(self):
        L.allocate(self.pop, self.hist, [opp()], {}, "RID", NOW)
        L.settle(self.pop, self.hist, lambda _id: {"closed": False}, NOW)
        self.assertEqual(self.hist[0]["status"], "OPEN")

        def boom(_id):
            raise OSError("down")
        self.assertIn("PENDING", L.settle(self.pop, self.hist, boom, NOW)[0])
        self.assertEqual(self.hist[0]["status"], "OPEN")

    def test_take_profit_sells_at_0985(self):
        L.allocate(self.pop, self.hist, [opp()], {}, "RID", NOW)
        b = {"best_bid": 0.99, "bids": [(0.99, 1000.0)]}
        L.take_profit(self.pop, self.hist, {"ty": b}, NOW)
        self.assertEqual(self.hist[0]["status"], "SOLD")

    def test_mitosis_at_double(self):
        self.pop["lineages"][0]["cash_usd"] = 140.0
        out = L.life_cycle(self.pop, self.hist, {}, NOW)
        self.assertEqual(len(L.living(self.pop)), 2)
        parent, kid = self.pop["lineages"]
        self.assertAlmostEqual(parent["cash_usd"], 74.0)
        self.assertEqual((kid["parent_id"], kid["generation"], kid["cash_usd"]),
                         (parent["lineage_id"], 1, 66.0))
        self.assertTrue(any("MITOSIS" in o for o in out))

    def test_no_mitosis_when_cash_tied_up(self):
        self.pop["lineages"][0]["cash_usd"] = 60.0
        self.hist.append({"status": "OPEN", "lineage_id": self.pop["lineages"][0]["lineage_id"],
                          "token_id": "t", "shares": 100.0, "cost_usd": 50.0})
        L.life_cycle(self.pop, self.hist, {"t": 0.9}, NOW)            # equity 150, cash 60
        self.assertEqual(len(L.living(self.pop)), 1)

    def test_extinction_under_floor_and_population_halt(self):
        self.pop["lineages"][0]["cash_usd"] = 5.0
        out = L.life_cycle(self.pop, self.hist, {}, NOW)
        self.assertFalse(self.pop["lineages"][0]["alive"])
        self.assertTrue(self.pop["halted"])
        self.assertEqual(L.allocate(self.pop, self.hist, [opp()], {}, "RID", NOW), [])
        self.assertTrue(any("HALTED" in o for o in out))

    def test_burn_rule_halts_when_pnl_does_not_cover_burn(self):
        for i in range(10):
            self.hist.append({"status": "LOST", "closed_at": (NOW - timedelta(hours=1)).isoformat(),
                              "pnl_usd": 0.0, "lineage_id": "x"})
        L.record_burn(self.pop, 0.5, 1000, NOW - timedelta(hours=2))
        L.life_cycle(self.pop, self.hist, {}, NOW)
        self.assertIn("did not cover", self.pop["halted"])

    def test_burn_pending_never_halts_on_a_guess(self):
        for i in range(10):
            self.hist.append({"status": "LOST", "closed_at": NOW.isoformat(), "pnl_usd": -1.0, "lineage_id": "x"})
        L.record_burn(self.pop, None, 1000, NOW)
        L.life_cycle(self.pop, self.hist, {}, NOW)
        self.assertIsNone(self.pop["halted"])
        self.assertFalse(L.burn_total(self.pop)[1])

    def test_save_load_roundtrip(self):
        L.allocate(self.pop, self.hist, [opp()], {}, "RID", NOW)
        with tempfile.TemporaryDirectory() as d:
            L.save(self.pop, self.hist, Path(d))
            pop, hist = L.load(Path(d))
        self.assertEqual(pop, json.loads(json.dumps(self.pop)))
        self.assertEqual(len(hist), 1)


class PaperOnly(unittest.TestCase):
    """The capital bright line: nothing in this package can sign or send."""
    FORBIDDEN_IMPORTS = {"eth_account", "web3", "py_clob_client", "py_clob_client_v2"}

    def test_no_signing_or_order_libraries_imported(self):
        for f in PKG.rglob("*.py"):
            if "tests" in f.parts:
                continue
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                for n in names:
                    self.assertNotIn(n.split(".")[0], self.FORBIDDEN_IMPORTS, f"{f.name} imports {n}")

    def test_no_order_endpoint_or_private_key(self):
        for f in PKG.rglob("*.py"):
            if "tests" in f.parts:
                continue
            src = f.read_text(encoding="utf-8")
            for path in ('}/order', '"/order', "'/order"):    # a URL path, not a comment
                self.assertNotIn(path, src, f.name)
            self.assertNotIn("PRIVATE_KEY", src, f.name)
            self.assertNotIn("requests.post(f\"{C.CLOB", src, f.name)


if __name__ == "__main__":
    unittest.main()
