#!/usr/bin/env python3
import gzip
from pathlib import Path

import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
idx = gzip.compress((root / "app/agent_dashboard/index.php").read_bytes(), 9)
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("index.php.gz", idx, "application/gzip")},
    timeout=180,
)
url = r.text.strip()
print("index", url)

sh = f"""#!/bin/bash
set -eu
echo "=== Fix stuck Call ended status (SIP 487) ==="
curl -fsSL -o /tmp/index.php.gz '{url}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v5 /opt/skykin/app/app/agent_dashboard/index.php
grep -c skykinRestoreRegisteredStatus /opt/skykin/app/app/agent_dashboard/index.php
echo DONE
"""
out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_out_status_clear.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r2 = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_out_status_clear.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r2.text.strip())
