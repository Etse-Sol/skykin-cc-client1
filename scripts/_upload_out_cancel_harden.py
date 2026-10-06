#!/usr/bin/env python3
"""Upload outbound premature-cancel harden pack to catbox for ecs-cc."""
import gzip
from pathlib import Path

import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php.gz": root / "app/agent_dashboard/index.php",
    "supervisor.php.gz": root / "app/agent_dashboard/supervisor.php",
}
urls = {}
for name, path in files.items():
    gz = gzip.compress(path.read_bytes(), 9)
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (name, gz, "application/gzip")},
        timeout=180,
    )
    urls[name] = r.text.strip()
    print(name, urls[name])

sh = f"""#!/bin/bash
set -eu
echo "=== Harden outbound: stop ORIGINATOR_CANCEL right after Call ==="
curl -fsSL -o /tmp/index.php.gz '{urls["index.php.gz"]}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php.gz"]}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v6 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v2 "$DASH/supervisor.php"
grep -c '_outDeclineTicks >= 5' "$DASH/index.php"
grep -c 'ageMs >= 4000' "$DASH/index.php"
echo DONE
"""
out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_out_cancel_harden.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_out_cancel_harden.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
