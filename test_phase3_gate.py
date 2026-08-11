import sys
import os
sys.path.insert(0, r"C:\Users\Motunrayo\omniroute test\olp_xdv_agent")
os.chdir(r"C:\Users\Motunrayo\omniroute test\olp_xdv_agent")
from olp_xdv.clv.phase3_gate import gate_status_for_dashboard, evaluate_gate, sign_off_gate, get_signed_gate, can_deploy_capital, revoke_sign_off
print("Testing Phase 3 Gate...")

# Test 1: Evaluate gate
print("\n1. Evaluating gate...")
gate = evaluate_gate()
for k, v in gate.to_dict().items():
    print(f"  {k}: {v}")

# Test 2: Dashboard status
print("\n2. Dashboard status...")
dash = gate_status_for_dashboard()
for k, v in dash.items():
    print(f"  {k}: {v}")

# Test 3: Can deploy capital
print("\n3. Can deploy capital...")
auth, reason = can_deploy_capital()
print(f"  authorized: {auth}, reason: {reason}")

# Test 4: Sign off (if gate met)
if gate.gate_met:
    print("\n4. Signing off gate...")
    try:
        signed = sign_off_gate("Test Architect")
        for k, v in signed.to_dict().items():
            print(f"  {k}: {v}")
    except RuntimeError as e:
        print(f"  Error: {e}")
else:
    print("\n4. Gate not met - skipping sign off")

# Test 5: Check signed gate
print("\n5. Signed gate record...")
signed_gate = get_signed_gate()
if signed_gate:
    for k, v in signed_gate.to_dict().items():
        print(f"  {k}: {v}")
else:
    print("  No signed gate record")

# Test 6: Can deploy after sign-off
print("\n6. Can deploy capital after sign-off...")
auth, reason = can_deploy_capital()
print(f"  authorized: {auth}, reason: {reason}")

print("\nAll tests completed!")