#!/usr/bin/env python3
"""Send email via Outlook / Microsoft 365 SMTP.

Usage:
    py -3.12 scripts/send_email.py --to "someone@example.com" --subject "Hi" --body "Hello!"
    py -3.12 scripts/send_email.py --to "a@x.com,b@x.com" --subject "Meeting" --body "Details" --cc "cc@x.com" --attachments "file1.pdf,image.png"

Reads credentials from .env:
    OUTLOOK_SMTP_USER       your_email@outlook.com
    OUTLOOK_SMTP_PASSWORD   app_password (NOT your login password)
    OUTLOOK_SMTP_HOST       smtp.office365.com  (default)
    OUTLOOK_SMTP_PORT       587                 (default)

Requires: py -3.12 (Python 3.12 stdlib only — no pip deps).
"""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path


def _load_env(env_path: Path) -> None:
    """Minimal .env loader (no dotenv dependency)."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def build_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    attachments: list[str] | None = None,
) -> EmailMessage:
    """Build and return an EmailMessage (does NOT send it)."""
    msg = EmailMessage()
    msg["From"] = os.environ.get("OUTLOOK_SMTP_USER", "")
    msg["To"] = to
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    if cc:
        msg["Cc"] = cc

    msg.set_content(body)

    # Attachments
    for path_str in (attachments or []):
        p = Path(path_str)
        if not p.exists():
            print(f"WARNING: attachment not found: {p}", file=sys.stderr)
            continue
        ctype = _guess_mime(p)
        maintype, subtype = ctype.split("/", 1)
        with open(p, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=p.name,
            )

    return msg


def send(msg: EmailMessage) -> dict:
    """Send the message via SMTP. Returns dict with status."""
    user = os.environ.get("OUTLOOK_SMTP_USER", "")
    password = os.environ.get("OUTLOOK_SMTP_PASSWORD", "")
    host = os.environ.get("OUTLOOK_SMTP_HOST", "smtp.office365.com")
    port = int(os.environ.get("OUTLOOK_SMTP_PORT", "587"))

    if not user or not password:
        return {
            "success": False,
            "error": "Missing OUTLOOK_SMTP_USER or OUTLOOK_SMTP_PASSWORD in .env",
        }

    # Collect all recipients (To + Cc + Bcc)
    all_recipients: list[str] = []
    if msg["To"]:
        all_recipients.extend(r.strip() for r in msg["To"].split(","))
    if msg.get("Cc"):
        all_recipients.extend(r.strip() for r in msg["Cc"].split(","))
    if bcc:
        all_recipients.extend(r.strip() for r in bcc.split(","))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(user, password)
            server.send_message(msg, from_addr=user, to_addrs=all_recipients)
        return {"success": True, "message_id": msg.get("Message-ID", ""), "to": msg["To"]}
    except smtplib.SMTPAuthenticationError as exc:
        return {"success": False, "error": f"SMTP auth failed: {exc}"}
    except smtplib.SMTPException as exc:
        return {"success": False, "error": f"SMTP error: {exc}"}
    except Exception as exc:
        return {"success": False, "error": f"Unexpected: {exc}"}


def _guess_mime(path: Path) -> str:
    """Return MIME type string from file extension."""
    suffix = path.suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt": "text/plain",
        ".html": "text/html",
        ".csv": "text/csv",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".zip": "application/zip",
    }.get(suffix, "application/octet-stream")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Send email via Outlook SMTP")
    p.add_argument("--to", required=True, help="Recipient(s), comma-separated")
    p.add_argument("--subject", required=True, help="Email subject")
    p.add_argument("--body", required=True, help="Email body (plain text)")
    p.add_argument("--cc", default=None, help="CC recipient(s), comma-separated")
    p.add_argument("--bcc", default=None, help="BCC recipient(s), comma-separated")
    p.add_argument(
        "--attachments",
        default=None,
        help="Comma-separated file paths to attach",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build message but don't send (prints preview)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv)

    # Load .env from repo root (scripts/../../.env)
    env_path = Path(__file__).resolve().parent.parent / ".env"
    _load_env(env_path)

    attachments = (
        [a.strip() for a in ns.attachments.split(",")] if ns.attachments else []
    )

    msg = build_message(
        to=ns.to,
        subject=ns.subject,
        body=ns.body,
        cc=ns.cc,
        bcc=ns.bcc,
        attachments=attachments,
    )

    if ns.dry_run:
        print("=== DRY RUN — message not sent ===")
        print(f"From:  {msg['From']}")
        print(f"To:    {msg['To']}")
        if msg.get("Cc"):
            print(f"Cc:    {msg['Cc']}")
        print(f"Subj:  {msg['Subject']}")
        print(f"Date:  {msg['Date']}")
        print(f"Body:\n{msg.get_content()[:500]}")
        if attachments:
            print(f"\nAttachments: {attachments}")
        return 0

    result = send(msg)

    if result["success"]:
        print(f"OK — email sent to {result.get('to', ns.to)}")
        if result.get("message_id"):
            print(f"Message-ID: {result['message_id']}")
        return 0
    else:
        print(f"FAILED — {result['error']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
