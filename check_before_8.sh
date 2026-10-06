#!/bin/bash
# SkyKin health — TODAY before 08:00 EAT (00:00-08:00)
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
echo "==== Before 08:00 today (EAT) — $DOMAIN ===="
docker exec -e DOMAIN="$DOMAIN" skykin-web php -r '
require "/var/www/fusionpbx/app/agent_dashboard/skykin_config.php";
$domain = getenv("DOMAIN") ?: "ahununu";
$tz = new DateTimeZone("Africa/Addis_Ababa");
$day = (new DateTime("now", $tz))->format("Y-m-d");
$from = new DateTime("$day 00:00:00", $tz);
$to = new DateTime("$day 07:59:59", $tz);
$ts = $from->getTimestamp();
$te = $to->getTimestamp();
echo "Window: ".$from->format("Y-m-d H:i")." -> ".$to->format("Y-m-d H:i T")."\n";
$db = skykin_pdo_fusionpbx();
$rows = skykin_cdr_fetch_period($db, $domain, $ts, $te);
$m = skykin_cdr_period_metrics($rows);
$failed=0; $busy=0; $rec=0; $ansNoRec=0; $in=0; $out=0;
$hourly=[];
foreach ($rows as $r) {
  $lab = skykin_cdr_result_label($r);
  $dir = strtolower(trim((string)($r["direction"]??"")));
  if ($dir==="inbound") $in++; elseif ($dir==="outbound") $out++;
  if ($lab==="Failed") $failed++;
  if ($lab==="Agent Busy") $busy++;
  if (trim((string)($r["record_name"]??""))!=="") $rec++;
  if ($lab==="Answered" && trim((string)($r["record_name"]??""))==="") $ansNoRec++;
  $h = (int)($r["hour"] ?? -1);
  if ($h < 0 && !empty($r["call_time"]) && preg_match("/ (\d{2}):/", (string)$r["call_time"], $mm)) $h = (int)$mm[1];
  if ($h >= 0) {
    if (!isset($hourly[$h])) $hourly[$h] = ["t"=>0,"a"=>0,"abd"=>0,"m"=>0];
    $hourly[$h]["t"]++;
    if ($lab==="Answered") $hourly[$h]["a"]++;
    elseif ($lab==="Abandoned") $hourly[$h]["abd"]++;
    elseif ($lab==="Missed") $hourly[$h]["m"]++;
  }
}
printf("Calls: %d  (in %d / out %d)\n", (int)$m["total"], $in, $out);
printf("Answered: %d | Abandoned: %d | Missed: %d | Failed: %d | Busy: %d\n",
  (int)$m["answered"], (int)$m["abandoned"], (int)$m["missed"], $failed, $busy);
printf("Avg talk: %s | Recordings on CDR: %d | Answered without file: %d\n",
  skykin_cdr_fmt_dur((int)($m["avg_dur"]??0)), $rec, $ansNoRec);
echo "---- By hour ----\n";
ksort($hourly);
foreach ($hourly as $h=>$v) {
  printf("%02d:00  total=%d  answered=%d  abandoned=%d  missed=%d\n", $h, $v["t"], $v["a"], $v["abd"], $v["m"]);
}
if ((int)$m["total"] < 1) echo "No CDR before 08:00 (quiet night or no traffic).\n";
else echo "OK: early-morning CDR present.\n";
echo "---- Latest 12 before 08:00 ----\n";
$i=0;
foreach ($rows as $r) {
  if ($i++ >= 12) break;
  $lab = skykin_cdr_result_label($r);
  $recf = trim((string)($r["record_name"]??"")) !== "" ? "rec" : "-";
  printf("  %s  %-10s  %s -> %s  %s  %s\n",
    $r["call_time"]??"", $lab, $r["caller_id_number"]??"", $r["destination_number"]??"",
    skykin_cdr_fmt_dur(skykin_cdr_display_sec($r)), $recf);
}
'

echo
echo "==== Continuity (FS / gateways — same as now, up for days) ===="
FS "status" | head -3 | sed "s/^/  /"
FS "sofia status gateway" 2>/dev/null | egrep "SIP803[5-9]" | sed "s/^/  /"
echo DONE
