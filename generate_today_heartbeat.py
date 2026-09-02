#!/usr/bin/env python3
"""
Generate today's heartbeat (2026-09-02) based on the latest board data.
"""

import json
import sys
import os
from datetime import date
from collections import defaultdict
import glob

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_latest_board():
    """Get the most recent board file."""
    board_files = glob.glob('olp_xdv_agent/olp_xdv/output/boards/board_*.json')
    if not board_files:
        return None
    latest_board = max(board_files, key=lambda f: os.path.getmtime(f))
    return latest_board

def load_board_data(board_path):
    """Load board data from JSON file."""
    try:
        with open(board_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading board: {e}")
        return None

def generate_heartbeat_for_date(target_date):
    # Encode output for Windows console compatibility
    if sys.platform == "win32":
        # Replace emojis with ASCII equivalents for Windows console
        heartbeat = heartbeat.replace("🎯", "[TARGET]")
        heartbeat = heartbeat.replace("📅", "[DATE]")
        heartbeat = heartbeat.replace("⚽", "[SOCCER]")
        heartbeat = heartbeat.replace("🕐", "[CLOCK]")
        heartbeat = heartbeat.replace("💡", "[IDEA]")
        heartbeat = heartbeat.replace("📈", "[CHART_UP]")
        heartbeat = heartbeat.replace("💷", "[POUND]")
        heartbeat = heartbeat.replace("⚠️", "[WARNING]")
    print(heartbeat)

if __name__ == "__main__":
    target_date = "2026-09-02"  # Today's date
    heartbeat = generate_heartbeat_for_date(target_date)
    # Encode output for Windows console compatibility
    if sys.platform == "win32":
        # Replace emojis with ASCII equivalents for Windows console
        heartbeat = heartbeat.replace("🎯", "[TARGET]")
        heartbeat = heartbeat.replace("📅", "[DATE]")
        heartbeat = heartbeat.replace("⚽", "[SOCCER]")
        heartbeat = heartbeat.replace("🕐", "[CLOCK]")
        heartbeat = heartbeat.replace("💡", "[IDEA]")
        heartbeat = heartbeat.replace("📈", "[CHART_UP]")
        heartbeat = heartbeat.replace("💷", "[POUND]")
        heartbeat = heartbeat.replace("⚠️", "[WARNING]")
    print(heartbeat)