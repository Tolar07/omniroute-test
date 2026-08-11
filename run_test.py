import sys
import tempfile
import os
from pathlib import Path

AGENT = Path(__file__).parent / "olp_xdv_agent"
sys.path.insert(0, str(AGENT))
os.chdir(str(AGENT))

# Run the telegram test
_g = {"__file__": str(AGENT / "olp_xdv" / "tests" / "telegram_commands_test.py"),
      "__name__": "__main__"}
exec(open(AGENT / "olp_xdv" / "tests" / "telegram_commands_test.py", encoding="utf-8").read(), _g)

print("Test completed successfully!")