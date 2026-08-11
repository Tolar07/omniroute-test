import sys
import os
from pathlib import Path

AGENT = Path(__file__).parent / "olp_xdv_agent"
sys.path.insert(0, str(AGENT))
os.chdir(str(AGENT))

TESTS = [
    AGENT / "olp_xdv" / "tests" / "closing_capture_test.py",
    AGENT / "olp_xdv" / "tests" / "clv_grade_test.py",
    AGENT / "olp_xdv" / "tests" / "telegram_commands_test.py",
    AGENT / "olp_xdv" / "tests" / "telegram_webhook_test.py",
    AGENT / "olp_xdv" / "tests" / "gate_telemetry_test.py",
]

for t in TESTS:
    if not t.exists():
        print(f"\nSKIP (missing): {t.name}")
        continue
    print(f"\n{'='*70}\nRUNNING: {t.name}\n{'='*70}")
    g = {"__file__": str(t), "__name__": "__main__"}
    exec(open(t, encoding="utf-8").read(), g)
    print(f"\n[tests/{t.name} PASSED]")

print("\nALL TEST SUITES COMPLETED SUCCESSFULLY")
