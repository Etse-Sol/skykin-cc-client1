#!/usr/bin/env python3
import base64
import requests
from pathlib import Path

p = Path(r"C:\Users\hp\skykin-fusionpbx\scripts\deploy_recent_dials.py").read_bytes()
b64 = base64.b64encode(p).decode()
sh = (
    "#!/bin/bash\n"
    "set -eu\n"
    f"python3 -c \"import base64; open('/tmp/deploy_recent_dials.py','wb').write(base64.b64decode('{b64}'))\"\n"
    "python3 /tmp/deploy_recent_dials.py\n"
)
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("recent_dials.sh", sh.encode(), "application/x-sh")},
    timeout=60,
)
print(r.text)
