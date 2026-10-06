#!/usr/bin/env python3
import base64
from pathlib import Path
import requests

lua = Path(r"C:\Users\hp\skykin-fusionpbx\docker\freeswitch\scripts\skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n")
b64 = base64.b64encode(lua).decode()

sh = f"""#!/bin/bash
set -eu
echo "=== Deploy skykin_inbound.lua (opening/welcome before queue) ==="
python3 -c "import base64; open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('{b64}'))"
docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua
cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true
echo "=== Verify welcome block in Lua ==="
docker exec skykin-freeswitch grep -n "skykin welcome\\|ahununu-opening" /etc/freeswitch/scripts/skykin_inbound.lua | head -15
echo
echo "DONE — no FS restart. Next inbound call should log: skykin welcome play ..."
echo "After a test call: docker exec skykin-freeswitch sh -c 'grep \"skykin welcome\" /var/log/freeswitch/freeswitch.log | tail -5'"
"""

out = Path(r"C:\\Users\\hp\\skykin-fusionpbx\\scripts\\_deploy_inbound_welcome.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_inbound_welcome.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print(r.text)
print("bytes", out.stat().st_size)
