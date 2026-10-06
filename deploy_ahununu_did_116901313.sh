#!/bin/bash
# Add 0116901313 / +251116901313 as ahununu inbound DID (same path as 8414).
# Does not touch client1 or skykin_inbound.lua.
set -euo pipefail
set +H

PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2-)
FS() { docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1"; }

docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml \
  /tmp/02_skykin_did_ahununu.xml.bak.before-116901313

docker cp skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml \
  /tmp/02_skykin_did_ahununu.xml

# New expression: 035-039 OR 8414 OR 0116901313 / 116901313 / +251116901313
python3 << 'PY'
from pathlib import Path
import re
p = Path("/tmp/02_skykin_did_ahununu.xml")
t = p.read_text()
new_expr = r"^(\+?(?:251)?0?11619803[5-9]|8414|\+?(?:251)?0?116901313)$"
t2, n = re.subn(
    r'(field="destination_number" expression=")[^"]+(")',
    rf'\1{new_expr}\2',
    t,
    count=1,
)
if n != 1:
    raise SystemExit("destination_number not found")
p.write_text(t2)
print("OK")
for i, line in enumerate(t2.splitlines(), 1):
    if "destination_number" in line or "domain_name=ahununu" in line:
        print(f"{i}:{line}")
PY

echo "==== CHECK ===="
grep -n destination_number /tmp/02_skykin_did_ahununu.xml

docker cp /tmp/02_skykin_did_ahununu.xml \
  skykin-freeswitch:/etc/freeswitch/dialplan/public/02_skykin_did_ahununu.xml
mkdir -p /opt/skykin/fs-live
cp /tmp/02_skykin_did_ahununu.xml /opt/skykin/fs-live/02_skykin_did_ahununu.xml
FS "reloadxml"
echo DONE
echo "Inbound accepted: 035-039, 8414, 0116901313 / +251116901313"
echo "Ethio must route 0116901313 to your SIP8035-8039 trunks for this to ring."
