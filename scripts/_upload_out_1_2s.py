#!/usr/bin/env python3
import gzip
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php.gz": root / "app/agent_dashboard/index.php",
    "supervisor.php.gz": root / "app/agent_dashboard/supervisor.php",
    "skykin_outbound.lua.gz": root / "docker/freeswitch/scripts/skykin_outbound.lua",
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
echo "=== Faster outbound aim 1-2s (ICE 400ms + warm + lua) ==="
curl -fsSL -o /tmp/index.php.gz '{urls["index.php.gz"]}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php.gz"]}'
curl -fsSL -o /tmp/skykin_outbound.lua.gz '{urls["skykin_outbound.lua.gz"]}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_outbound.lua.gz > /tmp/skykin_outbound.lua
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_OUT_RING_v9 "$DASH/index.php"
grep -c SKYKIN_SUP_OUT_v5 "$DASH/supervisor.php"
grep -c SKYKIN_ICE_FAST_v2 "$DASH/index.php"
docker exec skykin-freeswitch grep -c bgapi /etc/freeswitch/scripts/skykin_outbound.lua
echo DONE
"""
out = root / "scripts" / "_deploy_out_1_2s.sh"
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_out_1_2s.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
