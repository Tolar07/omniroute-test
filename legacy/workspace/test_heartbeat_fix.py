#!/usr/bin/env python3
"""
Test script to verify the heartbeat fix works correctly.
"""

import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_heartbeat_selection():
    """Test that heartbeat_compact.py selects highest EV picks."""

    # Import the fixed function
    from olp_xdv_agent.olp_xdv.heartbeat_compact import generate_compact_heartbeat

    # Load today's board
    board_file = Path("olp_xdv_agent/olp_xdv/output/boards/board_2026-08-31.json")
    with open(board_file, 'r') as f:
        board_data = json.load(f)

    # Generate compact heartbeat
    result = generate_compact_heartbeat(board_data, "2026-08-31")

    print("Generated heartbeat:")
    # Print as ASCII to avoid encoding issues
    print(result.encode('ascii', errors='replace').decode('ascii'))
    print("\n" + "="*50 + "\n")

    # Verify it contains the highest EV pick (Osasuna v Getafe BTTS_NO at +0.0611 EV)
    if "Osasuna v Getafe" in result and "Both teams to score — no" in result and "EV: 6.1%" in result:
        print("SUCCESS: Heartbeat correctly shows highest EV pick (Osasuna v Getafe BTTS_No)")
        return True
    else:
        print("FAILURE: Heartbeat does not show highest EV pick")
        print("Looking for: Osasuna v Getafe, Both teams to score — no, EV: 6.1%")
        return False

if __name__ == "__main__":
    success = test_heartbeat_selection()
    sys.exit(0 if success else 1)