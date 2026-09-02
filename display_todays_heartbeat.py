#!/usr/bin/env python3
"""
Display today's heartbeat in the expected Telegram format.
Since we don't have today's board yet (latest is 2026-08-31),
this shows what today's heartbeat would look like based on the format.
"""

import sys
from datetime import datetime

def generate_sample_heartbeat():
    """Generate a sample heartbeat for today (2026-09-02)"""

    # Get today's date for display
    today = datetime.now()
    weekday = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][today.weekday()]
    month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][today.month-1]
    date_label = f'{weekday} {today.day:02d} {month} {today.year}'

    # Sample leagues and fixtures that might be in today's slate
    sample_data = [
        {
            "league": "Premier League",
            "fixture": "Man City v Liverpool",
            "pick": "Man City to win",
            "probability": 0.58,
            "edge": 0.042,
            "sportybet_price": 1.65,
            "verification": "Pending Review"
        },
        {
            "league": "La Liga",
            "fixture": "Real Madrid v Barcelona",
            "pick": "Over 2.5 goals",
            "probability": 0.62,
            "edge": 0.038,
            "sportybet_price": 1.72,
            "verification": "Pending Review"
        },
        {
            "league": "Bundesliga",
            "fixture": "Bayern Munich v Dortmund",
            "pick": "BTTS - Yes",
            "probability": 0.55,
            "edge": 0.035,
            "sportybet_price": 1.80,
            "verification": "Pending Review"
        },
        {
            "league": "Serie A",
            "fixture": "Inter Milan v AC Milan",
            "pick": "Draw",
            "probability": 0.32,
            "edge": 0.028,
            "sportybet_price": 3.20,
            "verification": "Pending Review"
        }
    ]

    # Generate heartbeat format
    lines = []
    lines.append("[TARGET] OLP XDV HEARTBEAT")
    lines.append(f"[DATE]  {date_label}")
    lines.append("")

    for item in sample_data:
        prob_pct = int(item['probability'] * 100)
        edge_pct = int(item['edge'] * 100)

        lines.append(f"[SOCCER]  {item['league']}")
        lines.append(f"[CLOCK]  ??:??   {item['fixture']}")
        lines.append(f"[IDEA]  Pick: {item['pick']} ({prob_pct}%)")
        lines.append(f"[CHART_UP]  Edge: +{edge_pct}%")
        lines.append(f"[POUND]  SportyBet: {item['sportybet_price']:.2f}")
        lines.append(f"[WARNING]  Verification: {item['verification']}")
        lines.append("")

    # Add footer
    lines.append("📊 4 fixtures across 4 leagues")
    lines.append("🎯 Avg edge: +0.036 (3.6%)")
    lines.append("⏰ Next verification: ~22:00 UTC (dynamic timing)")

    return "\n".join(lines)

if __name__ == "__main__":
    try:
        heartbeat = generate_sample_heartbeat()
        # Handle Windows console encoding
        if sys.platform == "win32…….”

        # Replace emojis for Windows console compatibility
        heartbeat = heartbeat.replace("📊", "[CHART]")
        heartbeat = heartbeat.replace("🎯", "[TARGET]")
        heartbeat = heartbeat.replace("⏰", "[CLOCK]")
        print(heartbeat)
    except Exception as e:
        print(f"Error generating heartbeat: {e}")
        # Fallback simple output
        print("OLP XDV HEARTBEAT")
        print(f"[DATE]  {datetime.now().strftime('%a %d %b %Y')}")
        print("")
        print("[SOCCER]  Premier League")
        print("[CLOCK]  ??:??   Man City v Liverpool")
        print("[IDEA]  Pick: Man City to win (58%)")
        print("[CHART_UP]  Edge: +4%")
        print("[POUND]  SportyBet: 1.65")
        print("[WARNING]  Verification: Pending Review")