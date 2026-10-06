#!/usr/bin/env python3
"""Build installer that wires notifications@ SMTP on ecs-cc. Password only in install payload."""
import base64
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
send_py = (root / "scripts/skykin_send_smtp.py").read_bytes().replace(b"\r\n", b"\n")
alert_sh = (root / "scripts/skykin_fraud_alert.sh").read_bytes().replace(b"\r\n", b"\n")

# Credentials are NOT stored here — set them on ecs-cc in /opt/skykin/fraud-alert/smtp.env
SMTP_ENV = """SMTP_HOST=mail.skykintech.com.et
SMTP_PORT=465
SMTP_USER=notifications@skykintech.com.et
SMTP_PASS=REDACTED_SET_ON_SERVER
EMAIL_FROM=notifications@skykintech.com.et
EMAIL_FROM_NAME=PMS
"""

ALERT_TO = "ashineshetu@skykintech.com,solomonetsegenet7@gmail.com"

sh = f'''#!/bin/bash
set -eu
DIR=/opt/skykin/fraud-alert
ALERT_TO='{ALERT_TO}'
mkdir -p "$DIR" /var/lib/skykin-fraud

echo "=== 1) Install SMTP sender + fraud monitor ==="
python3 -c "import base64; open('$DIR/skykin_send_smtp.py','wb').write(base64.b64decode('{base64.b64encode(send_py).decode()}')); open('$DIR/skykin_fraud_alert.sh','wb').write(base64.b64decode('{base64.b64encode(alert_sh).decode()}')); print('unpacked')"
chmod 755 "$DIR/skykin_send_smtp.py" "$DIR/skykin_fraud_alert.sh"

echo "=== 2) Write smtp.env (mode 600) ==="
python3 -c "import base64; open('$DIR/smtp.env','wb').write(base64.b64decode('{base64.b64encode(SMTP_ENV.encode()).decode()}')); print('smtp.env written')"
chmod 600 "$DIR/smtp.env"
chown root:root "$DIR/smtp.env"

echo "=== 3) Cron every 5 min ==="
cat > /etc/cron.d/skykin-fraud-alert <<EOF
*/5 * * * * root SKYKIN_FRAUD_ALERT_TO='$ALERT_TO' SKYKIN_SMTP_ENV=$DIR/smtp.env SKYKIN_SMTP_PY=$DIR/skykin_send_smtp.py $DIR/skykin_fraud_alert.sh >> /var/log/skykin-fraud-alert.log 2>&1
EOF
chmod 644 /etc/cron.d/skykin-fraud-alert

echo "=== 4) SMTP test send ==="
python3 "$DIR/skykin_send_smtp.py" \\
  --env "$DIR/smtp.env" \\
  --to "$ALERT_TO" \\
  --subject "[SkyKin] SMTP alert test OK" \\
  --body "SkyKin fraud/email alerts are wired.

From: PMS <notifications@skykintech.com.et>
Host: mail.skykintech.com.et:465
Time: $(date -Is)
Server: $(hostname)

If you received this, SMTP works.
"

echo "=== 5) Run fraud monitor once ==="
SKYKIN_FRAUD_ALERT_TO="$ALERT_TO" SKYKIN_SMTP_ENV="$DIR/smtp.env" SKYKIN_SMTP_PY="$DIR/skykin_send_smtp.py" \\
  "$DIR/skykin_fraud_alert.sh" || true

echo
echo "DONE. Check inbox/spam for: $ALERT_TO"
echo "Log: tail -30 /var/log/skykin-fraud-alert.log"
'''

out = root / "scripts/_install_smtp_notifications.sh"
out.write_bytes(sh.replace("\r\n", "\n").encode())
print("wrote", out, "bytes", out.stat().st_size)

r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("install_smtp_notifications.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print(r.text)
