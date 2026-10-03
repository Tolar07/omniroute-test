import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "extract_to_file.py"
result = subprocess.run([sys.executable, str(TARGET)],
                       capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)