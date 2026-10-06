#!/usr/bin/env python3
"""Build + upload deploy script for outbound Busy/ringback differentiation."""
import base64
from pathlib import Path

import requests

ROOT = Path(r"C:\Users\hp\skykin-fusionpbx")
index_b64 = base64.b64encode((ROOT / "app/agent_dashboard/index.php").read_bytes()).decode()
lua_b64 = base64.b64encode(
    (ROOT / "docker/freeswitch/scripts/skykin_outbound.lua").read_bytes().replace(b"\r\n", b"\n")
).decode()

sh = f"""#!/bin/bash
set -eu
echo "=== Deploy outbound cause labels + ringback ==="
python3 -c "import base64; open('/tmp/index.php','wb').write(base64.b64decode('{index_b64}'))"
python3 -c "import base64; open('/tmp/skykin_outbound.lua','wb').write(base64.b64decode('{lua_b64}'))"

install -m 0644 /tmp/index.php /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-web php -r 'opcache_reset();' 2>/dev/null || true

mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_outbound.lua /opt/skykin/fs-live/skykin_outbound.lua
cp /tmp/skykin_outbound.lua /opt/skykin/fs-config/skykin_outbound.lua 2>/dev/null || true
docker cp /tmp/skykin_outbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_outbound.lua

echo "=== Verify ==="
grep -c skykinOutboundFailLabel /opt/skykin/app/app/agent_dashboard/index.php
grep -c hangup_cause /opt/skykin/app/app/agent_dashboard/index.php
docker exec skykin-freeswitch grep -n 'hangup agent cause\\|Propagate the real B-leg' /etc/freeswitch/scripts/skykin_outbound.lua | head -5
echo "DONE — hard-refresh agent dashboard (Ctrl+F5), then test Busy / off / ringing"
"""

out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_outbound_cause.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
print("script bytes", out.stat().st_size)

r = requests.post(
    "https://litterbox.catbox.moe/resources/internals/api.php",
    data={"reqtype": "fileupload", "time": "72h"},
    files={"fileToUpload": ("deploy_outbound_cause.sh", out.read_bytes(), "application/x-sh")},
    timeout=180,
)
print("URL", r.text.strip())
