#!/usr/bin/env python3
"""
telegram_trigger_listener.py — answers "is it that I trigger it from my
own end, from Telegram" directly: yes, this makes that possible.

This is also the fastest way to settle the Task Scheduler question once
and for all. Right now you can't tell whether Task Scheduler is firing
and the pipeline is failing silently, or Task Scheduler itself never
fires at all. If you send /run_now from Telegram and the pipeline runs
correctly, that PROVES the pipeline itself works — meaning the problem
is 100% isolated to the scheduled trigger, not the code. If /run_now
also fails the same way, the problem is in the pipeline, not the
scheduler. One command, and the ambiguity is gone.

Must run as a persistent, always-on process (same as your existing
Telegram bot) — it works by long-polling Telegram's getUpdates, so if
this process itself isn't running, it can't hear your commands either.
Consider running it as the SAME process as your existing bot rather
than a second one, to avoid needing two things to stay alive.

Commands:
    /run_now  — triggers run_night_pipeline.py immediately, replies when done
    /status   — reports today's completion marker without running anything
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # only this chat can trigger anything
PIPELINE_SCRIPT = os.environ.get("PIPELINE_SCRIPT", "run_night_pipeline.py")
MARKER_DIR = Path(os.environ.get("PIPELINE_MARKER_DIR", "run_markers"))
POLL_INTERVAL_SEC = 3

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(chat_id: str, text: str) -> None:
    try:
        requests.post(f"{API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram_trigger] failed to send message: {exc}", file=sys.stderr)


def get_updates(offset: int | None) -> list[dict]:
    params = {"timeout": 20}
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=25)
        return resp.json().get("result", [])
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram_trigger] getUpdates failed: {exc}", file=sys.stderr)
        return []


def handle_run_now(chat_id: str) -> None:
    send_message(chat_id, "⏳ Manual run triggered — starting the pipeline now. "
                           "You'll get the usual stage-by-stage alerts and a summary at the end.")
    # Runs in the foreground deliberately -- this listener process is
    # dedicated to being the trigger, not doing other work concurrently.
    # If you want it non-blocking, launch with subprocess.Popen instead
    # and accept that a second /run_now while one is in flight could
    # overlap -- foreground keeps that impossible.
    result = subprocess.run([sys.executable, PIPELINE_SCRIPT], capture_output=True, text=True)
    if result.returncode == 0:
        send_message(chat_id, "✅ Manual run finished — see the summary message above/below for stage details.")
    else:
        send_message(chat_id, f"❌ Manual run exited with an error (code {result.returncode}). "
                               f"Check logs/ for the full trace.")


def handle_status(chat_id: str) -> None:
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    marker_path = MARKER_DIR / f"run_{today}.json"
    if not marker_path.exists():
        send_message(chat_id, f"No completion marker for {today} yet — either it hasn't run, "
                               f"or it's still in progress. Use /run_now to trigger it manually.")
        return
    payload = json.loads(marker_path.read_text(encoding="utf-8"))
    lines = [f"Status for {today}: {payload.get('overall', 'unknown')}"]
    for s in payload.get("stages", []):
        lines.append(f"  {s['status']}: {s['name']} ({s['duration_sec']:.0f}s)")
    send_message(chat_id, "\n".join(lines))


def main() -> int:
    if not TELEGRAM_BOT_TOKEN or not AUTHORIZED_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        return 1

    print(f"[telegram_trigger] listening for commands from chat {AUTHORIZED_CHAT_ID}...")
    offset = None

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "").strip()

            if chat_id != AUTHORIZED_CHAT_ID:
                # Deliberately silent — don't even acknowledge an
                # unauthorized sender, don't confirm this bot exists to them.
                continue

            if text == "/run_now":
                handle_run_now(chat_id)
            elif text == "/status":
                handle_status(chat_id)

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    sys.exit(main())