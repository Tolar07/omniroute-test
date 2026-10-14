"""
Telegram debriefs for the Matchbook agent (bot token + chat id from the runner's secrets).

  - at once, when a run has news: a bet placed or settled, mitosis, a death, a
    halt, an order or account error, or the mode changing (DRY <-> LIVE)
  - once a day, the first run at or after DIGEST_HOUR_UTC: the full heartbeat

Quiet runs send nothing. No token -> nothing is sent and the heartbeat says so.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Callable

import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DIGEST_HOUR_UTC = 7            # 08:00 BST / 07:00 GMT
NEWS = ("OPEN ", "WON", "LOST", "VOID", "PUSH", "MITOSIS", "EXTINCT", "HALTED", "ORDER ERROR",
        "ACCOUNT PENDING", "SCAN FAILED", "SWEEP")
LIMIT = 4000                   # Telegram caps a message at 4096 characters


def news(events: list[str]) -> list[str]:
    return [e for e in events if e.startswith(NEWS)]


def due(pop: dict, now: datetime, mode: str, events: list[str]) -> str | None:
    """Why this run should message, or None. Updates pop's bookkeeping."""
    reason = None
    mode_word = mode.split(" ")[0]
    if pop.get("last_mode") != mode_word:
        reason = f"mode now {mode_word}"
        pop["last_mode"] = mode_word
    if news(events):
        reason = reason or "news"
    today = now.date().isoformat()
    if now.hour >= DIGEST_HOUR_UTC and pop.get("last_digest") != today:
        pop["last_digest"] = today
        reason = reason or "daily debrief"
    return reason


def send(text: str, post: Callable = requests.post) -> str:
    if not (TOKEN and CHAT_ID):
        return "Telegram not configured"
    if len(text) > LIMIT:
        text = text[:LIMIT - 20] + "\n… (cut)"
    try:
        r = post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}, timeout=20)
        return "Telegram sent" if r.status_code == 200 else f"Telegram failed: HTTP {r.status_code}"
    except requests.RequestException as e:
        return f"Telegram failed: {type(e).__name__}"
