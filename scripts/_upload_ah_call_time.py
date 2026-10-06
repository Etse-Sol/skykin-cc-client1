#!/usr/bin/env python3
"""Build+upload after-hours call-time fix installer."""
import base64
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
php = (root / "app/agent_dashboard/skykin_after_hours_cb.php").read_bytes().replace(b"\r\n", b"\n")
lua = (root / "docker/freeswitch/scripts/skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n")

update_php = b'''<?php
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db = skykin_pdo_fusionpbx();
$items = json_decode(file_get_contents("/tmp/ah_items.json") ?: "[]", true) ?: [];
$n = 0;
foreach ($items as $it) {
  $phone = (string)($it["phone"] ?? "");
  $ts = (string)($it["ts"] ?? "");
  $domain = (string)($it["domain"] ?? "ahununu");
  if ($phone === "" || $ts === "") continue;
  $notes = "Called {$ts} EAT \\xc2\\xb7 return after 08:00 | domain={$domain} | did=log-backfill | uuid=log";
  $digits = preg_replace("/\\D+/", "", $phone) ?? "";
  $st = $db->prepare(
    "UPDATE skykin_callbacks
        SET callback_time = :t, notes = :n, customer_name = '\\''After-hours caller'\\''
      WHERE agent_id = '\\''after-hours'\\'' AND status = '\\''Scheduled'\\''
        AND (customer_phone = :p OR customer_phone = :p2 OR notes LIKE :like)"
  );
  $st->execute([
    ":t" => $ts,
    ":n" => $notes,
    ":p" => $phone,
    ":p2" => $digits,
    ":like" => "%" . $digits . "%",
  ]);
  $n += $st->rowCount();
}
echo "updated_rows=$n\\n";
'''
# Fix the PHP properly without broken escapes
update_php = '''<?php
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db = skykin_pdo_fusionpbx();
$items = json_decode(file_get_contents("/tmp/ah_items.json") ?: "[]", true) ?: [];
$n = 0;
foreach ($items as $it) {
  $phone = (string)($it["phone"] ?? "");
  $ts = (string)($it["ts"] ?? "");
  $domain = (string)($it["domain"] ?? "ahununu");
  if ($phone === "" || $ts === "") continue;
  $notes = "Called {$ts} EAT · return after 08:00 | domain={$domain} | did=log-backfill | uuid=log";
  $digits = preg_replace("/\\D+/", "", $phone) ?? "";
  $st = $db->prepare(
    "UPDATE skykin_callbacks
        SET callback_time = :t, notes = :n, customer_name = 'After-hours caller'
      WHERE agent_id = 'after-hours' AND status = 'Scheduled'
        AND (customer_phone = :p OR customer_phone = :p2 OR notes LIKE :like)"
  );
  $st->execute([
    ":t" => $ts,
    ":n" => $notes,
    ":p" => $phone,
    ":p2" => $digits,
    ":like" => "%" . $digits . "%",
  ]);
  $n += $st->rowCount();
}
echo "updated_rows=$n\\n";
'''.encode()

bash = f'''#!/bin/bash
set -eu
KEY=skykin-ah-cb-2026
WEB_PHP=/var/www/fusionpbx/app/agent_dashboard

echo "=== Unpack ==="
python3 -c "import base64; open('/tmp/skykin_after_hours_cb.php','wb').write(base64.b64decode('{base64.b64encode(php).decode()}')); open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('{base64.b64encode(lua).decode()}')); open('/tmp/ah_update_times.php','wb').write(base64.b64decode('{base64.b64encode(update_php).decode()}')); print('ok')"

echo "=== PHP + Lua ==="
docker cp /tmp/skykin_after_hours_cb.php skykin-web:$WEB_PHP/skykin_after_hours_cb.php
docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
mkdir -p /opt/skykin/fs-live
cp /tmp/skykin_inbound.lua /opt/skykin/fs-live/skykin_inbound.lua
cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true
docker cp /tmp/ah_update_times.php skykin-web:/tmp/ah_update_times.php

echo "=== UI column label ==="
docker exec skykin-web php -r '
foreach (["/var/www/fusionpbx/app/agent_dashboard/index.php","/var/www/fusionpbx/app/agent_dashboard/supervisor_tools.php"] as $p) {{
  $s=file_get_contents($p);
  $n=str_replace(["<th>Scheduled Time</th>","<th>Scheduled</th>"],["<th>Called / Due</th>","<th>Called / Due</th>"],$s);
  if ($n!==$s) {{ file_put_contents($p,$n); echo "patched $p\\n"; }} else {{ echo "ok $p\\n"; }}
}}
'

echo "=== Complete smoke-test row ==="
docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db=skykin_pdo_fusionpbx();
$db->exec("UPDATE skykin_callbacks SET status='"'"'Completed'"'"' WHERE agent_id='"'"'after-hours'"'"' AND customer_phone LIKE '"'"'%900000099'"'"'");
echo "smoke completed\\n";
'

echo "=== Re-stamp times from FS logs ==="
docker exec skykin-freeswitch sh -c 'grep -h "skykin after-hours drop" /var/log/freeswitch/freeswitch.log* 2>/dev/null | tail -400' > /tmp/ah_drops2.txt || true
python3 - <<'PY'
import re, json, subprocess
from pathlib import Path
text = Path("/tmp/ah_drops2.txt").read_text(errors="replace") if Path("/tmp/ah_drops2.txt").exists() else ""
pat = re.compile(
    r"(?P<ts>\\d{{4}}-\\d{{2}}-\\d{{2}}\\s+\\d{{2}}:\\d{{2}}:\\d{{2}})(?:\\.\\d+)?\\s+.*?after-hours drop domain=(?P<domain>\\S+)\\s+cid=(?P<cid>\\S+)"
)
latest = {{}}
for m in pat.finditer(text):
    latest[m.group("cid").rstrip("\\\\n")] = {{
        "ts": m.group("ts"),
        "domain": m.group("domain"),
        "phone": m.group("cid").rstrip("\\\\n"),
    }}
items = list(latest.values())
print(f"parsed unique CIDs: {{len(items)}}")
Path("/tmp/ah_items.json").write_text(json.dumps(items))
subprocess.check_call(["docker", "cp", "/tmp/ah_items.json", "skykin-web:/tmp/ah_items.json"])
out = subprocess.check_output(["docker", "exec", "skykin-web", "php", "/tmp/ah_update_times.php"], text=True, errors="replace")
print(out)
PY

echo "=== Sample rows ==="
docker exec skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$db=skykin_pdo_fusionpbx();
$r=$db->query("SELECT callback_time, customer_phone, left(notes,72) n FROM skykin_callbacks WHERE agent_id='"'"'after-hours'"'"' AND status='"'"'Scheduled'"'"' ORDER BY callback_time DESC LIMIT 8");
foreach ($r as $row) {{ echo $row["callback_time"]."  ".$row["customer_phone"]."  ".$row["n"]."\\n"; }}
'

echo
echo "DONE. Hard-refresh Callbacks — first column = when they called (EAT)."
'''

# Fix double-brace over-escaping in the python heredoc inside bash
# The f-string doubled braces for literal; the PY regex needs single braces for {{4}} etc which become {4}
# Actually in f-string {{ -> { so \\d{{4}} becomes \d{4} in output - good for the remote python regex.

out = root / "scripts/_fix_ah_cb_call_time.sh"
out.write_bytes(bash.replace("\r\n", "\n").encode())
print("wrote", out, "bytes", out.stat().st_size)

r = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("fix_ah_cb_call_time.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print(r.text)
