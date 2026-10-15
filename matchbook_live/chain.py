"""
Start the next cycle — the agent keeps itself running.

GitHub's cron never fired on the agent's repo its first night (the framework
measured its own crons 3-7 h late or dropped), so the workflow's last step runs
this: wait GAP_S, then ask GitHub to start the workflow again (workflow_dispatch
is the one event a job's own token may trigger). The hourly cron stays as a
backup starter; the concurrency group keeps it to one cycle at a time.

Stop the chain by disabling the workflow; MATCHBOOK_LIVE=0 or a STOP file only
stops orders.

    python -m matchbook_live.chain        (needs GH_TOKEN and REPO in the env)
"""
from __future__ import annotations

import os
import sys
import time

import requests

GAP_S = 300
WORKFLOW = "matchbook-agent.yml"


def request_next(token: str, repo: str, post=requests.post) -> int:
    r = post(f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches",
             headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
             json={"ref": "main", "inputs": {"mode": "once"}}, timeout=30)
    return r.status_code


def main() -> int:
    token, repo = os.getenv("GH_TOKEN", ""), os.getenv("REPO", "")
    if not (token and repo):
        print("chain: GH_TOKEN / REPO not set — next cycle NOT requested (hourly cron will start one)")
        return 1
    time.sleep(GAP_S)
    for attempt in range(3):
        try:
            code = request_next(token, repo)
        except requests.RequestException as e:
            code = f"{type(e).__name__}"
        print(f"chain: next cycle requested -> {code}", flush=True)
        if code == 204:
            return 0
        time.sleep(20 * (attempt + 1))
    return 1


if __name__ == "__main__":
    sys.exit(main())
