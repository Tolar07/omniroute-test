#!/usr/bin/env python3
"""Final execution script to send heartbeat and run sync"""

import subprocess
import sys
import os

def run_command(cmd, description):
    print(f"\n{'='*50}")
    print(f"Executing: {description}")
    print(f"Command: {cmd}")
    print('='*50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"Error executing command: {e}")
        return False

def main():
    print("OLP XDV Heartbeat Final Execution")
    print("==================================")
    
    # Change to project directory
    os.chdir(r'C:\Users\Motunrayo\omniroute test')
    
    # Task 1: Send today's heartbeat to Telegram
    success1 = run_command(
        "python olp_xdv_agent/olp_xdv/send_heartbeat.py",
        "Send today's heartbeat to Telegram"
    )
    
    # Task 2: Run vault-memory sync (push)
    success2 = run_command(
        "node olp_xdv_agent/olp_xdv/.claude/scripts/hooks/vault-memory-sync.js push",
        "Push memory to vault (HR54 compliance)"
    )
    
    # Summary
    print(f"\n{'='*50}")
    print("FINAL EXECUTION SUMMARY")
    print('='*50)
    print(f"Telegram Send: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"Vault-Memory Sync: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 ALL TASKS COMPLETED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  Some tasks failed - check output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())