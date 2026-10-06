#!/bin/bash
set -e
FS=skykin-freeswitch
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env | cut -d= -f2- | tr -d '\r')
fs() { docker exec "$FS" fs_cli -p "$PW" -x "$1"; }

LUA=/etc/freeswitch/scripts/skykin_inbound.lua
docker exec "$FS" test -f "$LUA"

docker exec "$FS" sed -i \
  -e 's/instant_ringback=false/instant_ringback=true/g' \
  -e 's/session:sleep(1000)/session:sleep(500)/g' \
  "$LUA" 2>/dev/null || true

if ! docker exec "$FS" grep -q 'ringback.*us-ring' "$LUA" 2>/dev/null; then
  docker exec "$FS" sed -i \
    '/session:execute("ring_ready")/a session:setVariable("ringback", "${us-ring}")' \
    "$LUA"
fi

for f in \
  /etc/freeswitch/dialplan/public/01_skykin_did.xml \
  /root/skykin-fs-etc/dialplan/public/01_skykin_did.xml; do
  if docker exec "$FS" test -f "$f" 2>/dev/null; then
    docker exec "$FS" sed -i 's/instant_ringback=false/instant_ringback=true/g' "$f"
    echo "patched ringback in $f"
  fi
done

DP=/etc/freeswitch/dialplan/01_skykin_ahununu.xml
if docker exec "$FS" test -f "$DP"; then
  if ! docker exec "$FS" grep -q skykin_outbound_et_e164 "$DP"; then
    docker cp /tmp/add_e164_ahununu.py "$FS":/tmp/add_e164_ahununu.py
    docker exec "$FS" python3 /tmp/add_e164_ahununu.py
  else
    echo "e164 rule already in dialplan"
  fi
fi

fs reloadxml
echo "==== verify ===="
docker exec "$FS" grep -n instant_ringback "$LUA" | head -3
grep -c skykin_cdr_hunt_leg /opt/skykin/app/app/agent_dashboard/skykin_config.php
echo DONE
