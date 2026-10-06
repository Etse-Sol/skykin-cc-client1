#!/bin/bash
# Deploy load-harden skykin_inbound.lua + bridge-fail alert to ecs-cc (run ON the server).
set -euo pipefail

LUA_SRC="${1:-/opt/skykin/app/docker/freeswitch/scripts/skykin_inbound.lua}"
if [ ! -f "$LUA_SRC" ]; then
  LUA_SRC="/opt/skykin/docker/freeswitch/scripts/skykin_inbound.lua"
fi

echo "==== verify source has load harden ===="
grep -n "retry once\|softphone tech fail\|is_softphone_tech_fail" "$LUA_SRC" | head -10

echo "==== install into FreeSWITCH container ===="
docker cp "$LUA_SRC" skykin-freeswitch:/etc/freeswitch/scripts/skykin_inbound.lua
# Also keep host copy in sync if present
for d in /opt/skykin/docker/freeswitch/scripts /opt/skykin/app/docker/freeswitch/scripts; do
  if [ -d "$d" ]; then
    cp -a "$LUA_SRC" "$d/skykin_inbound.lua"
  fi
done

echo "==== verify live container ===="
docker exec skykin-freeswitch grep -n "retry once\|softphone tech fail\|ALWAYS WebRTC\|media_webrtc=true" \
  /etc/freeswitch/scripts/skykin_inbound.lua | head -20

echo "==== install alert script ===="
mkdir -p /opt/skykin/scripts /var/lib/skykin-bridge-fail
if [ -f /opt/skykin/app/scripts/skykin_bridge_fail_alert.sh ]; then
  cp -a /opt/skykin/app/scripts/skykin_bridge_fail_alert.sh /opt/skykin/scripts/
elif [ -f "$(dirname "$0")/skykin_bridge_fail_alert.sh" ]; then
  cp -a "$(dirname "$0")/skykin_bridge_fail_alert.sh" /opt/skykin/scripts/
fi
chmod +x /opt/skykin/scripts/skykin_bridge_fail_alert.sh

CRON_LINE='*/2 * * * * /opt/skykin/scripts/skykin_bridge_fail_alert.sh >/dev/null 2>&1'
(crontab -l 2>/dev/null | grep -v skykin_bridge_fail_alert; echo "$CRON_LINE") | crontab -

echo "==== done — lua reloads per call; no FS restart needed ===="
echo "FS log: docker exec skykin-freeswitch sh -c 'tail -c 2M /var/log/freeswitch/freeswitch.log | grep softphone'"
