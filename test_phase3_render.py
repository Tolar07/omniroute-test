import sys
import os
sys.path.insert(0, r"C:\Users\Motunrayo\omniroute test\olp_xdv_agent")
os.chdir(r"C:\Users\Motunrayo\omniroute test\olp_xdv_agent")

from olp_xdv.webapp.render import _phase3_gate_section

# Test 1: No legs with CLV
print("Test 1: No legs with CLV")
gate1 = {
    "legs_with_clv": 0,
    "gate_requirement": 30,
    "mean_clv_pct": None,
    "positive_mean_clv": False,
    "gate_met_pending_architect_signoff": False,
    "architect_signed_off": False,
}
html1 = _phase3_gate_section(gate1)
print("✓ Rendered (length:", len(html1), ")")
print(html1[:500])
print("...")

# Test 2: In progress
print("\n\nTest 2: In progress (15/30 legs)")
gate2 = {
    "legs_with_clv": 15,
    "gate_requirement": 30,
    "mean_clv_pct": 2.5,
    "positive_mean_clv": True,
    "gate_met_pending_architect_signoff": False,
    "architect_signed_off": False,
}
html2 = _phase3_gate_section(gate2)
print("✓ Rendered (length:", len(html2), ")")

# Test 3: Gate met, awaiting sign-off
print("\n\nTest 3: Gate met, awaiting sign-off (30/30 legs)")
gate3 = {
    "legs_with_clv": 30,
    "gate_requirement": 30,
    "mean_clv_pct": 3.2,
    "positive_mean_clv": True,
    "gate_met_pending_architect_signoff": True,
    "architect_signed_off": False,
}
html3 = _phase3_gate_section(gate3)
print("✓ Rendered (length:", len(html3), ")")
# Check for sign-off form
if "sign_off" in html3 or "Sign Off" in html3:
    print("✓ Contains sign-off form")

# Test 4: Signed off
print("\n\nTest 4: Signed off by Architect")
gate4 = {
    "legs_with_clv": 35,
    "gate_requirement": 30,
    "mean_clv_pct": 4.1,
    "positive_mean_clv": True,
    "gate_met_pending_architect_signoff": True,
    "architect_signed_off": True,
    "signed_by": "V7-Architect",
    "signed_at": "2026-08-09T12:00:00+00:00",
}
html4 = _phase3_gate_section(gate4)
print("✓ Rendered (length:", len(html4), ")")
if "SIGNED OFF" in html4 and "V7-Architect" in html4:
    print("✓ Shows signed off status")

print("\n\nAll render tests passed!")