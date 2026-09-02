import sys, json
sys.path.insert(0, r'C:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv')
from output.heartbeat import select_top_heartbeats, render_heartbeat_telegram, HeartbeatFixture, BoardFixture
with open('olp_xdv_agent/olp_xdv/output/boards/board_2026-09-02.json') as f:
    data = json.load(f)

# Convert to BoardFixture objects
board_list = [BoardFixture(**f) for f in data['board']]
heartbeats = select_top_heartbeats(board_list, target_date='2026-09-02', top_n=5, min_edge=0.0)
for hb in heartbeats:
    print(render_heartbeat_telegram(hb))
    print()