import subprocess
import sys

result = subprocess.run([sys.executable, r'c:\Users\Motunrayo\omniroute test\extract_teams.py'],
                       capture_output=True, text=True)
print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")