#!/usr/bin/env python3
from pathlib import Path
import base64
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
php = (root / "app/agent_dashboard/skykin_after_hours_cb.php").read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
lua = (root / "docker/freeswitch/scripts/skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
deploy_lines = (root / "scripts/deploy_after_hours_callback.sh").read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
body = "\n".join(deploy_lines[2:]) + "\n"

final = (
    "#!/bin/bash\n"
    "set -eu\n"
    "echo Unpacking after-hours callback files...\n"
    "python3 -c \"import base64; "
    f"open('/tmp/skykin_after_hours_cb.php','wb').write(base64.b64decode('{base64.b64encode(php).decode()}')); "
    f"open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('{base64.b64encode(lua).decode()}')); "
    "print('unpacked')\"\n"
    + body
)
out = root / "scripts/_install_ah_cb_full.sh"
out.write_bytes(final.encode("utf-8"))
print("wrote", out, "bytes", out.stat().st_size)

r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("install_ah_cb.sh", final.encode("utf-8"), "application/x-sh")},
    timeout=90,
)
print(r.text)
