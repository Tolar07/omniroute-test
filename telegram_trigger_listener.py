#!/usr/bin/env python3
"""
telegram_trigger_listener.py — answers "is it that I trigger it from my
own end, from Telegram" directly: yes, this makes that possible.

ALSO self-triggers on a schedule, in the SAME process, so it doesn't
depend on you remembering to send anything OR on Windows Task Scheduler
actually firing correctly. This is the more reliable design: rather than
Task Scheduler starting a separate script at 22:00 (the mechanism that's
been ambiguous this whole time), the ONE always-on process that's
already alive and watching for your commands also watches the clock
itself, and announces to Telegram the moment it fires — "🕙 Scheduled
run starting now" — so you get an unmistakable signal every single
night, whether you're at your phone or not.

This is also the fastest way to settle the Task Scheduler question once
and for all. Right now you can't tell whether Task Scheduler is firing
and the pipeline is failing silently, or Task Scheduler itself never
fires at all. If you send /run_now from Telegram and the pipeline runs
correctly, that PROVES the pipeline itself works — meaning the problem
is 100% isolated to the scheduled trigger, not the code. If /run_now
also fails the same way, the problem is in the pipeline, not the
scheduler. One command, and the ambiguity is gone. Once the internal
auto-trigger below is running, you can retire Task Scheduler for this
job entirely rather than running two competing triggers.

Must run as a persistent, always-on process (same as your existing
Telegram bot) — it works by long-polling Telegram's getUpdates, so if
this process itself isn't running, it can't hear your commands OR fire
its own schedule either. Consider running it as the SAME process as
your existing bot rather than a second one, to avoid needing two things
to stay alive.

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
from datetime import datetime, date
from pathlib import Path

import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # only this chat can trigger anything
PIPELINE_SCRIPT = os.environ.get("PIPELINE_SCRIPT", "run_night_pipeline.py")
MARKER_DIR = Path(os.environ.get("PIPELINE_MARKER_DIR", "run_markers"))
POLL_INTERVAL_SEC = 3

# ---- Internal auto-trigger schedule ----
AUTO_TRIGGER_HOUR = int(os.environ.get("AUTO_TRIGGER_HOUR", "22"))
AUTO_TRIGGER_MINUTE = int(os.environ.get("AUTO_TRIGGER_MINUTE", "0"))
# -----------------------------------------

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


def run_pipeline_and_report(chat_id: str, trigger_source: str) -> None:
    """Shared by both /run_now and the internal auto-trigger, so both
    paths behave identically — same subprocess call, same reporting."""
    send_message(chat_id, f"⏳ {trigger_source} — starting the pipeline now. "
                           f"You'll get the usual stage-by-stage alerts and a summary at the end.")
    result = subprocess.run([sys.executable, PIPELINE_SCRIPT], capture_output=True, text=True)
    if result.returncode == 0:
        send_message(chat_id, "✅ Run finished — see the summary message above/below for stage details.")
    else:
        send_message(chat_id, f"❌ Run exited with an error (code {result.returncode}). "
                               f"Check logs/ for the full trace.")


def handle_run_now(chat_id: str) -> None:
    run_pipeline_and_report(chat_id, "Manual run triggered")


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


def already_ran_today(fired_marker: Path) -> bool:
    if not fired_marker.exists():
        return False
    return fired_marker.read_text(encoding="utf-8").strip() == date.today().isoformat()


def mark_fired_today(fired_marker: Path) -> None:
    fired_marker.write_text(date.today().isoformat(), encoding="utf-8")


def main() -> int:
    if not TELEGRAM_BOT_TOKEN or not AUTHORIZED_CHAT_ID:
        print("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.", file=sys.stderr)
        return 1

    print(f"[telegram_trigger] listening for commands from chat {AUTHORIZED_CHAT_ID}...")
    print(f"[telegram_trigger] auto-trigger armed for {AUTO_TRIGGER_HOUR:02d}:{AUTO_TRIGGER_MINUTE:02d} daily")
    offset = None
    fired_marker = MARKER_DIR / "auto_trigger_last_fired.txt"
    MARKER_DIR.mkdir(parents=True, exist_ok=True)

    while True:
        # --- Check the internal schedule first, every loop iteration ---
        now = datetime.now()
        if (now.hour, now.minute) >= (AUTO_TRIGGER_HOUR, AUTO_TRIGGER_MINUTE) and not already_ran_today(fired_marker):
            mark_fired_today(fired_marker)  # mark BEFORE running so a crash mid-run can't cause a duplicate fire
            send_message(
                AUTHORIZED_CHAT_ID,
                f"🕙 Scheduled run starting now ({now.strftime('%H:%M')}) — "
                f"this is the internal auto-trigger firing, not Task Scheduler. "
                f"If you've stopped relying on Task Scheduler for this job, this "
                f"message every night IS your confirmation the trigger fired."
            )
            run_pipeline_and_report(AUTHORIZED_CHAT_ID, "Scheduled run")

        # --- Then check for any manual commands ---
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