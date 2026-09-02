#!/usr/bin/env python3
"""
run_night_pipeline.py — wraps the existing stages (heartbeat, fetch,
engine, produce_bet, verify_results, notify) so a single stage failing
can't silently take down or corrupt the whole night's run, and so YOU
find out the moment something breaks instead of discovering it the next
morning.

This does not replace your existing stage scripts. It calls them. Fill in
the STAGES list below with your actual functions/subprocess calls.

Core behaviour:
  - Each stage runs in its own try/except. A failure is logged in full
    (traceback + timestamp) to logs/run_<date>.log, appended as one line
    to INCIDENTS.md (so patterns across days become visible instead of
    being re-discovered from scratch each time), and triggers an
    IMMEDIATE Telegram alert naming the exact stage and error.
  - Non-critical stage failures let the run continue (e.g. if enrichment
    intel fails, the board can still run with a NO DATA flag on that
    field per HR35 — never fabricate to cover the gap).
  - Critical stage failures (e.g. the engine itself) stop the run, but
    the alert and the completion marker still get written, so the
    watchdog and you both know exactly what happened and where.
  - A completion marker is ALWAYS written at the end, success or failure,
    recording per-stage status. This is what watchdog.py checks for.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import requests  # for Telegram alerts

# ---- CONFIGURE THIS ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
LOG_DIR = Path(os.environ.get("PIPELINE_LOG_DIR", "logs"))
INCIDENTS_MD = Path(os.environ.get("INCIDENTS_MD", "INCIDENTS.md"))
MARKER_DIR = Path(os.environ.get("PIPELINE_MARKER_DIR", "run_markers"))
# -------------------------


@dataclass
class Stage:
    name: str
    fn: Callable[[], None]
    critical: bool = True  # if True, a failure here stops the whole run


@dataclass
class StageResult:
    name: str
    status: str  # "ok" | "failed" | "skipped"
    error: str | None = None
    duration_sec: float = 0.0


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"run_{today_str()}.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    return log_path


def send_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram not configured — alert not sent: %s", message)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        # Telegram itself being down is not a reason to crash the pipeline --
        # log it hard so it's at least visible in the log file / next digest.
        logging.error("Telegram alert FAILED to send: %s | original message: %s", exc, message)


def append_incident(stage_name: str, error: str, log_path: Path) -> None:
    INCIDENTS_MD.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"- **{datetime.now().isoformat(timespec='seconds')}** — "
        f"`{stage_name}` failed: {error.splitlines()[0][:200]} "
        f"(full traceback: {log_path})\n"
    )
    with open(INCIDENTS_MD, "a", encoding="utf-8") as f:
        f.write(line)


def run_stage(stage: Stage, log_path: Path) -> StageResult:
    start = datetime.now()
    logging.info("=== STAGE START: %s ===", stage.name)
    try:
        stage.fn()
        duration = (datetime.now() - start).total_seconds()
        logging.info("=== STAGE OK: %s (%.1fs) ===", stage.name, duration)
        return StageResult(stage.name, "ok", duration_sec=duration)
    except Exception:
        tb = traceback.format_exc()
        duration = (datetime.now() - start).total_seconds()
        logging.error("=== STAGE FAILED: %s ===\n%s", stage.name, tb)
        append_incident(stage.name, tb, log_path)
        send_telegram(
            f"⚠️ *Night run — stage failed*\n"
            f"Stage: `{stage.name}`\n"
            f"Time: {datetime.now().strftime('%H:%M')}\n"
            f"Error: `{tb.splitlines()[-1][:300]}`\n"
            f"Attempting auto-remediation via Claude Code..."
        )

        try:
            from auto_remediate import attempt_remediation
            safe_to_retry = attempt_remediation(stage.name, tb)
        except Exception as remediation_exc:
            logging.error("auto_remediate itself failed: %s", remediation_exc)
            safe_to_retry = False

        if safe_to_retry:
            logging.info("=== RETRYING after auto-fix: %s ===", stage.name)
            try:
                stage.fn()
                duration = (datetime.now() - start).total_seconds()
                send_telegram(f"✅ *Auto-fixed and retried* — `{stage.name}` succeeded after an automatic fix.")
                return StageResult(stage.name, "ok", duration_sec=duration)
            except Exception:
                tb2 = traceback.format_exc()
                logging.error("=== STAGE FAILED AGAIN after auto-fix attempt: %s ===\n%s", stage.name, tb2)
                append_incident(f"{stage.name} (post-auto-fix retry)", tb2, log_path)

        send_telegram(
            f"❌ *Auto-remediation did not resolve it* — `{stage.name}` still failing. "
            f"Needs your attention. See INCIDENTS.md for what was tried.\n"
            f"{'This is CRITICAL — run stopped here.' if stage.critical else 'Non-critical — continuing.'}"
        )
        return StageResult(stage.name, "failed", error=tb, duration_sec=duration)


def write_marker(results: list[StageResult]) -> None:
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    marker_path = MARKER_DIR / f"run_{today_str()}.json"
    payload = {
        "date": today_str(),
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "stages": [
            {"name": r.name, "status": r.status, "duration_sec": r.duration_sec}
            for r in results
        ],
        "overall": "ok" if all(r.status == "ok" for r in results) else "degraded_or_failed",
    }
    marker_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def send_summary(results: list[StageResult]) -> None:
    lines = ["🌙 *Night run summary*"]
    for r in results:
        icon = {"ok": "✅", "failed": "❌", "skipped": "⏭"}[r.status]
        lines.append(f"{icon} {r.name} ({r.duration_sec:.0f}s)")
    overall_ok = all(r.status == "ok" for r in results)
    lines.append("\n*Result:* " + ("All stages OK." if overall_ok else "Some stages failed — see above / INCIDENTS.md."))
    send_telegram("\n".join(lines))


def main() -> int:
    log_path = setup_logging()

    # ---- FILL IN YOUR ACTUAL STAGES HERE ----
    # Import your real functions and list them in run order. Mark a stage
    # critical=False if the rest of the pipeline can meaningfully continue
    # without it (e.g. an optional intel enrichment step); leave the core
    # engine/produce_bet/notify stages critical=True.
    stages: list[Stage] = [
        # Stage("heartbeat_check", heartbeat_module.run, critical=True),
        # Stage("fetch_fixtures", fetch_module.run, critical=True),
        # Stage("fetch_odds", odds_module.run_with_fallback, critical=True),
        # Stage("engine", engine_module.run, critical=True),
        # Stage("verify_yesterday_results", lambda: os.system(
        #     "python verify_results.py --input yesterdays_fixtures.json --output verify_output.json"
        # ), critical=False),
        # Stage("produce_bet", produce_bet_module.run, critical=True),
        # Stage("notify_telegram", notify_module.send_board, critical=True),
    ]
    # ------------------------------------------

    if not stages:
        logging.error("No stages configured — edit the STAGES list in this file.")
        return 1

    results: list[StageResult] = []
    for stage in stages:
        result = run_stage(stage, log_path)
        results.append(result)
        if result.status == "failed" and stage.critical:
            logging.error("Critical stage '%s' failed — stopping run.", stage.name)
            break

    write_marker(results)
    send_summary(results)
    return 0 if all(r.status == "ok" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())