#!/bin/bash
# SkyKin whole-system health — today from 08:00 EAT (run as root on ecs-cc)
set -u
DOMAIN="${1:-ahununu}"
PW=$(grep -E '^ESL_PASSWORD=' /opt/skykin/app/.env 2>/dev/null | cut -d= -f2- || true)
FS() {
  if [ -n "${PW:-}" ]; then
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -p "$PW" -x "$1" 2>/dev/null
  else
    docker exec skykin-freeswitch fs_cli -H 127.0.0.1 -P 8021 -x "$1" 2>/dev/null
  fi
}
ok(){ echo "  OK  $*"; }
bad(){ echo "  FAIL $*"; }
warn(){ echo "  WARN $*"; }
sec(){ echo; echo "==== $* ===="; }

sec "1) Docker containers"
docker ps --format 'table {{.Names}}\t{{.Status}}' | egrep -i 'NAME|skykin' || bad "docker ps failed"

sec "2) FreeSWITCH up + ESL"
UP=$(FS "status" | head -5)
if echo "$UP" | grep -qi 'UP'; then ok "FreeSWITCH ESL responding"; echo "$UP" | sed 's/^/    /'
else bad "FreeSWITCH ESL not responding (check ESL_PASSWORD / container)"
fi

sec "3) Ethio SIP gateways (ahununu)"
GW=$(FS "sofia status gateway" 2>/dev/null || true)
echo "$GW" | egrep -i 'SIP8035|SIP8036|SIP8037|SIP8038|SIP8039|SIP757|SIP758|SIP759|Name|State' | head -40 | sed 's/^/    /'
DOWN=$(echo "$GW" | egrep -i 'SIP803[5-9]|SIP75[789]' | egrep -vic 'REGED|NOREG|UP' || true)
# NOREG is OK for IP auth trunks; look for FAILED/DOWN
FAIL=$(echo "$GW" | egrep -i 'SIP803[5-9]|SIP75[789]' | egrep -ic 'FAIL|DOWN|UNREACH' || true)
if [ "${FAIL:-0}" -gt 0 ]; then bad "some gateways FAIL/DOWN"; else ok "no FAIL/DOWN on Ethio gateways"; fi

sec "4) Agent softphone registrations ($DOMAIN)"
REG=$(FS "sofia status profile internal reg" 2>/dev/null || true)
echo "$REG" | egrep -i "User:|Contact:|$DOMAIN|Auth-User|Status" | head -60 | sed 's/^/    /'
for ext in 201 202 203 204 205; do
  C=$(FS "sofia_contact */${ext}@${DOMAIN}" 2>/dev/null | tr -d '\r')
  if echo "$C" | grep -qi 'error\|not_registered\|-ERR'; then
    warn "ext $ext not registered"
  else
    ok "ext $ext registered"
  fi
done

sec "5) Call center queue 8000@$DOMAIN"
FS "callcenter_config queue list agents 8000@$DOMAIN" 2>/dev/null | head -25 | sed 's/^/    /'
MEM=$(FS "callcenter_config queue list members 8000@$DOMAIN" 2>/dev/null | head -15)
echo "$MEM" | sed 's/^/    /'
WAIT=$(echo "$MEM" | grep -c '|' || true)
# header line counts; rough
ok "queue agents listed (see Waiting/Idle/In a queue above)"

sec "6) Active channels now"
CH=$(FS "show channels count" 2>/dev/null | tr -d '\r')
echo "    $CH"
FS "show calls count" 2>/dev/null | sed 's/^/    /'

sec "7) Web / DB containers"
docker exec skykin-web php -r 'echo "PHP ".PHP_VERSION." ok\n";' 2>/dev/null | sed 's/^/    /' || bad "skykin-web php"
docker exec skykin-db pg_isready -U fusionpbx 2>/dev/null | sed 's/^/    /' || \
  docker exec skykin-db pg_isready 2>/dev/null | sed 's/^/    /' || warn "pg_isready check skipped"

sec "8) Call stats today from 08:00 EAT ($DOMAIN)"
docker exec -e DOMAIN="$DOMAIN" skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$domain = getenv("DOMAIN") ?: "ahununu";
$tz = new DateTimeZone("Africa/Addis_Ababa");
$now = new DateTime("now", $tz);
$from = new DateTime($now->format("Y-m-d")." 08:00:00", $tz);
$ts = $from->getTimestamp();
$te = $now->getTimestamp();
echo "Window: ".$from->format("Y-m-d H:i")." -> ".$now->format("Y-m-d H:i T")."\n";
$db = skykin_pdo_fusionpbx();
$rows = skykin_cdr_fetch_period($db, $domain, $ts, $te);
$m = skykin_cdr_period_metrics($rows);
$failed=0; $busy=0; $rec=0; $ansNoRec=0; $in=0; $out=0;
foreach ($rows as $r) {
  $lab = skykin_cdr_result_label($r);
  $dir = strtolower(trim((string)($r["direction"]??"")));
  if ($dir==="inbound") $in++; elseif ($dir==="outbound") $out++;
  if ($lab==="Failed") $failed++;
  if ($lab==="Agent Busy") $busy++;
  if (trim((string)($r["record_name"]??""))!=="") $rec++;
  if ($lab==="Answered" && trim((string)($r["record_name"]??""))==="") $ansNoRec++;
}
printf("Calls: %d  (in %d / out %d)\n", (int)$m["total"], $in, $out);
printf("Answered: %d | Abandoned: %d | Missed: %d | Failed: %d | Busy: %d\n",
  (int)$m["answered"], (int)$m["abandoned"], (int)$m["missed"], $failed, $busy);
printf("Avg talk: %s | Recordings on CDR: %d | Answered without file: %d\n",
  skykin_cdr_fmt_dur((int)($m["avg_dur"]??0)), $rec, $ansNoRec);
if ((int)$m["total"] < 1) echo "WARN: no CDR rows since 08:00 — check xml_cdr / clock\n";
elseif ((int)$m["answered"] < 1 && $in > 5) echo "WARN: inbound traffic but 0 Answered\n";
else echo "OK: CDR flow looks alive since 08:00\n";
' 2>&1 | sed 's/^/    /'

sec "9) Recordings disk (today archive)"
TODAY_Y=$(TZ=Africa/Addis_Ababa date +%Y)
TODAY_M=$(TZ=Africa/Addis_Ababa date +%b)
TODAY_D=$(TZ=Africa/Addis_Ababa date +%d)
REC="/var/lib/freeswitch/recordings/$DOMAIN/archive/$TODAY_Y/$TODAY_M/$TODAY_D"
docker exec skykin-freeswitch sh -c "ls -lah '$REC' 2>/dev/null | tail -15; echo -n 'wav count: '; ls '$REC'/*.wav 2>/dev/null | wc -l" 2>/dev/null | sed 's/^/    /' \
  || warn "no archive folder yet $REC"

sec "10) Recent FS errors (last 30m keywords)"
docker logs skykin-freeswitch --since 30m 2>&1 | egrep -i 'ERROR|CRIT|skykin_record_on_agent|blacklist drop|gateway' | tail -25 | sed 's/^/    /' \
  || warn "no matching log lines"

sec "Summary"
echo "  If gateways OK + some agents registered + CDR increasing since 08:00 → core calling path is working."
echo "  Abandoned with no recording is normal (IVR only)."
echo "  Answered without recording needs investigation for those rows."
echo DONE
