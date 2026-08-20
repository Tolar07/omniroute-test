import subprocess
import sys

result = subprocess.run([sys.executable, r'c:\Users\Motunrayo\omniroute test\extract_to_file.py'],
                       capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)