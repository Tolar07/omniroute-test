import re
import sys
from collections import defaultdict

def parse_fixtures_output(filename):
    """Parse the fixtures agent output and count verified fixtures by league."""

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the verified fixtures section
    lines = content.split('\n')

    in_verified_section = False
    current_league = None
    league_counts = defaultdict(int)
    fixtures_by_league = defaultdict(list)

    for line in lines:
        # Check if we're entering the verified fixtures section
        if 'FOOTBALL FIXTURES - 2026-09-06  (verified)' in line:
            in_verified_section = True
            continue

        # Check if we're leaving the verified fixtures section
        if in_verified_section and line.strip() == '' and current_league is not None:
            # Blank line after league content - end of current league
            continue

        if in_verified_section:
            # Check for league header (starts with 2 spaces, then league name, then count in parentheses)
            league_match = re.match(r'^  (.+?)\s+\((\d+)\)', line)
            if league_match:
                current_league = league_match.group(1).strip()
                count = int(league_match.group(2))
                # Don't trust the count from header, we'll count verified ourselves
                league_counts[current_league] = 0  # Reset to count verified only
                continue

            # Check for fixture lines (indented with 6 spaces, with team names and [verified] or [UNVERIFIED])
            if line.startswith('      '):  # 6 spaces
                # This is a fixture line
                if '[verified]' in line:
                    if current_league:
                        league_counts[current_league] += 1
                        # Extract the fixture info
                        fixture_match = re.match(r'^      (.+?)\s+\[FlashScore\s+\|\s+[\d\-:TZ]+\s+\|\s+(verified|UNVERIFIED)\]', line)
                        if fixture_match:
                            fixture_text = fixture_match.group(1).strip()
                            status = fixture_match.group(2)
                            fixtures_by_league[current_league].append((fixture_text, status))
                elif '[UNVERIFIED]' in line:
                    # Still count for debugging but not for verified total
                    if current_league:
                        pass  # We don't count unverified
                continue

            # If we hit a line that's not a fixture and not blank, we might be done with this league
            if line.strip() != '' and not line.startswith(' ') and current_league:
                # New section or end of fixtures
                current_league = None

    return dict(league_counts), dict(fixtures_by_league)

if __name__ == '__main__':
    # Use the most recent output file
    import glob
    import os

    task_dir = r'C:\Users\MOTUNR~1\AppData\Local\Temp\claude\c--Users-Motunrayo-omniroute-test\0ed82d02-8fc1-4eac-912f-05494eb40146\tasks'
    output_files = glob.glob(os.path.join(task_dir, '*.output'))

    if not output_files:
        print("No output files found")
        sys.exit(1)

    # Get the most recently modified file
    latest_file = max(output_files, key=os.path.getmtime)
    print(f"Parsing: {latest_file}")
    print()

    league_counts, fixtures_by_league = parse_fixtures_output(latest_file)

    print("VERIFIED FIXTURES BY LEAGUE:")
    print("=" * 40)
    total_verified = 0
    for league in sorted(league_counts.keys()):
        count = league_counts[league]
        total_verified += count
        print(f"{league}: {count}")

    print()
    print(f"TOTAL VERIFIED FIXTURES: {total_verified}")

    # Show some examples
    print()
    print("SAMPLE VERIFIED FIXTURES:")
    print("-" * 30)
    for league in sorted(fixtures_by_league.keys())[:3]:  # First 3 leagues
        print(f"{league}:")
        for fixture, status in fixtures_by_league[league][:3]:  # First 3 fixtures
            print(f"  {fixture} [{status}]")
        print()