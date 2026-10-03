import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "extract_teams.py"
result = subprocess.run([sys.executable, str(TARGET)],
                       capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")