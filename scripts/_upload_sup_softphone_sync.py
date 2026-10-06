#!/usr/bin/env python3
import gzip
from pathlib import Path

import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "supervisor.php.gz": root / "app/agent_dashboard/supervisor.php",
    "index.php.gz": root / "app/agent_dashboard/index.php",
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
echo "=== Sync supervisor softphone + agent status clear ==="
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php.gz"]}'
curl -fsSL -o /tmp/index.php.gz '{urls["index.php.gz"]}'
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/index.php.gz > /tmp/index.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
install -m 0644 /tmp/index.php "$DASH/index.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_SUP_OUT_v1 "$DASH/supervisor.php"
grep -c SKYKIN_OUT_RING_v5 "$DASH/index.php"
grep -c skykinRestoreRegisteredStatus "$DASH/index.php"
echo DONE
"""
out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_sup_softphone_sync.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_sup_softphone_sync.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
