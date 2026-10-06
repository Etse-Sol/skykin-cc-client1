#!/usr/bin/env python3
import gzip
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
files = {
    "index.php.gz": root / "app/agent_dashboard/index.php",
    "supervisor.php.gz": root / "app/agent_dashboard/supervisor.php",
    "skykin_inbound.lua.gz": root / "docker/freeswitch/scripts/skykin_inbound.lua",
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
echo "=== Softphone harden v1 (keepalive + cooldown + optional SRTP) ==="
curl -fsSL -o /tmp/index.php.gz '{urls["index.php.gz"]}'
curl -fsSL -o /tmp/supervisor.php.gz '{urls["supervisor.php.gz"]}'
curl -fsSL -o /tmp/skykin_inbound.lua.gz '{urls["skykin_inbound.lua.gz"]}'
gzip -dc /tmp/index.php.gz > /tmp/index.php
gzip -dc /tmp/supervisor.php.gz > /tmp/supervisor.php
gzip -dc /tmp/skykin_inbound.lua.gz > /tmp/skykin_inbound.lua
DASH=/opt/skykin/app/app/agent_dashboard
install -m 0644 /tmp/index.php "$DASH/index.php"
install -m 0644 /tmp/supervisor.php "$DASH/supervisor.php"
cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua
cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true
docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 "$DASH/index.php"
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 "$DASH/supervisor.php"
grep -c SKYKIN_SOFTPHONE_HARDEN_v1 /opt/skykin/fs-live/skykin_inbound.lua
grep -c 'tech-fail cooldown 90s' /opt/skykin/fs-live/skykin_inbound.lua
grep -c 'rtp_secure_media=optional' /opt/skykin/fs-live/skykin_inbound.lua
echo DONE
"""
out = root / "scripts" / "_deploy_softphone_harden.sh"
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_softphone_harden.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("DEPLOY", r.text.strip())
