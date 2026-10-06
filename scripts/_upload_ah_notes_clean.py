#!/usr/bin/env python3
from pathlib import Path
import base64
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
php = (root / "app/agent_dashboard/skykin_after_hours_cb.php").read_bytes().replace(b"\r\n", b"\n")

sh = f'''#!/bin/bash
set -eu
echo "=== Unpack PHP ==="
python3 -c "import base64; open('/tmp/skykin_after_hours_cb.php','wb').write(base64.b64decode('{base64.b64encode(php).decode()}')); print('ok')"
docker cp /tmp/skykin_after_hours_cb.php skykin-web:/var/www/fusionpbx/app/agent_dashboard/skykin_after_hours_cb.php

echo "=== Clean existing after-hours notes ==="
docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db = skykin_pdo_fusionpbx();
$n = $db->exec("UPDATE skykin_callbacks SET notes = '"'"'After hours'"'"' WHERE agent_id = '"'"'after-hours'"'"' AND status = '"'"'Scheduled'"'"'");
echo "updated=$n\\n";
$r = $db->query("SELECT callback_time, customer_phone, notes FROM skykin_callbacks WHERE agent_id='"'"'after-hours'"'"' AND status='"'"'Scheduled'"'"' ORDER BY callback_time DESC LIMIT 5");
foreach ($r as $row) {{
  echo $row["callback_time"]."  ".$row["customer_phone"]."  [".$row["notes"]."]\\n";
}}
'
echo "DONE — hard refresh Callbacks (Notes = After hours)"
'''

out = root / "scripts/_fix_ah_notes_clean.sh"
out.write_bytes(sh.replace("\r\n", "\n").encode())
r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("fix_ah_notes_clean.sh", out.read_bytes(), "application/x-sh")},
    timeout=60,
)
print("wrote", out)
print(r.text)
