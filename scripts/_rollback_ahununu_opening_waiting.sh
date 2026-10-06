#!/bin/bash
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
