#!/usr/bin/env python3
"""Send email via SkyKin smtp.env (SSL 465 or STARTTLS 587)."""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="/opt/skykin/fraud-alert/smtp.env")
    ap.add_argument("--to", required=True, help="Comma-separated recipients")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", default="")
    ap.add_argument("--body", default="")
    args = ap.parse_args()

    cfg = load_env(Path(args.env))
    host = cfg.get("SMTP_HOST", "")
    port = int(cfg.get("SMTP_PORT", "465"))
    user = cfg.get("SMTP_USER", "")
    password = cfg.get("SMTP_PASS", "")
    from_addr = cfg.get("EMAIL_FROM", user) or user
    from_name = cfg.get("EMAIL_FROM_NAME", "SkyKin Alerts")

    if not host or not user or not password:
        print("missing SMTP_HOST/USER/PASS in", args.env, file=sys.stderr)
        return 2

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8", errors="replace")
    if not body:
        body = sys.stdin.read()

    msg = EmailMessage()
    msg["Subject"] = args.subject
    msg["From"] = formataddr((from_name, from_addr))
    recipients = [x.strip() for x in args.to.split(",") if x.strip()]
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    ctx = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(user, password)
                s.send_message(msg)
    except Exception as e:
        print("SMTP send failed:", e, file=sys.stderr)
        return 1
    print("SMTP OK →", ", ".join(recipients))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
