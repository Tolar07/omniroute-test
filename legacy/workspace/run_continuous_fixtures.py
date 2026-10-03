#!/usr/bin/env python3
"""
Continuous fixtures runner with verification loop
Runs the fixtures agent continuously and verifies results
"""
import subprocess
import time
import json
import os
from datetime import datetime
from pathlib import Path

def run_fixtures_agent():
    """Run the fixtures agent and return parsed output"""
    try:
        # Run fixtures agent for today
        result = subprocess.run(
            ['python', 'fixtures_agent.py'],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), 'olp_xdv_agent', 'olp_xdv')
        )

        if result.returncode != 0:
            print(f"[{datetime.now()}] ERROR running fixtures agent: {result.stderr}")
            return None

        return result.stdout
    except Exception as e:
        print(f"[{datetime.now()}] EXCEPTION running fixtures agent: {e}")
        return None

def save_state(data, filename):
    """Save state to file for persistence"""
    state_dir = Path('./state')
    state_dir.mkdir(exist_ok=True)
    with open(state_dir / filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_state(filename):
    """Load state from file"""
    try:
        with open(Path('./state') / filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[{datetime.now()}] Error loading {filename}: {e}")
        return None

def main():
    print(f"[{datetime.now()}] Starting continuous fixtures verification system")
    print(f"[{datetime.now()}] Press Ctrl+C to stop")

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            print(f"\n[{datetime.now()}] === Cycle #{cycle_count} ===")

]")

            # Run fixtures agent
            output = run_fixtures_agent()

            if output is not None:
                # Save raw output for debugging
                save_state({
                    'timestamp': datetime.now().isoformat(),
                    'output': output,
                    'cycle': cycle_count
                }, f'fixtures_output_{cycle_count}.json')

                print(f"[{datetime.now()}] Fixtures agent completed successfully")
                # Print last few lines of output to show progress
                lines = output.strip().split('\n')
                if len(lines) > 5:
                    print(f"[{datetime.now()}] Last 5 lines of output:")
                    for line in lines[-5:]:
                        print(f"  {line}")
                else:
                    print(f"[{datetime.now()}] Output: {output[:200]}...")
            else:
                print(f"[{datetime.now()}] Fixtures agent failed")

            # Wait before next run (5 minutes)
            print(f"[{datetime.now()}] Waiting 300 seconds until next run...")
            time.sleep(300)

    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        print(f"\n[{datetime.now()}] Unexpected error: {e}")
    finally:
        print(f"[{datetime.now()}] Continuous fixtures system stopped")

if __name__ == "__main__":
    main()