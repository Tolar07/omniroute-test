#!/usr/bin/env python3
import sys
import json
sys.path.insert(0, 'olp_xdv_agent/olp_xdv')

from output.heartbeat import select_heartbeat_fixture, select_top_heartbeats
from output.produce_bet import BoardFixture
from verification.id403 import VerificationResult, Tier

# Simple mock objects for testing
class MockProbs:
    def __init__(self, data):
        self.__dict__.update(data)
        self.home_team = "Home Team"
        self.away_team = "Away Team"

# Load today's board
with open('olp_xdv_agent/olp_xdv/output/boards/board_2026-09-02.json', 'r') as f:
    data = json.load(f)

# Convert to BoardFixture objects
board = []
for entry in data['board']:
    if entry.get('probs'):
        probs = MockProbs(entry['probs'])
        verification = VerificationResult(
            tier=Tier.SINGLE_SOURCE,
            value=None,
            factors={},
            note="SINGLE-SOURCE — one source only, no capital on this alone"
        )  # All are SINGLE_SOURCE from scan

        bf = BoardFixture(
            fixture=entry['fixture'],
            probs=probs,
            verification=verification,
            on_deploy_shortlist=False,
            mes_trigger_price=None,
            rejection_reason=None,
            best_market=entry.get('best_market'),
            best_price=None,
            best_bookmaker=None,
            best_n_books=0,
            best_mes_ev=entry.get('best_mes_ev'),
            best_model_prob=entry.get('best_model_prob'),
            kickoff_date=entry.get('kickoff_date'),
            kickoff_utc=entry.get('kickoff_utc'),
            elo_probs=None,
            engine_divergence=None
        )
        board.append(bf)

print(f"Loaded {len(board)} fixtures for 2026-09-02")

# Try to select heartbeat
heartbeat = select_heartbeat_fixture(board, target_date='2026-09-02')
if heartbeat:
    print('\nHeartbeat selected:')
    print(f'Fixture: {heartbeat.fixture}')
    print(f'Pick: {heartbeat.pick} ({heartbeat.probability*100:.0f}%)')
    print(f'Edge: {heartbeat.edge*100:+.1f}%')
    print(f'Price: {heartbeat.price or "N/A"}')
    print(f'Verification: {"Passed" if heartbeat.verification_passed else "Failed"}')
    print(f'Lineage ID: {heartbeat.lineage_id}')
    print(f'Generation: {heartbeat.generation}')
else:
    print('\nNo heartbeat selected')

# Try top heartbeats for lineage system
top_heartbeats = select_top_heartbeats(board, target_date='2026-09-02', top_n=3)
print(f'\nTop {len(top_heartbeats)} heartbeats for lineage:')
for i, hb in enumerate(top_heartbeats):
    print(f'{i+1}. {hb.fixture} - {hb.pick} ({hb.probability*100:.0f}%, Edge: {hb.edge*100:+.1f}%)')

# Check what the lineage system would do
print(f'\nCurrent living lineages: 3 (from lineage.json)')
print('For AI survival to work, we need:')
print('- Deploy-eligible fixtures (softness A/B)')
print('- Positive edge values')
print('- Verified fixtures')
print('')
print('Today\'s reality:')
print('- All fixtures softness tier C (scan-only)')
print('- Best edge: +3.0% (Hoffenheim v Dortmund)')
print('- All fixtures SINGLE-SOURCE verification')
print('- No deploy-eligible calls')