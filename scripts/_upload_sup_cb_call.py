#!/usr/bin/env python3
import base64
import requests
from pathlib import Path

src = Path(r"C:\Users\hp\skykin-fusionpbx\app\agent_dashboard\supervisor_tools.php").read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
b64 = base64.b64encode(src).decode()
sh = f"""#!/bin/bash
set -eu
python3 -c \"import base64; open('/tmp/supervisor_tools.php','wb').write(base64.b64decode('{b64}'))\"
docker cp /tmp/supervisor_tools.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/supervisor_tools.php
docker exec skykin-web grep -n callFromCallback /var/www/fusionpbx/app/agent_dashboard/supervisor_tools.php | head -5
echo OK — hard refresh Supervisor Callbacks
"""
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("sup_cb_call.sh", sh.encode(), "application/x-sh")},
    timeout=60,
)
print(r.text)
