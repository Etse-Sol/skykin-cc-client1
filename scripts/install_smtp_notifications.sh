#!/bin/bash
# Wire notifications@skykintech.com.et SMTP for SkyKin fraud alerts.
# Run on ecs-cc as root. LF only.
set -eu
DIR=/opt/skykin/fraud-alert
ALERT_TO='ashineshetu@skykintech.com,solomonetsegenet7@gmail.com'
mkdir -p "$DIR" /var/lib/skykin-fraud

cat > "$DIR/smtp.env" <<'EOF'
SMTP_HOST=mail.skykintech.com.et
SMTP_PORT=465
SMTP_USER=notifications@skykintech.com.et
SMTP_PASS=REDACTED_ALREADY_ON_CATBOX_INSTALL
EMAIL_FROM=notifications@skykintech.com.et
EMAIL_FROM_NAME=PMS
EOF
chmod 600 "$DIR/smtp.env"
chown root:root "$DIR/smtp.env"

cat > "$DIR/skykin_send_smtp.py" <<'PY'
#!/usr/bin/env python3
import argparse, smtplib, ssl, sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

def load_env(path):
    env = {}
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ap = argparse.ArgumentParser()
ap.add_argument("--env", default="/opt/skykin/fraud-alert/smtp.env")
ap.add_argument("--to", required=True)
ap.add_argument("--subject", required=True)
ap.add_argument("--body-file", default="")
ap.add_argument("--body", default="")
args = ap.parse_args()
cfg = load_env(args.env)
host, port = cfg["SMTP_HOST"], int(cfg.get("SMTP_PORT", "465"))
user, password = cfg["SMTP_USER"], cfg["SMTP_PASS"]
from_addr = cfg.get("EMAIL_FROM", user)
from_name = cfg.get("EMAIL_FROM_NAME", "SkyKin Alerts")
body = args.body or (Path(args.body_file).read_text(encoding="utf-8") if args.body_file else sys.stdin.read())
msg = EmailMessage()
msg["Subject"] = args.subject
msg["From"] = formataddr((from_name, from_addr))
recs = [x.strip() for x in args.to.split(",") if x.strip()]
msg["To"] = ", ".join(recs)
msg.set_content(body)
ctx = ssl.create_default_context()
if port == 465:
    with smtplib.SMTP_SSL(host, port, timeout=30, context=ctx) as s:
        s.login(user, password)
        s.send_message(msg)
else:
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo(); s.starttls(context=ctx); s.ehlo(); s.login(user, password); s.send_message(msg)
print("SMTP OK ->", ", ".join(recs))
PY
chmod 755 "$DIR/skykin_send_smtp.py"

MON="$DIR/skykin_fraud_alert.sh"
if [ -f "$MON" ]; then
  python3 - <<'PY'
import re
from pathlib import Path
p = Path("/opt/skykin/fraud-alert/skykin_fraud_alert.sh")
s = p.read_text()
if "skykin_send_smtp.py" in s:
    print("send_mail already uses SMTP")
else:
    new_fn = r'''send_mail() {
  local subject="$1"
  local body="$2"
  local smtp_env="${SKYKIN_SMTP_ENV:-/opt/skykin/fraud-alert/smtp.env}"
  local smtp_py="${SKYKIN_SMTP_PY:-/opt/skykin/fraud-alert/skykin_send_smtp.py}"
  if [ -f "$smtp_env" ] && [ -f "$smtp_py" ]; then
    local tmp; tmp=$(mktemp)
    printf '%s\n' "$body" > "$tmp"
    if python3 "$smtp_py" --env "$smtp_env" --to "$ALERT_TO" --subject "$subject" --body-file "$tmp"; then
      rm -f "$tmp"; return 0
    fi
    rm -f "$tmp"
  fi
  local from="${SKYKIN_FRAUD_FROM:-skykin-fraud@$(hostname -f 2>/dev/null || echo ecs-cc)}"
  if command -v mail >/dev/null 2>&1; then
    printf '%s\n' "$body" | mail -s "$subject" -r "$from" "$ALERT_TO" && return 0
  fi
  if command -v sendmail >/dev/null 2>&1; then
    { echo "To: $ALERT_TO"; echo "From: $from"; echo "Subject: $subject"; echo; printf '%s\n' "$body"; } | sendmail -t && return 0
  fi
  echo "WARN: SMTP failed and no mail fallback" >&2
  return 1
}'''
    s2, n = re.subn(r"send_mail\(\) \{[\s\S]*?\n\}", new_fn, s, count=1)
    if n != 1:
        raise SystemExit(f"could not patch send_mail (n={n})")
    p.write_text(s2)
    print("patched send_mail for SMTP")
PY
else
  echo "WARN: $MON missing — SMTP files ready; reinstall fraud monitor later"
fi

cat > /etc/cron.d/skykin-fraud-alert <<EOF
*/5 * * * * root SKYKIN_FRAUD_ALERT_TO='$ALERT_TO' SKYKIN_SMTP_ENV=$DIR/smtp.env SKYKIN_SMTP_PY=$DIR/skykin_send_smtp.py $DIR/skykin_fraud_alert.sh >> /var/log/skykin-fraud-alert.log 2>&1
EOF
chmod 644 /etc/cron.d/skykin-fraud-alert

echo "=== SMTP test ==="
python3 "$DIR/skykin_send_smtp.py" \
  --env "$DIR/smtp.env" \
  --to "$ALERT_TO" \
  --subject "[SkyKin] SMTP alert test OK" \
  --body "SkyKin alerts wired.
From: PMS <notifications@skykintech.com.et>
Host: mail.skykintech.com.et:465
Time: $(date -Is)
Server: $(hostname)
"

echo "DONE — check inbox/spam for $ALERT_TO"
