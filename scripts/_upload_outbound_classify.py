#!/usr/bin/env python3
"""Upload outbound classification deploy pack to catbox."""
import gzip
from pathlib import Path

import requests

ROOT = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php.gz": ROOT / "app/agent_dashboard/index.php",
    "skykin_config.php.gz": ROOT / "app/agent_dashboard/skykin_config.php",
    "supervisor.php.gz": ROOT / "app/agent_dashboard/supervisor.php",
    "skykin_outbound.lua.gz": ROOT / "docker/freeswitch/scripts/skykin_outbound.lua",
}
urls = {}
for name, path in files.items():
    data = path.read_bytes()
    if name.endswith(".lua.gz"):
        data = data.replace(b"\r\n", b"\n")
    gz = gzip.compress(data, 9)
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": (name, gz, "application/gzip")},
        timeout=180,
    )
    urls[name] = r.text.strip()
    print(name, urls[name], len(gz))

sh = f"""#!/bin/bash
set -eu
echo "=== Deploy outbound call classification ==="
curl -fsSL -o /tmp/index.php.gz '{urls['index.php.gz']}'
curl -fsSL -o /tmp/skykin_config.php.gz '{urls['skykin_config.php.gz']}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls['supervisor.php.gz']}'
curl -fsSL -o /tmp/skykin_outbound.lua.gz '{urls['skykin_outbound.lua.gz']}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/skykin_config.php.gz > /tmp/skykin_config.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_outbound.lua.gz > /tmp/skykin_outbound.lua

DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/skykin_config.php "$DASH/skykin_config.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true

mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua

echo "=== Verify ==="
grep -c skykin_outbound_fail_label "$DASH/skykin_config.php"
grep -c skykinOutboundFailLabel "$DASH/index.php"
grep -c playOutboundFailTone "$DASH/index.php"
docker exec skykin-freeswitch grep -c 'hangup agent cause' /etc/freeswitch/scripts/skykin_outbound.lua
echo "DONE — hard-refresh agent + supervisor dashboards"
echo "Live call: Busy / No answer tones. History Status: Busy, No answer / switched off, etc."
"""
out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_outbound_classify.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_outbound_classify.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
