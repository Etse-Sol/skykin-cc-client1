#!/bin/sh
# Fix agent-to-agent calls on ecs-testbed (503 / Network unavailable).
# Root cause: direct nginx->7443 WSS puts fs_path on registrations; bridge dies.
#
# Run as root:
#   cd /opt/skykin/skykin-cc-client1 && git pull
#   bash scripts/skykin_fix_agent_local_calls.sh
set -eu

cd "$(dirname "$0")/.."
REPO="$(pwd)"
ESL_PASS="$(grep '^ESL_PASSWORD=' .env 2>/dev/null | cut -d= -f2- || true)"

echo "=== 1) ws-sip gateway (WSS -> FS UDP, no fs_path) ==="
bash "$REPO/scripts/skykin_install_ws_sip.sh"

echo "=== 2) point web /wss/ at ws-sip (not 7443) ==="
grep -q '^FREESWITCH_WS_UPSTREAM=' .env || echo 'FREESWITCH_WS_UPSTREAM=172.18.0.1:18081' >> .env
grep -q '^FREESWITCH_WS_SCHEME=' .env || echo 'FREESWITCH_WS_SCHEME=http' >> .env
sed -i 's|^FREESWITCH_WS_UPSTREAM=.*|FREESWITCH_WS_UPSTREAM=172.18.0.1:18081|' .env
sed -i 's|^FREESWITCH_WS_SCHEME=.*|FREESWITCH_WS_SCHEME=http|' .env
grep -E '^FREESWITCH_WS_' .env

docker compose -f docker-compose.ecs-cc.yml --env-file .env up -d --force-recreate web
sleep 3
docker exec skykin-web grep proxy_pass /etc/nginx/sites-available/skykin.conf | head -2

echo "=== 3) FreeSWITCH: drop NDLB fs_path + use static WebRTC dialplan ==="
docker exec skykin-freeswitch sh -c '
f=/etc/freeswitch/sip_profiles/internal.xml
sed -i "s#<param name=\"sip-force-contact\" value=\"NDLB-tls-connectile-dysfunction\"/>#<param name=\"sip-force-contact\" value=\"\"/>#" "$f" || true
sed -i "s#<param name=\"apply-nat-acl\" value=\"nat.auto\"/>#<param name=\"apply-nat-acl\" value=\"none\"/>#" "$f" || true
grep -E "sip-force-contact|apply-nat-acl|xml-handler-bindings" /etc/freeswitch/autoload_configs/lua.conf.xml "$f" | head -10
'
bash "$REPO/scripts/skykin_use_static_dialplan.sh"

echo "=== 4) patch static bridge to rtp_secure_media=true ==="
docker exec skykin-freeswitch sh -c '
for f in /etc/freeswitch/dialplan/client1.skykin.local/00_webrtc_local.xml \
         /etc/freeswitch/dialplan/01_skykin_client1.skykin.local.xml; do
  [ -f "$f" ] || continue
  sed -i "s/rtp_secure_media=optional/rtp_secure_media=true/g" "$f"
done
grep -n "rtp_secure_media\|media_webrtc\|bridge" /etc/freeswitch/dialplan/client1.skykin.local/00_webrtc_local.xml | head -8
'

if [ -n "$ESL_PASS" ]; then
	docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$ESL_PASS" -x "reloadxml"
fi

echo ""
echo "DONE"
echo "1) Hard-refresh BOTH agent browsers (Ctrl+F5)"
echo "2) Wait for Registered on 101 and 102"
echo "3) Dial 102 from 101"
echo ""
echo "Verify registration has NO fs_path (should show UDP 127.0.0.1 after ws-sip):"
echo "  docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p \"\$ESL_PASS\" -x \"sofia status profile internal reg\""
