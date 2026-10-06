#!/usr/bin/env python3
import base64
import re
from pathlib import Path
import requests

src = Path(r"C:\Users\hp\skykin-fusionpbx\docker\freeswitch\scripts\skykin_inbound.lua").read_text(encoding="utf-8")
rb = re.sub(
    r"\n-- Opening / welcome.*?^end\n\nlocal queue",
    r"\n\nlocal queue",
    src,
    count=1,
    flags=re.S | re.M,
)
if "ahununu-opening" in rb:
    raise SystemExit("rollback strip failed")
lua = rb.replace("\r\n", "\n").encode()
b64 = base64.b64encode(lua).decode()

sh = f"""#!/bin/bash
set -eu
echo "=== ROLLBACK skykin_inbound.lua (remove opening/welcome) ==="
if [ -f /opt/skykin/fs-live/skykin_inbound.lua.bak-pre-welcome ]; then
  echo "Restoring /opt/skykin/fs-live/skykin_inbound.lua.bak-pre-welcome"
  docker cp /opt/skykin/fs-live/skykin_inbound.lua.bak-pre-welcome skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
  cp /opt/skykin/fs-live/skykin_inbound.lua.bak-pre-welcome /opt/skykin/fs-live/skykin_inbound.lua
else
  echo "No pre-welcome backup — installing Lua without opening block"
  python3 -c "import base64; open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('{b64}'))"
  docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
  mkdir -p /opt/skykin/fs-live
  cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua
fi
echo "=== Verify opening gone ==="
if docker exec skykin-freeswitch grep -n "ahununu-opening\\|skykin welcome" /etc/freeswitch/scripts/skykin_inbound.lua; then
  echo "WARN: welcome strings still present"
else
  echo "OK: no welcome/opening in inbound Lua"
fi
echo "DONE — no FS restart. New calls skip opening."
"""

out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_rollback_inbound_welcome.sh")
out.write_bytes(sh.encode("utf-8").replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("rollback_inbound_welcome.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print(r.text)
