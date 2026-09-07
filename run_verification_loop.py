#!/usr/bin/env python3
"""
Verification loop agent for fixtures
Continuously verifies fixture results and applies enhancements
"""
import subprocess
import time
import json
import os
from datetime import datetime
from pathlib import Path

def run_verification_on_fixtures(fixtures_data=None):
    """Run verification on the latest fixtures data"""
    try:
        # If we have fixtures data, pass it to verification
        if fixtures_data is not None:
            # Create a temporary file with the fixtures data
            temp_file = Path('./temp_fixtures.json')
            with open(temp_file, 'w') as f:
                json.dump(fixtures_data, f)

            # Run verification script with the data
            result = subprocess.run(
                ['python', '-c', f"""
import json
import sys
sys.path.insert(0, 'olp_xdv_agent/olp_xdv')
from fixtures_agent import *
# Load fixtures and run verification
with open('temp_fixtures.json', 'r') as f:
    fixtures = json.load(f)
# Apply verification (this modifies fixtures in-place)
_apply_verification(fixtures)
print(json.dumps({{
    'verified_count': sum(1 for f in fixtures if f.get('verified', False)),
    'total_count': len(fixtures),
    'timestamp': '{datetime.now().isoformat()}',
    'fixtures': fixtures
}}))
"""],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__)
            )

            # Clean up temp file
            if temp_file.exists():
                temp_file.unlink()

        else:
            # Just run the fixtures agent with verification
            result = subprocess.run(
                ['python', 'fixtures_agent.py'],
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), 'olp_xdv_agent', 'olp_xdv')
            )

        if result.returncode != 0:
            print(f"[{datetime.now()}] ERROR in verification: {result.stderr}")
            return None

        return result.stdout
    except Exception as e:
        print(f"[{datetime.now()}] EXCEPTION in verification: {e}")
        return None

def enhance_fixtures(fixtures_data):
    """Apply enhancements to fixtures data"""
    enhancements = []

    # Add enhancement: timestamp enrichment
    for fixture in fixtures_data:
        if 'fetched_at' not in fixture:
            fixture['fetched_at'] = datetime.now().isoformat() + "Z"
            enhancements.append(f"Added timestamp to {fixture.get('home', '?')} vs {fixture.get('away', '?')}")

    # Add enhancement: confidence scoring based on verification
    for fixture in fixtures_data:
        # Simple confidence: verified fixtures get higher confidence
        fixture['confidence'] = 'high' if fixture.get('verified', False) else 'low'
        if fixture.get('verified', False):
            enhancements.append(f"Set high confidence for {fixture.get('home', '?')} vs {fixture.get('away', '?')}")
        else:
            enhancements.append(f"Set low confidence for {fixture.get('home', '?')} vs {fixture.get('away', '?')}")

    return enhancements

def save_verification_results(data, filename):
    """Save verification results to file"""
    state_dir = Path('./state')
    state_dir.mkdir(exist_ok=True)
    with open(state_dir / filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_latest_fixtures():
    """Load the latest fixtures data from state"""
    state_dir = Path('./state')
    if not state_dir.exists():
        return None

    # Find the most recent fixtures output file
    fixture_files = list(state_dir.glob('fixtures_output_*.json'))
    if not fixture_files:
        return None

    # Sort by modification time, get latest
    latest_file = max(fixture_files, key=lambda f: f.stat().st_mtime)
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
            return data.get('output')  # Return the raw output for now
    except Exception as e:
        print(f"[{datetime.now()}] Error loading latest fixtures: {e}")
        return None

def main():
    print(f"[{datetime.now()}] Starting verification loop")
    print(f"[{datetime.now()}] Press Ctrl+C to stop")

    verification_count = 0

    try:
        while True:
            verification_count += 1
            print(f"\n[{datetime.now()}] === Verification Cycle #{verification_count} ===")

            # Try to load latest fixtures data
            latest_output = load_latest_fixtures()

            if latest_output:
                print(f"[{datetime.now()}] Found latest fixtures data, running verification...")
                # Run verification on the data
                verification_result = run_verification_on_fixtures(latest_output)

                if verification_result is not None:
                    # Save verification results
                    save_verification_results({
                        'timestamp': datetime.now().isoformat(),
                        'verification_count': verification_count,
                        'result': verification_result
                    }, f'verification_result_{verification_count}.json')

                    print(f"[{datetime.now()}] Verification completed successfully")
                    # Show brief result
                    lines = verification_result.strip().split('\n')
                    if lines:
                        print(f"[{datetime.now()}] Verification output preview: {lines[0][:100]}...")
                else:
                    print(f"[{datetime.now()}] Verification failed")
            else:
                print(f"[{datetime.now()}] No fixtures data available yet, running fresh fixtures agent...")
                # Run fresh fixtures agent
                verification_result = run_verification_on_fixtures()

                if verification_result is not None:
                    save_verification_results({
                        'timestamp': datetime.now().isoformat(),
                        'verification_count': verification_count,
                        'result': verification_result
                    }, f'verification_result_{verification_count}.json')

                    print(f"[{datetime.now()}] Fresh verification completed successfully")
                else:
                    print(f"[{datetime.now()}] Fresh verification failed")

            # Apply enhancements if we have data
            if latest_output:
                print(f"[{datetime.now()}] Applying enhancements...")
                # In a full implementation, we would parse the fixtures and apply enhancements
                # For now, we'll just log that enhancements would be applied
                enhancements = ["Would apply timestamp enrichment", "Would apply confidence scoring"]
                print(f"[{datetime.now()}] Enhancements to apply: {len(enhancements)} items")

            # Wait before next verification cycle (2 minutes)
            print(f"[{datetime.now()}] Waiting 120 seconds until next verification...")
            time.sleep(120)

    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Received interrupt signal, shutting down verification loop...")
    except Exception as e:
        print(f"\n[{datetime.now()}] Unexpected error in verification loop: {e}")
    finally:
        print(f"[{datetime.now()}] Verification loop stopped")

if __name__ == "__main__":
    main()