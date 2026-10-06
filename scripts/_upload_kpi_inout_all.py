#!/usr/bin/env python3
import gzip
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php.gz": root / "app/agent_dashboard/index.php",
    "supervisor.php.gz": root / "app/agent_dashboard/supervisor.php",
    "skykin_config.php.gz": root / "app/agent_dashboard/skykin_config.php",
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
echo "=== KPI Inbound/Outbound split (agent + supervisor) ==="
curl -fsSL -o /tmp/index.php.gz '{urls["index.php.gz"]}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php.gz"]}'
curl -fsSL -o /tmp/skykin_config.php.gz '{urls["skykin_config.php.gz"]}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_config.php.gz > /tmp/skykin_config.php
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
install -m 0644 /tmp/skykin_config.php "$DASH/skykin_config.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_AGENT_KPI_IN_OUT_v1 "$DASH/index.php"
grep -c SKYKIN_KPI_IN_OUT_v1 "$DASH/supervisor.php"
grep -c answered_inbound "$DASH/skykin_config.php"
echo DONE
"""
out = root / "scripts" / "_deploy_kpi_inout_all.sh"
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_kpi_inout_all.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
