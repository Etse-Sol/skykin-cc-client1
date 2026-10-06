# Paste on ecs-cc — inspect real inbound + after-hours

echo "==== A) live lua size + head ===="
docker exec skykin-freeswitch sh -c '
ls -la /etc/freeswitch/scripts/skykin_inbound.lua
wc -l /etc/freeswitch/scripts/skykin_inbound.lua
head -100 /etc/freeswitch/scripts/skykin_inbound.lua
'

echo "==== B) search after-hours anywhere in scripts ===="
docker exec skykin-freeswitch sh -c '
grep -rn "after-hours\|outside_business\|biz_hours\|1900\|call-end-2\|closed.wav" \
  /etc/freeswitch/scripts/ 2>/dev/null | head -40
'

echo "==== C) dialplan hours / inbound lua call ===="
docker exec skykin-freeswitch sh -c '
grep -rn "skykin_inbound\|biz_hours\|after.hour\|1900\|lua.*inbound" \
  /etc/freeswitch/dialplan/ 2>/dev/null | head -40
'

echo "==== D) FS container status + fs_cli socket ===="
docker ps --filter name=skykin-freeswitch --format "{{.Names}} {{.Status}}"
docker exec skykin-freeswitch sh -c '
ls -la /var/run/freeswitch/freeswitch.sock /usr/local/freeswitch/var/run/freeswitch/freeswitch.sock 2>/dev/null
ps aux | grep -i free | grep -v grep | head -5
'

echo "==== E) host vs Addis time ===="
date -u
TZ=Africa/Addis_Ababa date
