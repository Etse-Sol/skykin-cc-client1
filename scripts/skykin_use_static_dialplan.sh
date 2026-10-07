#!/bin/sh
# Use SkyKin static dialplan (WebRTC bridge) instead of FusionPBX DB dialplan.
# FusionPBX DB still serves the SIP directory so extensions from the UI register.
#
# Run on ecs-testbed as root:
#   bash scripts/skykin_use_static_dialplan.sh
set -eu

LUACONF=/etc/freeswitch/autoload_configs/lua.conf.xml
ESL_PASS="${ESL_PASSWORD:-}"
if [ -z "$ESL_PASS" ] && [ -f .env ]; then
	ESL_PASS=$(grep '^ESL_PASSWORD=' .env | cut -d= -f2-)
fi

echo "=== before ==="
docker exec skykin-freeswitch grep xml-handler-bindings "$LUACONF" || true
docker exec skykin-freeswitch sh -c 'grep -n "webrtc_local\|skykin_local_extension" /etc/freeswitch/dialplan/01_skykin_*.xml /etc/freeswitch/dialplan/client1.skykin.local/*.xml 2>/dev/null | head -6'

echo "=== switch xml_handler to directory-only (static dialplan) ==="
docker exec skykin-freeswitch sed -i \
	's/name="xml-handler-bindings" value="directory dialplan"/name="xml-handler-bindings" value="directory"/' \
	"$LUACONF"
docker exec skykin-freeswitch sed -i \
	's/name="xml-handler-bindings" value="directory,dialplan"/name="xml-handler-bindings" value="directory"/' \
	"$LUACONF"

echo "=== after ==="
docker exec skykin-freeswitch grep xml-handler-bindings "$LUACONF" || true

echo "=== restart FreeSWITCH (mod_lua reads bindings at load time) ==="
docker restart skykin-freeswitch
sleep 8

if [ -n "$ESL_PASS" ]; then
	docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$ESL_PASS" -x "status" | head -3
fi

echo "DONE — hard-refresh both agent browsers, wait for Registered, dial 102 from 101"
echo "During call, expect: EXECUTE ... bridge (not app.lua voicemail)"
