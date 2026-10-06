#!/bin/bash
set -euo pipefail
echo "==== Find ahununu audio files ===="
docker exec skykin-freeswitch sh -c '
echo "-- recordings tree --"
find /var/lib/freeswitch/recordings/ahununu -type f \( -name "*.wav" -o -name "*.mp3" \) 2>/dev/null | head -40
echo "-- opening/welcome names --"
find /var/lib/freeswitch/recordings /usr/share/freeswitch/sounds /etc/freeswitch -iname "*open*" -o -iname "*welcome*" -o -iname "*wait*" -o -iname "*ahununu*" 2>/dev/null | head -40
echo "-- scripts welcome path --"
grep -n "opening\|welcome\|wav" /etc/freeswitch/scripts/skykin_welcome.lua 2>/dev/null || true
grep -n "playback\|streamFile\|opening\|music" /etc/freeswitch/scripts/skykin_inbound.lua 2>/dev/null || true
'
echo "==== host overlay ===="
ls -la /opt/skykin/fs-live/recordings/ahununu 2>/dev/null | head -20 || true
find /opt/skykin -iname "*opening*" -o -iname "*welcome*" 2>/dev/null | head -20
echo DONE
