#!/usr/bin/env python3
import base64
from pathlib import Path
import requests

root = Path(r"C:\Users\hp\skykin-fusionpbx")
lua_b64 = base64.b64encode(
    (root / "docker/freeswitch/scripts/skykin_inbound.lua").read_bytes().replace(b"\r\n", b"\n")
).decode()
wel_b64 = base64.b64encode(
    (root / "docker/freeswitch/scripts/skykin_welcome.lua").read_bytes().replace(b"\r\n", b"\n")
).decode()

rb = """#!/bin/bash
set -eu
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || echo SkykinEslChangeMe1)
LIVE=/opt/skykin/fs-live
BAK="$LIVE/skykin_inbound.lua.bak-pre-opening-waiting"
echo "=== ROLLBACK opening/waiting ==="
if [ ! -f "$BAK" ]; then echo "Missing $BAK"; exit 1; fi
docker cp "$BAK" skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
cp "$BAK" "$LIVE/skykin_inbound.lua"
if [ -f /tmp/ahununu_did.xml.bak ]; then
  XML=$(docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/dialplan/public/*ahununu* 2>/dev/null | head -1' || true)
  if [ -n "$XML" ]; then docker cp /tmp/ahununu_did.xml.bak "skykin-freeswitch:$XML" || true; fi
fi
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "reloadxml" || true
echo "DONE — rolled back. No FS restart."
"""
rb_path = root / "scripts/_rollback_ahununu_opening_waiting.sh"
rb_path.write_bytes(rb.replace("\r\n", "\n").encode())
r2 = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("rollback_ahununu_ow.sh", rb_path.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("rollback", r2.text)
rollback_url = r2.text.strip()

# Build deploy without outer f-string interpreting {WAIT}
parts = []
parts.append("#!/bin/bash\nset -eu\n")
parts.append("PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || echo SkykinEslChangeMe1)\n")
parts.append("REC=/var/lib/freeswitch/recordings/ahununu\nLIVE=/opt/skykin/fs-live\n\n")
parts.append('echo "=== 0) Backup current Lua ==="\nmkdir -p "$LIVE"\n')
parts.append('docker exec skykin-freeswitch cat /etc/freeswitch/scripts/skykin_inbound.lua > "$LIVE/skykin_inbound.lua.bak-pre-opening-waiting"\n')
parts.append('ls -la "$LIVE/skykin_inbound.lua.bak-pre-opening-waiting"\n\n')
parts.append('echo "=== 1) Ensure WAVs on FreeSWITCH ==="\ndocker exec skykin-freeswitch mkdir -p "$REC"\n')
parts.append("""for name in opening-long.wav waiting-2.wav music.wav call-end-2.wav; do
  if docker exec skykin-freeswitch test -f "$REC/$name"; then echo "FS has $name"; continue; fi
  FOUND=$(docker exec skykin-web sh -c "find /var/lib/freeswitch/recordings/ahununu /var/www/fusionpbx -name '$name' 2>/dev/null | head -1" || true)
  if [ -n "$FOUND" ]; then
    docker cp "skykin-web:$FOUND" "/tmp/$name"
    docker cp "/tmp/$name" "skykin-freeswitch:$REC/$name"
    echo "copied $name"
  else
    echo "WARN: missing $name"
  fi
done
docker exec skykin-freeswitch ls -lah "$REC"/opening-long.wav "$REC"/waiting-2.wav 2>/dev/null || true

""")
parts.append('echo "=== 2) Install Lua ==="\n')
parts.append(
    "python3 -c \"import base64; open('/tmp/skykin_inbound.lua','wb').write(base64.b64decode('"
    + lua_b64
    + "')); open('/tmp/skykin_welcome.lua','wb').write(base64.b64decode('"
    + wel_b64
    + "'))\"\n"
)
parts.append("""docker cp /tmp/skykin_inbound.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
docker cp /tmp/skykin_welcome.lua skykin-freeswitch:/etc/freeswitch/scripts/skykin_welcome.lua
cp /tmp/skykin_inbound.lua "$LIVE/skykin_inbound.lua"
cp /tmp/skykin_inbound.lua /opt/skykin/fs-config/skykin_inbound.lua 2>/dev/null || true

echo "=== 3) Patch ahununu dialplan MOH (best-effort) ==="
XML=$(docker exec skykin-freeswitch sh -c 'ls /etc/freeswitch/dialplan/public/*ahununu* 2>/dev/null | head -1' || true)
if [ -n "$XML" ]; then
  docker cp "skykin-freeswitch:$XML" /tmp/ahununu_did.xml
  cp /tmp/ahununu_did.xml /tmp/ahununu_did.xml.bak
  python3 <<'PY'
from pathlib import Path
p = Path("/tmp/ahununu_did.xml")
s = p.read_text()
WAIT = "/var/lib/freeswitch/recordings/ahununu/waiting-2.wav"
s2 = s.replace('data="cc_moh_override="/>', 'data="cc_moh_override=' + WAIT + '"/>')
needle = '<action application="set" data="cc_moh_override=' + WAIT + '"/>'
if 'export" data="cc_moh_override=' not in s2 and needle in s2:
    s2 = s2.replace(needle, needle + "\\n      <action application=\\"export\\" data=\\"cc_moh_override=" + WAIT + '\\"/>')
idx = s2.find("cc_export_vars")
if idx >= 0 and "cc_moh_override" not in s2[idx:idx+120]:
    s2 = s2.replace(
        'data="cc_export_vars=execute_on_hangup"',
        'data="cc_export_vars=execute_on_hangup,cc_moh_override"',
    )
p.write_text(s2)
print("dialplan:", "changed" if s2 != s else "unchanged")
for ln in s2.splitlines():
    if "cc_moh" in ln or "cc_export" in ln:
        print(" ", ln.strip())
PY
  docker cp /tmp/ahununu_did.xml "skykin-freeswitch:$XML"
  echo "updated $XML"
else
  echo "WARN: no ahununu DID xml — Lua still sets waiting moh"
fi

echo "=== 4) reloadxml ==="
docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "reloadxml" || true

echo "=== 5) Verify ==="
docker exec skykin-freeswitch grep -n "opening-long\\|waiting-2\\|skykin welcome\\|skykin waiting" \\
  /etc/freeswitch/scripts/skykin_inbound.lua | head -25

echo
echo "DONE — no FS restart."
echo "Opening: opening-long.wav | Waiting: waiting-2.wav | After-hours: call-end-2.wav"
echo "Rollback: curl -fsSL ROLLBACK_URL | bash"
""")

text = "".join(parts).replace("ROLLBACK_URL", rollback_url).replace("\r\n", "\n")
out = root / "scripts/_deploy_ahununu_opening_waiting.sh"
out.write_bytes(text.encode())
r1 = requests.post(
    "https://catbox.moe/user/api.php",
    data={"reqtype": "fileupload"},
    files={"fileToUpload": ("deploy_ahununu_ow.sh", out.read_bytes(), "application/x-sh")},
    timeout=90,
)
print("deploy", r1.text)
print("rollback", rollback_url)
