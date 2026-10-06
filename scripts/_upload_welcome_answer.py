#!/usr/bin/env python3
import base64
from pathlib import Path
import requests

lua = Path(r"C:\Users\hp\skykin-fusionpbx\docker\freeswitch\scripts\skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n")
b64 = base64.b64encode(lua).decode()

sh = (
    "#!/bin/bash\n"
    "set -eu\n"
    "echo '=== Fix welcome: answer() so PSTN hears opening ==='\n"
    "python3 -c \"import base64; open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('"
    + b64
    + "'))\"\n"
    "docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua\n"
    "cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua\n"
    "cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true\n"
    "echo '=== WAV files present? ==='\n"
    "docker exec skykin-freeswitch ls -lah /var/lib/freeswitch/recordings/ahununu/opening-long.wav /var/lib/freeswitch/recordings/ahununu/ahununu-opening.wav /var/lib/freeswitch/recordings/ahununu/waiting-2.wav 2>&1 | head -20\n"
    "echo '=== Verify answer in Lua ==='\n"
    "docker exec skykin-freeswitch grep -n 'welcome answer\\|opening-long\\|streamFile' /etc/freeswitch/scripts/skykin_inbound.lua | head -15\n"
    "echo\n"
    "echo 'DONE — no FS restart. Call again: call should ANSWER then play opening (timer starts).'\n"
    "echo \"Then: docker exec skykin-freeswitch sh -c 'grep \\\"skykin welcome\\\" /var/log/freeswitch/freeswitch.log | tail -5'\"\n"
)

out = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\_deploy_welcome_answer.sh")
out.write_bytes(sh.encode().replace(b"\r\n", b"\n"))
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_welcome_answer.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print(r.text)
