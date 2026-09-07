import os
import subprocess

# Load the API key from the olp_xdv .env file
env_path = r"c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv\.env"
with open(env_path) as f:
    for line in f:
        if line.startswith("API_FOOTBALL_KEY="):
            os.environ["APIFOOTBALL_KEY"] = line.strip().split("=", 1)[1]
            break

# Run the fixtures agent
result = subprocess.run(["python", "fixtures_agent_final.py"],
                       cwd=r"c:\Users\Motunrayo\omniroute test\olp_xdv_agent\olp_xdv",
                       capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)