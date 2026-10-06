#!/bin/bash
# FreeSWITCH quick health — read-only. LF only.
set -u
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || true)
FS() {
  if [ -n "${PW:-}" ]; then
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1" 2>/dev/null
  else
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -x "$1" 2>/dev/null
  fi
}

echo "===== container ====="
docker ps --format '{{.Names}} {{.Status}}' | grep -E 'freeswitch|skykin' || true

echo
echo "===== ESL / status ====="
FS "status" | head -20

echo
echo "===== 8021 listening ====="
docker exec skykin-freeswitch sh -c 'ss -lntp 2>/dev/null | grep 8021 || netstat -lntp 2>/dev/null | grep 8021 || echo "(ss/netstat limited)"'

echo
echo "===== sofia profiles ====="
FS "sofia status" | head -40

echo
echo "===== gateways ====="
FS "sofia status gateway" | head -40

echo
echo "===== registrations (sample) ====="
FS "show registrations" | head -40

echo
echo "===== channels now ====="
FS "show channels count"
FS "show calls count"

echo
echo "===== ACL skykin (ESL) ====="
docker exec skykin-freeswitch sh -c 'grep -A20 "list name=\"skykin\"" /etc/freeswitch/autoload_configs/acl.conf.xml 2>/dev/null | head -25'

echo
echo "===== recent ESL rejects (last 15) ====="
docker exec skykin-freeswitch sh -c 'grep -F "Rejected by acl" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -15'

echo
echo "===== recent external INVITEs (scanner style, last 15) ====="
docker exec skykin-freeswitch sh -c 'grep -E "receiving invite from|New Channel sofia/external/" /var/log/freeswitch/freeswitch.log 2>/dev/null | tail -15'

echo
echo "===== rtp advertise / inbound.lua IP ====="
docker exec skykin-freeswitch sh -c 'grep -n "rtp_ip\|236.12" /etc/freeswitch/scripts/skykin_inbound.lua 2>/dev/null | head -10'

echo
echo "DONE"
